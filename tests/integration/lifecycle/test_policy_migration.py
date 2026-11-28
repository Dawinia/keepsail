"""Migration from signed policy transitions, reader-first (plan C3, C7, C10).

Steps 1-2 run the previous release (this Change's branch point, pinned below)
to migrate a ``signed-plan-decision`` policy to json owner conclusions with one
signed transition.  Step 3 delivers the upgrade itself without a risk-boundary
change and is verified by the *old* verifier installed from the migrated base.
Step 4 delivers ordinarily with this code, verified by the new verifier
installed from the upgraded base; an in-flight Change listed in the old signed
continuation re-obtains its approval under the effective policy.

Needs full history (``fetch-depth: 0``): a missing pinned commit fails, it is
never skipped.  The old release needs ``cryptography`` (a test-only dependency).
"""

import base64
import io
import json
import os
import shutil
import subprocess
import tarfile
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from keepsail.core.approval import canonical_json
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state
from tests.integration.lifecycle.policy_repo import (
    OWNER_PROCESS,
    SOURCE,
    PolicyRepo,
    edited,
    git,
    install_wheel,
    verify_with_installed_base,
)

PREVIOUS_RELEASE = "5c351ddcee8efdfd2449ad77f5fbdba74f4f70e3"
MAINTAINER = {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
              "issuer": "maintainer"}


def previous_release_python(area: Path) -> Path:
    present = subprocess.run(["git", "cat-file", "-e", f"{PREVIOUS_RELEASE}^{{commit}}"],
                             cwd=SOURCE, capture_output=True)
    if present.returncode != 0:
        pytest.fail(f"pinned previous release {PREVIOUS_RELEASE} is not in this clone; the "
                    "migration test needs full history (actions/checkout fetch-depth: 0)")
    source = area / "previous-source"
    git(SOURCE, "worktree", "add", "-q", "--detach", str(source), PREVIOUS_RELEASE)
    try:
        return install_wheel(source, area / "previous-wheels", area / "previous-venv")
    finally:
        git(SOURCE, "worktree", "remove", "--force", str(source))


def checkout_previous_source(root: Path) -> None:
    archive = subprocess.check_output(["git", "archive", "--format=tar", PREVIOUS_RELEASE,
                                       "src/keepsail", "pyproject.toml", "README.md"],
                                      cwd=SOURCE)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(root, filter="data")
        else:  # Python 3.10/3.11 before the extraction filters
            tar.extractall(root)  # our own git archive


