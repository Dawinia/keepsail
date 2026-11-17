"""A real rename into or out of a protected scope still requires code review."""

import base64
import json
import subprocess
import sys
from hashlib import sha256

import yaml
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.cli import main
from keepsail.core.approval import canonical_json, digest_record
from keepsail.core.initial_policy import prepare_initial_confirmation
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state
from keepsail.core.verification_config import parse_verification_config, required_check_contract


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_rename_either_side_of_scope_requires_exact_code_review(tmp_path):
    root = tmp_path
    harness = root / ".harness"
    harness.mkdir()
    (root / "public").mkdir()
    (root / "secure").mkdir()
    (root / "public/inside.txt").write_text("move into protected scope\n", encoding="utf-8")
    (root / "secure/outside.txt").write_text("move out of protected scope\n", encoding="utf-8")
    (root / "plan.md").write_text("# Move the approved document\n", encoding="utf-8")
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    key_id = sha256(public).hexdigest()
    authority = {"version": "policy-authority/v1", "repository_id": "owner/project",
                 "target_ref": "refs/heads/main", "enabled": True, "keys": [{
                     "key_id": key_id, "algorithm": "ed25519",
                     "public_key": base64.b64encode(public).decode(),
                     "purposes": ["policy-transition", "plan-decision"],
                 }]}
    config = {"layers": {"baseline": {"enabled": False},
                         "framework_adapter": {"enabled": False},
                         "user_checks": {"enabled": True}},
              "checks": [{"id": "fixture", "command": [sys.executable, "-c", "print('ok')"]}]}
    config_text = yaml.safe_dump(config)
    policy = {"version": "review-recognition/v2", "enabled": True,
              "processes_by_kind": {
                  "plan": {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
                           "issuers": ["maintainer"], "evidence_forms": ["signed-plan-decision"],
                           "requirements": {}},
                  "code": {"id": "independent-code", "version": "v1", "issuers": ["reviewer"],
                           "evidence_forms": ["json"], "requirements": {}},
              }, "code_review": {"mode": "scope", "scope": ["secure"]},
              "required_checks_digest": required_check_contract(
                  parse_verification_config(config_text, strict=True))["digest"],
              "builtin_checks_version": "keepsail-baseline/v2", "activation": {"kind": "initial"}}
    policy["policy_digest"] = digest_record(policy)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(authority), encoding="utf-8")
    (harness / "verification.yaml").write_text(config_text, encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "add", ".")
    git(root, "commit", "-qm", "propose first scoped policy")
    initial = git(root, "rev-parse", "HEAD")
    owner = {"owner": "fixture owner", "statement": "Confirm this first scoped policy",
             "evidence_reference": "fixture-confirmation", "original_evidence": "Owner confirmed"}
    confirmation = prepare_initial_confirmation(root, initial_commit=initial,
                                                 repository_id="owner/project",
                                                 target_ref="refs/heads/main",
                                                 owner_confirmation=owner)
    (harness / "policy-initial-trust.json").write_text(json.dumps(confirmation), encoding="utf-8")
    git(root, "add", ".harness/policy-initial-trust.json")
    git(root, "commit", "-qm", "retain scoped-policy confirmation")
    base = git(root, "rev-parse", "HEAD")
    runner = CliRunner()

    def cli(*args, data=None):
        return runner.invoke(main, ["--workspace", str(root), *args], input=data)

    for change, old, new, matched in (
        ("rename-into", "public/inside.txt", "secure/inside.txt", "secure/inside.txt"),
        ("rename-out", "secure/outside.txt", "public/outside.txt", "secure/outside.txt"),
    ):
        git(root, "switch", "-qc", change, base)
        assert cli("change", "start", change, "--framework", "plain").exit_code == 0
        ready = cli("plan", "ready", change, "--plan", "plan.md", "--scope", "[public]",
                    "--commitment", "goal=Move the approved document")
        assert ready.exit_code == 0, ready.output
        subject = derive_state(events_path(root))[change].pending_revision["subject"]["subject_id"]
        decision = {"version": "signed-plan-decision/v1", "repository_id": "owner/project",
                    "target_ref": "refs/heads/main", "policy_digest": policy["policy_digest"],
                    "change_id": change, "subject_id": subject, "decision": "approve",
                    "evidence_id": f"plan-{change}", "supersedes": None, "key_id": key_id}
        decision["signature"] = base64.b64encode(
            key.sign(canonical_json(decision).encode())
        ).decode()
        plan_evidence = {"version": "review-evidence/v1", "evidence_id": f"plan-{change}",
                         "kind": "plan", "subject_id": subject, "decision": "approve",
                         "process": {"id": "maintainer-plan-review",
                                     "version": "maintainer-plan-review/v1"},
                         "issuer": "maintainer", "form": "signed-plan-decision",
                         "original_evidence": decision,
                         "provenance": {"policy_digest": policy["policy_digest"]}}
        imported = cli("review", "import", change, "--evidence", "-",
                       data=json.dumps(plan_evidence))
        assert imported.exit_code == 0, imported.output
        assert cli("implementation", "start", change).exit_code == 0
        git(root, "mv", old, new)
        git(root, "commit", "-qm", change)
        assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                      "reasons": ["Move the approved document"], "references": [old, new]}
        recorded = cli("implementation", "record", change, "--assessment", "-",
                       data=json.dumps(assessment))
        assert recorded.exit_code == 0, recorded.output
        done = cli("done", change)
        assert done.exit_code == 0, done.output
        state = derive_state(events_path(root))[change]
        assert state.current_state == "AWAITING_CODE_REVIEW"
        assert state.current_code_subject["manifest"][0]["old_path"] == old
        status = cli("--json", "status", change)
        assert status.exit_code == 0, status.output
        delivery = json.loads(status.output)["data"]["changes"][0]["delivery_policy"]
        assert delivery["code_review_required"] is True
        assert matched in delivery["code_review_reason"]
        assert delivery["subject_matches"] is True
        assert cli("attest", "write", change).exit_code != 0
        code_evidence = {"version": "review-evidence/v1", "evidence_id": f"code-{change}",
                         "kind": "code", "subject_id": state.current_code_subject["subject_id"],
                         "decision": "approve", "process": {"id": "independent-code",
                         "version": "v1"}, "issuer": "reviewer", "form": "json",
                         "original_evidence": {"decision": "approve"},
                         "provenance": {"policy_digest": policy["policy_digest"]}}
        reviewed = cli("review", "import", change, "--evidence", "-",
                       data=json.dumps(code_evidence))
        assert reviewed.exit_code == 0, reviewed.output
        attested = cli("attest", "write", change)
        assert attested.exit_code == 0, attested.output
        git(root, "add", f".harness/attestations/v3/{change}.jsonl")
        git(root, "commit", "-qm", "retain reviewed evidence")
        verified = cli("attest", "verify", "--base", base, "--head", "HEAD",
                       "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
        assert verified.exit_code == 0, verified.output