def replace_source_with_this_change(root: Path) -> None:
    shutil.rmtree(root / "src/keepsail")
    shutil.copytree(SOURCE / "src/keepsail", root / "src/keepsail",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for filename in ("pyproject.toml", "README.md"):
        shutil.copy2(SOURCE / filename, root / filename)


class Previous:
    """Drive the previous release's CLI in its own isolated interpreter."""

    def __init__(self, python: Path, root: Path) -> None:
        self.python, self.root = python, root

    def run(self, *args: str, data: object = None, check: bool = True) -> str:
        text = json.dumps(data) if isinstance(data, (dict, list)) else data
        result = subprocess.run(
            [str(self.python), "-I", "-c", "from keepsail.cli import main; main()",
             "--workspace", str(self.root), *args],
            input=text, capture_output=True, text=True, cwd=self.root,
            env={**os.environ, "PYTHONUTF8": "1"}, timeout=600)
        if check:
            assert result.returncode == 0, (args, result.stdout, result.stderr)
        return result.stdout

    def evaluate(self, program: str) -> object:
        output = subprocess.check_output([str(self.python), "-I", "-c", program], text=True,
                                         cwd=self.root, env={**os.environ, "PYTHONUTF8": "1"})
        return json.loads(output)


def signed_plan_evidence(key, policy_digest, change, subject, evidence_id, key_id):
    body = {"version": "signed-plan-decision/v1", "repository_id": "owner/project",
            "target_ref": "refs/heads/main", "policy_digest": policy_digest,
            "change_id": change, "subject_id": subject, "decision": "approve",
            "evidence_id": evidence_id, "supersedes": None, "key_id": key_id}
    body["signature"] = base64.b64encode(key.sign(canonical_json(body).encode())).decode()
    return {"version": "review-evidence/v1", "evidence_id": evidence_id, "kind": "plan",
            "subject_id": subject, "decision": "approve",
            "process": {"id": MAINTAINER["id"], "version": MAINTAINER["version"]},
            "issuer": "maintainer", "form": "signed-plan-decision", "original_evidence": body,
            "provenance": {"policy_digest": policy_digest}}


def pending_subject(root: Path, change: str) -> str:
    return derive_state(events_path(root))[change].pending_revision["subject"]["subject_id"]


def test_signed_policy_migrates_with_the_old_release_then_upgrades_reader_first(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    old_python = previous_release_python(tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    checkout_previous_source(root)
    repo = PolicyRepo(root, None)  # the old release writes the first policy below
    old = Previous(old_python, root)
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    key_id = sha256(public).hexdigest()

    # 1. Old release: owner-established initial signed-plan policy.
    git(root, "switch", "-q", "main")
    prepared = json.loads(old.run(
        "--json", "policy", "initial", "prepare", "--repository-id", "owner/project",
        "--target-ref", "refs/heads/main",
        "--public-key", base64.b64encode(public).decode()))["data"]
    initial_policy = prepared["policy"]
    repo.write_policy(initial_policy)
    (repo.harness / "policy-authority.yaml").write_text(yaml.safe_dump(prepared["authority"]),
                                                       encoding="utf-8")
    first = repo.commit("propose the first signed-plan policy")
    confirmation = old.run("policy", "initial", "confirmation", "--initial-commit", first,
                           "--repository-id", "owner/project", "--target-ref",
                           "refs/heads/main", "--evidence", "-", data={
                               "owner": "fixture owner", "statement": "Confirm the first policy",
                               "evidence_reference": "fixture", "original_evidence": "yes"})
    (repo.harness / "policy-initial-trust.json").write_text(confirmation, encoding="utf-8")
    signed_base = repo.commit("retain the owner's initial confirmation")
    git(root, "switch", "-q", "candidate")
    git(root, "reset", "-q", "--hard", signed_base)

    # 2. Old release: an in-flight Change approved under the signed process ...
    old.run("change", "start", "inflight", "--framework", "plain")
    old.run("plan", "ready", "inflight", "--plan", "plan.md", "--scope", "[plan.md]",
            "--commitment", "goal=Deliver the approved change")
    inflight_subject = pending_subject(root, "inflight")
    old.run("review", "import", "inflight", "--evidence", "-", data=signed_plan_evidence(
        key, initial_policy["policy_digest"], "inflight", inflight_subject,
        "maintainer-inflight", key_id))
    inflight_approval = derive_state(events_path(root))["inflight"].effective_approval
    # ... and one signed transition to json owner conclusions, listing it as continued.
    old.run("change", "start", "migrate", "--framework", "plain")
    old.run("plan", "ready", "migrate", "--plan", "plan.md",
            "--scope", "[.harness/review-recognition.yaml]",
            "--commitment", "goal=Migrate plan review to json owner conclusions")
    migrate_subject = pending_subject(root, "migrate")
    old.run("review", "import", "migrate", "--evidence", "-", data=signed_plan_evidence(
        key, initial_policy["policy_digest"], "migrate", migrate_subject,
        "maintainer-migrate", key_id))
    target = {k: v for k, v in initial_policy.items() if k != "policy_digest"}
    target["processes_by_kind"] = {"plan": {
        "id": OWNER_PROCESS["id"], "version": OWNER_PROCESS["version"],
        "issuers": [OWNER_PROCESS["issuer"]], "evidence_forms": ["json"], "requirements": {}}}
    target["activation"] = {"kind": "transition", "change": "migrate"}
    target = edited({**target, "policy_digest": ""})
    repo.write_policy(target)
    changes = old.evaluate(
        "import json, yaml\n"
        "from keepsail.core.delivery_policy import parse_delivery_policy\n"
        "from keepsail.core.policy_obligations import changed_obligations\n"
        "from keepsail.engineering.verification_config import "
        "parse_verification_config, required_check_contract\n"
        f"old = parse_delivery_policy({initial_policy!r})\n"
        f"new = parse_delivery_policy({target!r})\n"
        "checks = required_check_contract(parse_verification_config("
        "open('.harness/verification.yaml', encoding='utf-8').read(), strict=True))\n"
        "print(json.dumps(changed_obligations(old_processes={k: p for k in ('plan', 'code') "
        "if (p := old.recognition_for(k))}, old_code_review=old.code_review, "
        "old_scope=old.scope, old_builtin=old.builtin_checks_version, old_checks=checks, "
        "new_policy=new, new_checks=checks)))\n")
    authorization = {
        "version": "policy-authorization/v1", "repository_id": "owner/project",
        "target_ref": "refs/heads/main", "base_sha": signed_base,
        "predecessor_policy_digest": initial_policy["policy_digest"],
        "target_policy_digest": target["policy_digest"], "change_id": "migrate",
        "plan_subject_id": migrate_subject, "kind": "transition",
        "permitted_paths": [".harness/review-recognition.yaml"], "decision": "approve",
        "key_id": key_id,
        "obligation_changes": [{**item, "reason": "Owner moves to json conclusions"}
                               for item in changes],
        "continued_plans": [{
            "change_id": "inflight", "subject_id": inflight_approval["subject_id"],
            "approval_id": inflight_approval["approval_id"],
            "evidence_digest": inflight_approval["evidence_digest"],
            "predecessor_policy_digest": initial_policy["policy_digest"]}],
    }
    authorization["signature"] = base64.b64encode(
        key.sign(canonical_json(authorization).encode())).decode()
    repo.write_policy(initial_policy)  # the authorization is imported before implementation
    old.run("policy", "authorization", "import", "migrate", "--evidence", "-",
            "--repository-id", "owner/project", "--target-ref", "refs/heads/main",
            data=authorization)
    old.run("implementation", "start", "migrate")
    repo.write_policy(target)
    repo.commit("migrate plan review to json owner conclusions")
    old.run("implementation", "record", "migrate", "--assessment", "-", data={
        "affected_commitments": ["goal"], "conclusion": "within_approval",
        "reasons": ["Only the signed transition."],
        "references": [".harness/review-recognition.yaml"]})
    old.run("done", "migrate")
    old.run("attest", "write", "migrate", "--format", "v3")
    git(root, "add", ".harness/attestations/v3/migrate.jsonl")
    git(root, "commit", "-qm", "retain the signed migration")
    migrated = git(root, "rev-parse", "HEAD")
    verified = verify_with_installed_base(root, signed_base, migrated, label="old-migration")
    assert verified.returncode == 0, verified.stdout + verified.stderr
    repo.advance_main(migrated)

    # 3. Upgrade delivery (reader-first): this code, no risk-boundary change, the
    #    retained policy-authority.yaml kept, verified by the OLD verifier from the base.
    assert (repo.harness / "policy-authority.yaml").exists()
    upgrade_subject = repo.plan("upgrade")
    repo.ok("review", "import", "upgrade", "--evidence", "-", data=repo.evidence(
        "upgrade", "plan", upgrade_subject, OWNER_PROCESS, target))
    repo.ok("implementation", "start", "upgrade")
    replace_source_with_this_change(root)
    repo.commit("upgrade keepsail")
    changed = git(root, "diff", "--name-only", f"{migrated}..HEAD").splitlines()
    repo.record("upgrade", changed)
    repo.ok("done", "upgrade")
    record = repo.attest("upgrade")
    assert record["authorization"] is None
    upgraded = git(root, "rev-parse", "HEAD")
    verified = verify_with_installed_base(root, migrated, upgraded, label="old-reader")
    assert verified.returncode == 0, verified.stdout + verified.stderr
    repo.advance_main(upgraded)

    # 4. On the upgraded base: an ordinary delivery with this code and the new verifier.
    after_subject = repo.plan("after-upgrade")
    repo.ok("review", "import", "after-upgrade", "--evidence", "-", data=repo.evidence(
        "after-upgrade", "plan", after_subject, OWNER_PROCESS, target))
    repo.ok("implementation", "start", "after-upgrade")
    (root / "ordinary.txt").write_bytes(b"ordinary\n")
    repo.commit("ordinary change")
    repo.record("after-upgrade", ["ordinary.txt"])
    repo.ok("done", "after-upgrade")
    repo.attest("after-upgrade")
    head = git(root, "rev-parse", "HEAD")
    verified = verify_with_installed_base(root, upgraded, head, label="new-reader")
    assert verified.returncode == 0, verified.stdout + verified.stderr

    # The in-flight Change's signed continuation no longer applies after the upgrade.
    git(root, "switch", "-qc", "inflight-branch", upgraded)
    status = json.loads(repo.ok("--json", "status", "inflight").output)["data"]["changes"][0]
    assert status["approval_recognition"]["recognized"] is False
    assert "no longer in the effective policy" in status["approval_recognition"]["reason"]
    refused = repo.cli("implementation", "start", "inflight")
    assert refused.exit_code == 2
    # Approved but not started: rewind and obtain a plan approval under the new process.
    repo.ok("plan", "redeclare", "inflight", "--reason", "re-approve under the effective policy")
    resubmitted = repo.plan("inflight")
    supersedes = "maintainer-inflight" if resubmitted == inflight_subject else None
    repo.ok("review", "import", "inflight", "--evidence", "-", data=repo.evidence(
        "inflight", "plan", resubmitted, OWNER_PROCESS, target, supersedes=supersedes))
    repo.ok("implementation", "start", "inflight")
    (root / "inflight.txt").write_bytes(b"inflight\n")
    repo.commit("deliver the in-flight change")
    repo.record("inflight", ["inflight.txt"])
    repo.ok("done", "inflight")
    repo.attest("inflight")
    verified = repo.verify(upgraded)
    assert verified.exit_code == 0, verified.output
