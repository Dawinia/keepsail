"""Replay recovery, transition, rotation and ordinary delivery in an isolated Git repo."""

import base64
import json
import os
import shutil
import subprocess
import sys
import venv
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.cli import main
from keepsail.core.approval import (
    ApprovalError,
    _recognition_from_mapping,
    canonical_json,
    digest_record,
    recognition_policy_digest,
)
from keepsail.core.attestation_v3 import parse_v3_line
from keepsail.core.delivery_policy import parse_delivery_policy
from keepsail.core.paths import events_path
from keepsail.core.policy_authority import parse_authority
from keepsail.core.policy_obligations import changed_obligations
from keepsail.core.reducer import derive_state
from keepsail.core.review_basis import recovery_recognition_digest
from keepsail.engineering.attestation_v3 import verify_v2_activation, verify_v3_transition
from keepsail.engineering.verification_config import (
    parse_verification_config,
    required_check_contract,
)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def verify_with_installed_base(root, base, head, *, label, repository_id="owner/project",
                               target_ref="refs/heads/main"):
    """Build and install the verifier from the exact base, then block Python networking."""
    area = root.parent / f"{root.name}-{label}"
    checkout = area / "trusted"
    wheels = area / "wheels"
    environment = area / "venv"
    area.mkdir()
    git(root, "clone", "-q", "--shared", "--no-checkout", "-c", "core.autocrlf=false",
        str(root), str(checkout))
    git(checkout, "checkout", "-q", "--detach", base)
    wheels.mkdir()
    uv_name = "uv.exe" if os.name == "nt" else "uv"
    adjacent_uv = Path(sys.executable).parent / uv_name
    uv = str(adjacent_uv) if adjacent_uv.is_file() else shutil.which("uv")
    env_python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if uv:
        subprocess.run([uv, "build", "--wheel", "--out-dir", str(wheels), str(checkout)],
                       check=True, capture_output=True)
        subprocess.run([uv, "venv", "--python", sys.executable, str(environment)],
                       check=True, capture_output=True)
        wheel = next(wheels.glob("keepsail-*.whl"))
        subprocess.run([uv, "pip", "install", "--python", str(env_python), str(wheel)],
                       check=True, capture_output=True)
    else:
        subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir",
                        str(wheels), str(checkout)], check=True, capture_output=True)
        venv.EnvBuilder(with_pip=True).create(environment)
        wheel = next(wheels.glob("keepsail-*.whl"))
        subprocess.run([str(env_python), "-m", "pip", "install", str(wheel)],
                       check=True, capture_output=True)
    probe = subprocess.check_output(
        [str(env_python), "-I", "-c",
         "import hashlib,pathlib,keepsail.cli.attest as m; "
         "p=pathlib.Path(m.__file__).resolve(); print(p); "
         "print(hashlib.sha256(p.read_bytes()).hexdigest())"], text=True,
    ).splitlines()
    assert "site-packages" in probe[0]
    committed = subprocess.check_output(
        ["git", "show", f"{base}:src/keepsail/cli/attest.py"], cwd=root
    )
    assert probe[1] == sha256(committed).hexdigest()
    entries = subprocess.check_output(
        ["git", "ls-tree", "-rz", head, "--", ".harness/attestations"], cwd=checkout
    )
    for entry in filter(None, entries.split(b"\0")):
        header, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = header.split()
        relative = Path(raw_path.decode("utf-8"))
        assert mode in {b"100644", b"100755"} and kind == b"blob"
        assert relative.parts[:2] == (".harness", "attestations")
        assert (len(relative.parts) == 3 or
                (len(relative.parts) == 4 and relative.parts[2] in {"v2", "v3"}))
        assert relative.suffix == ".jsonl" and ".." not in relative.parts
        destination = checkout / relative
        assert destination.resolve().is_relative_to(checkout.resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(subprocess.check_output(["git", "cat-file", "blob", oid.decode()],
                                                        cwd=checkout))
    program = (
        "import socket\n"
        "def blocked(*a, **k): raise RuntimeError('network disabled for verifier')\n"
        "socket.create_connection=blocked\n"
        "socket.socket.connect=blocked\n"
        "socket.socket.connect_ex=blocked\n"
        "socket.getaddrinfo=blocked\n"
        "from keepsail.cli import main\n"
        "main()\n"
    )
    help_text = subprocess.check_output(
        [str(env_python), "-I", "-c", "from keepsail.cli import main; main()", "attest", "verify",
         "--help"], cwd=checkout, text=True,
    )
    args = [str(env_python), "-I", "-c", program, "--workspace", str(checkout), "--json",
            "attest", "verify", "--base", base, "--head", head]
    if "--repository-id" in help_text:
        args.extend(["--repository-id", repository_id, "--target-ref", target_ref])
    return subprocess.run(
        args, cwd=checkout, capture_output=True, text=True,
        env={**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0"},
        timeout=300,
    )


def test_recovery_plan_review_uses_only_the_signed_process_and_digest(tmp_path):
    root = tmp_path
    source = Path(__file__).resolve().parents[3]
    shutil.copytree(source / "src/keepsail", root / "src/keepsail",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for filename in ("pyproject.toml", "README.md"):
        shutil.copy2(source / filename, root / filename)
    harness = root / ".harness"
    harness.mkdir()
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    authority = {"version": "policy-authority/v1", "repository_id": "owner/project",
                 "target_ref": "refs/heads/main", "enabled": True, "keys": [{
                     "key_id": sha256(public).hexdigest(), "algorithm": "ed25519",
                     "public_key": base64.b64encode(public).decode("ascii"),
                     "purposes": ["policy-transition", "policy-recovery", "plan-decision"],
                 }]}
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(authority), encoding="utf-8")
    policy = {"version": "review-recognition/v1", "enabled": True, "process": {
        "id": "old-review", "version": "v1", "kinds": ["plan", "code"],
        "issuers": ["old-reviewer"], "evidence_forms": ["json"]}}
    policy["process"]["policy_digest"] = recognition_policy_digest(policy)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    verification = {"layers": {"baseline": {"enabled": False},
                                "framework_adapter": {"enabled": False},
                                "user_checks": {"enabled": True}},
                    "checks": [{"id": "fixture", "command": [sys.executable, "-c", "print('ok')"]}]}
    verification_text = yaml.safe_dump(verification)
    (harness / "verification.yaml").write_text(verification_text, encoding="utf-8")
    process = {"id": "old-review", "version": "v1", "issuers": ["old-reviewer"],
               "evidence_forms": ["json"], "requirements": {}}
    plan_process = {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
                    "issuers": ["maintainer"], "evidence_forms": ["signed-plan-decision"],
                    "requirements": {}}
    target = {"version": "review-recognition/v2", "enabled": True,
              "processes_by_kind": {"plan": plan_process, "code": process},
              "code_review": {"mode": "off"},
              "required_checks_digest": required_check_contract(
                  parse_verification_config(verification_text, strict=True))["digest"],
              "builtin_checks_version": "keepsail-baseline/v2",
              "activation": {"kind": "transition", "change": "recovery"}}
    target["policy_digest"] = digest_record(target)
    checks = required_check_contract(parse_verification_config(verification_text, strict=True))
    old_recognition = _recognition_from_mapping(policy)
    changes = changed_obligations(old_processes={"plan": old_recognition, "code": old_recognition},
                                  old_code_review="full", old_scope=(),
                                  old_builtin="keepsail-baseline/v1", old_checks=checks,
                                  new_policy=parse_delivery_policy(target), new_checks=checks)
    (root / "plan.md").write_text("# Recover the delivery policy\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "add", ".")
    git(root, "commit", "-qm", "old policy and provisioned recovery key")
    base = git(root, "rev-parse", "HEAD")
    git(root, "switch", "-qc", "candidate")
    runner = CliRunner()

    def cli(*args, data=None):
        return runner.invoke(main, ["--workspace", str(root), *args], input=data)

    for change in ("recovery", "another", "carry"):
        started = cli("change", "start", change, "--framework", "plain")
        assert started.exit_code == 0, started.output
        ready = cli("plan", "ready", change, "--plan", "plan.md", "--scope", "[plan.md]",
                    "--commitment", "goal=Recover the delivery policy")
        assert ready.exit_code == 0, ready.output
    for change in ("another", "carry"):
        old_subject = derive_state(events_path(root))[change].pending_revision["subject"][
            "subject_id"]
        old_evidence = {"version": "review-evidence/v1", "evidence_id": f"old-plan-{change}",
                        "kind": "plan", "subject_id": old_subject, "decision": "approve",
                        "process": {"id": "old-review", "version": "v1"},
                        "issuer": "old-reviewer", "form": "json",
                        "original_evidence": {"decision": "approve"},
                        "provenance": {"policy_digest": policy["process"]["policy_digest"]}}
        imported = cli("review", "import", change, "--evidence", "-",
                       data=json.dumps(old_evidence))
        assert imported.exit_code == 0, imported.output
    carry_approval = derive_state(events_path(root))["carry"].effective_approval
    subject = derive_state(events_path(root))["recovery"].pending_revision["subject"]["subject_id"]
    authorization = {
        "version": "policy-authorization/v1", "repository_id": "owner/project",
        "target_ref": "refs/heads/main", "base_sha": base,
        "predecessor_policy_digest": policy["process"]["policy_digest"],
        "target_policy_digest": target["policy_digest"], "change_id": "recovery",
        "plan_subject_id": subject, "kind": "recovery",
        "permitted_paths": ["plan.md", ".harness/review-recognition.yaml"],
        "decision": "approve", "key_id": authority["keys"][0]["key_id"],
        "reason": "Old reviewer is unavailable",
        "continued_plans": [{"change_id": "carry", "subject_id": carry_approval["subject_id"],
                             "approval_id": carry_approval["approval_id"],
                             "evidence_digest": carry_approval["evidence_digest"],
                             "predecessor_policy_digest": policy["process"]["policy_digest"]}],
        "obligation_changes": [{**item, "reason": "Owner selects the new built-in contract"}
                               for item in changes],
        "review_processes": [
            {"kind": kind, "id": "backup-review", "version": "v1",
             "issuer": "backup-reviewer", "evidence_form": "json"}
            for kind in ("plan", "code")
        ],
    }
    authorization["signature"] = base64.b64encode(
        key.sign(canonical_json(authorization).encode())
    ).decode()
    imported = cli("policy", "authorization", "import", "recovery", "--evidence", "-",
                   "--repository-id", "owner/project", "--target-ref", "refs/heads/main",
                   data=json.dumps(authorization))
    assert imported.exit_code == 0, imported.output
    basis_digest = recovery_recognition_digest(policy["process"]["policy_digest"],
                                               digest_record(authorization))
    evidence = {"version": "review-evidence/v1", "evidence_id": "backup-plan", "kind": "plan",
                "subject_id": subject, "decision": "approve",
                "process": {"id": "backup-review", "version": "v1"},
                "issuer": "backup-reviewer", "form": "json",
                "original_evidence": {"decision": "approve"},
                "provenance": {"policy_digest": basis_digest}}
    wrong = deepcopy(evidence)
    wrong["provenance"]["policy_digest"] = policy["process"]["policy_digest"]
    assert cli("review", "import", "recovery", "--evidence", "-",
               data=json.dumps(wrong)).exit_code == 2
    wrong = deepcopy(evidence)
    wrong["issuer"] = "different-reviewer"
    assert cli("review", "import", "recovery", "--evidence", "-",
               data=json.dumps(wrong)).exit_code == 2
    assert cli("review", "import", "another", "--evidence", "-",
               data=json.dumps(evidence)).exit_code == 2
    approved = cli("--json", "review", "import", "recovery", "--evidence", "-",
                   data=json.dumps(evidence))
    assert approved.exit_code == 0, approved.output
    assert json.loads(approved.output)["data"]["recognition_basis"]["mode"] == "recovery"
    assert derive_state(events_path(root))["recovery"].current_state == "PLAN_APPROVED"
    git(root, "commit", "--allow-empty", "-qm", "advance the target")
    git(root, "update-ref", "refs/heads/main", git(root, "rev-parse", "HEAD"))
    stale = cli("implementation", "start", "recovery")
    assert stale.exit_code == 2, stale.output
    git(root, "update-ref", "refs/heads/main", base)
    assert cli("implementation", "start", "recovery").exit_code == 0
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(target), encoding="utf-8")
    git(root, "add", ".harness/review-recognition.yaml")
    git(root, "commit", "-qm", "propose the signed target policy")
    assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                  "reasons": ["Only the frozen policy transition is implemented."],
                  "references": [".harness/review-recognition.yaml"]}
    recorded = cli("implementation", "record", "recovery", "--assessment", "-",
                   data=json.dumps(assessment))
    assert recorded.exit_code == 0, recorded.output
    completed = cli("done", "recovery")
    assert completed.exit_code == 0, completed.output
    code = derive_state(events_path(root))["recovery"].current_code_subject
    code_evidence = {**evidence, "evidence_id": "backup-code", "kind": "code",
                     "subject_id": code["subject_id"]}
    reviewed = cli("review", "import", "recovery", "--evidence", "-",
                   data=json.dumps(code_evidence))
    assert reviewed.exit_code == 0, reviewed.output
    assert derive_state(events_path(root))["recovery"].current_state == "READY_TO_MERGE"
    attested = cli("attest", "write", "recovery", "--format", "v3")
    assert attested.exit_code == 0, attested.output
    record = parse_v3_line((harness / "attestations/v3/recovery.jsonl").read_bytes())
    assert record["authorization"] == authorization
    assert record["recognition_basis"]["plan"]["mode"] == "recovery"
    assert record["recognition_basis"]["code"]["mode"] == "recovery"
    git(root, "add", ".harness/attestations/v3/recovery.jsonl")
    git(root, "commit", "-qm", "retain signed transition evidence")
    verdict = verify_v3_transition(root, record, base=base, head="HEAD",
                                   repository_id="owner/project", target_ref="refs/heads/main")
    assert verdict["target_policy_digest"] == target["policy_digest"]
    verified = cli("--json", "attest", "verify", "--base", base, "--head", "HEAD",
                   "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output)["data"]["attestations"] == ["recovery"]
    replayed = verify_v2_activation(root, trusted_commit="HEAD", repository_id="owner/project",
                                    target_ref="refs/heads/main")
    assert replayed["policy_digest"] == target["policy_digest"]
    assert replayed["predecessor_base"] == base
    with pytest.raises(ApprovalError):
        verify_v2_activation(root, trusted_commit="HEAD", repository_id="owner/other",
                             target_ref="refs/heads/main")
    active_base = git(root, "rev-parse", "HEAD")
    installed = verify_with_installed_base(root, base, active_base, label="activation-reader")
    assert installed.returncode == 0, installed.stdout + installed.stderr
    git(root, "update-ref", "refs/heads/main", active_base)
    continued = cli("implementation", "start", "carry")
    assert continued.exit_code == 0, continued.output
    unlisted = cli("implementation", "start", "another")
    assert unlisted.exit_code == 2, unlisted.output
    assert "continuation list" in unlisted.output
    git(root, "switch", "-qc", "carried-approval")
    (root / "recovery-notes.txt").write_text("Retained policy recovery notes\n", encoding="utf-8")
    git(root, "add", "recovery-notes.txt")
    git(root, "commit", "-qm", "implement a carried plan")
    carry_assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                        "reasons": ["Complete the approved recovery notes"],
                        "references": ["recovery-notes.txt"]}
    recorded = cli("implementation", "record", "carry", "--assessment", "-",
                   data=json.dumps(carry_assessment))
    assert recorded.exit_code == 0, recorded.output
    completed = cli("done", "carry")
    assert completed.exit_code == 0, completed.output
    carried = cli("attest", "write", "carry", "--format", "v3")
    assert carried.exit_code == 0, carried.output
    carry_record = parse_v3_line((harness / "attestations/v3/carry.jsonl").read_bytes())
    assert carry_record["recognition_basis"]["plan"]["mode"] == "continued_plan"
    git(root, "add", ".harness/attestations/v3/carry.jsonl")
    git(root, "commit", "-qm", "retain the carried approval")
    carry_verified = cli("attest", "verify", "--base", active_base, "--head", "HEAD",
                         "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert carry_verified.exit_code == 0, carry_verified.output
    git(root, "switch", "-q", "candidate")
    assert cli("change", "start", "after-activation", "--framework", "plain").exit_code == 0
    ready = cli("plan", "ready", "after-activation", "--plan", "plan.md", "--scope", "[plan.md]",
                "--commitment", "goal=Deliver under the activated policy")
    assert ready.exit_code == 0, ready.output
    current_subject = derive_state(events_path(root))["after-activation"].pending_revision[
        "subject"]["subject_id"]
    signed = {"version": "signed-plan-decision/v1", "repository_id": "owner/project",
              "target_ref": "refs/heads/main", "policy_digest": target["policy_digest"],
              "change_id": "after-activation", "subject_id": current_subject,
              "decision": "approve", "evidence_id": "maintainer-plan", "supersedes": None,
              "key_id": authority["keys"][0]["key_id"]}
    signed["signature"] = base64.b64encode(key.sign(canonical_json(signed).encode())).decode()
    signed_evidence = {"version": "review-evidence/v1", "evidence_id": "maintainer-plan",
                       "kind": "plan", "subject_id": current_subject, "decision": "approve",
                       "process": {"id": "maintainer-plan-review",
                                   "version": "maintainer-plan-review/v1"},
                       "issuer": "maintainer", "form": "signed-plan-decision",
                       "original_evidence": signed,
                       "provenance": {"policy_digest": target["policy_digest"]}}
    altered_evidence = deepcopy(signed_evidence)
    altered_evidence["original_evidence"]["subject_id"] = "plan:" + "0" * 64
    assert cli("review", "import", "after-activation", "--evidence", "-",
               data=json.dumps(altered_evidence)).exit_code == 2
    imported = cli("review", "import", "after-activation", "--evidence", "-",
                   data=json.dumps(signed_evidence))
    assert imported.exit_code == 0, imported.output
    assert derive_state(events_path(root))["after-activation"].current_state == "PLAN_APPROVED"
    started = cli("implementation", "start", "after-activation")
    assert started.exit_code == 0, started.output
    (root / "ordinary.txt").write_text("ordinary delivery\n", encoding="utf-8")
    git(root, "add", "ordinary.txt")
    git(root, "commit", "-qm", "ordinary change after activation")
    ordinary_assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                           "reasons": ["Implement the approved ordinary change."],
                           "references": ["ordinary.txt"]}
    recorded = cli("implementation", "record", "after-activation", "--assessment", "-",
                   data=json.dumps(ordinary_assessment))
    assert recorded.exit_code == 0, recorded.output
    completed = cli("done", "after-activation")
    assert completed.exit_code == 0, completed.output
    ordinary_state = derive_state(events_path(root))["after-activation"]
    assert ordinary_state.current_state == "READY_TO_MERGE"
    assert ordinary_state.event_counts["code_review_not_required"] == 1
    assert ordinary_state.current_verification["check_evidence"][
        "builtin_checks_version"] == "keepsail-baseline/v2"
    status = cli("--json", "status", "after-activation")
    assert status.exit_code == 0, status.output
    shown = json.loads(status.output)["data"]["changes"][0]["no_review_decision"]
    assert shown["base_matches"] is True
    assert shown["policy_digest"] == target["policy_digest"]
    report = cli("--json", "report")
    assert report.exit_code == 0, report.output
    assert any(item["change_id"] == "after-activation"
               for item in json.loads(report.output)["data"]["no_review_decisions"])
    ordinary_attested = cli("attest", "write", "after-activation", "--format", "v3")
    assert ordinary_attested.exit_code == 0, ordinary_attested.output
    git(root, "add", ".harness/attestations/v3/after-activation.jsonl")
    git(root, "commit", "-qm", "retain ordinary v3 delivery evidence")
    ordinary_verified = cli("--json", "attest", "verify", "--base", active_base, "--head", "HEAD",
                            "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert ordinary_verified.exit_code == 0, ordinary_verified.output
    decision = json.loads(ordinary_verified.output)["data"]["delivery_decisions"][
        "after-activation"]
    assert decision["code_review_required"] is False
    assert decision["policy_digest"] == target["policy_digest"]
    ordinary_head = git(root, "rev-parse", "HEAD")
    installed = verify_with_installed_base(root, active_base, ordinary_head,
                                           label="active-policy-reader")
    assert installed.returncode == 0, installed.stdout + installed.stderr
    git(root, "update-ref", "refs/heads/main", base)
    git(root, "switch", "-qc", "downgrade-case")
    old_attestation = harness / "attestations/v2/legacy.jsonl"
    old_attestation.parent.mkdir(parents=True, exist_ok=True)
    old_attestation.write_text("{}\n", encoding="utf-8")
    git(root, "add", ".harness/attestations/v2/legacy.jsonl")
    git(root, "commit", "-qm", "attempt a post-activation format downgrade")
    downgrade = cli("--json", "attest", "verify", "--base", active_base, "--head", "HEAD",
                    "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert downgrade.exit_code == 2, downgrade.output
    assert "active policy requires v3 evidence" in downgrade.output
    git(root, "switch", "-q", "candidate")
    assert cli("attest", "verify", "--base", base, "--head", active_base).exit_code == 2
    assert cli("attest", "verify", "--base", base, "--head", active_base,
               "--repository-id", "owner/other", "--target-ref", "refs/heads/main").exit_code == 2
    altered = deepcopy(record)
    altered["recognition_basis"] = {kind: {"mode": "current", "policy_digest":
                                               policy["process"]["policy_digest"]}
                                      for kind in ("plan", "code")}
    altered["digest"] = digest_record({k: v for k, v in altered.items() if k != "digest"})
    with pytest.raises(ApprovalError, match="committed Git blob"):
        verify_v3_transition(root, altered, base=base, head=active_base,
                             repository_id="owner/project", target_ref="refs/heads/main")
    attestation_path = harness / "attestations/v3/recovery.jsonl"
    committed_bytes = attestation_path.read_bytes()
    attestation_path.write_bytes(b"untrusted working tree content\n")
    assert cli("attest", "verify", "--base", base, "--head", active_base,
               "--repository-id", "owner/project", "--target-ref", "refs/heads/main").exit_code == 0
    attestation_path.write_bytes(committed_bytes)

    def prepare_v2_change(change, scope):
        started = cli("change", "start", change, "--framework", "plain")
        assert started.exit_code == 0, started.output
        ready = cli("plan", "ready", change, "--plan", "plan.md", "--scope", f"[{scope}]",
                    "--commitment", "goal=Deliver the authorized policy change")
        assert ready.exit_code == 0, ready.output
        return derive_state(events_path(root))[change].pending_revision["subject"]["subject_id"]

    def approve_v2_plan(change, plan_subject, policy_digest, signing_key, key_id):
        body = {"version": "signed-plan-decision/v1", "repository_id": "owner/project",
                "target_ref": "refs/heads/main", "policy_digest": policy_digest,
                "change_id": change, "subject_id": plan_subject, "decision": "approve",
                "evidence_id": f"signed-{change}", "supersedes": None, "key_id": key_id}
        body["signature"] = base64.b64encode(
            signing_key.sign(canonical_json(body).encode())
        ).decode()
        item = {"version": "review-evidence/v1", "evidence_id": f"signed-{change}",
                "kind": "plan", "subject_id": plan_subject, "decision": "approve",
                "process": {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1"},
                "issuer": "maintainer", "form": "signed-plan-decision", "original_evidence": body,
                "provenance": {"policy_digest": policy_digest}}
        return cli("review", "import", change, "--evidence", "-", data=json.dumps(item))

    def import_v2_authorization(change, body, signing_key, proposed_path=None):
        signed_body = deepcopy(body)
        signed_body["signature"] = base64.b64encode(
            signing_key.sign(canonical_json(signed_body).encode())).decode()
        args = ["policy", "authorization", "import", change, "--evidence", "-",
                "--repository-id", "owner/project", "--target-ref", "refs/heads/main"]
        if proposed_path is not None:
            args.extend(["--target-authority", str(proposed_path)])
        return cli(*args, data=json.dumps(signed_body))

    def record_implementation(change, path):
        assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                      "reasons": ["Implement the signed policy change."], "references": [path]}
        result = cli("implementation", "record", change, "--assessment", "-",
                     data=json.dumps(assessment))
        assert result.exit_code == 0, result.output

    git(root, "update-ref", "refs/heads/main", ordinary_head)
    next_policy = deepcopy(target)
    next_policy["code_review"] = {"mode": "full"}
    next_policy["activation"] = {"kind": "transition", "change": "next-policy"}
    next_policy["policy_digest"] = digest_record({k: v for k, v in next_policy.items()
                                                   if k != "policy_digest"})
    next_subject = prepare_v2_change("next-policy", ".harness/review-recognition.yaml")
    next_authorization = {
        "version": "policy-authorization/v1", "repository_id": "owner/project",
        "target_ref": "refs/heads/main", "base_sha": ordinary_head,
        "predecessor_policy_digest": target["policy_digest"],
        "target_policy_digest": next_policy["policy_digest"], "change_id": "next-policy",
        "plan_subject_id": next_subject, "kind": "transition", "decision": "approve",
        "permitted_paths": ["plan.md", ".harness/review-recognition.yaml"],
        "key_id": authority["keys"][0]["key_id"], "obligation_changes": [],
    }
    imported = import_v2_authorization("next-policy", next_authorization, key)
    assert imported.exit_code == 0, imported.output
    approved = approve_v2_plan("next-policy", next_subject, target["policy_digest"], key,
                               authority["keys"][0]["key_id"])
    assert approved.exit_code == 0, approved.output
    assert cli("implementation", "start", "next-policy").exit_code == 0
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(next_policy), encoding="utf-8")
    git(root, "add", ".harness/review-recognition.yaml")
    git(root, "commit", "-qm", "propose the next policy")
    record_implementation("next-policy", ".harness/review-recognition.yaml")
    completed = cli("done", "next-policy")
    assert completed.exit_code == 0, completed.output
    assert derive_state(events_path(root))["next-policy"].current_state == "READY_TO_MERGE"
    exported = cli("attest", "write", "next-policy", "--format", "v3")
    assert exported.exit_code == 0, exported.output
    git(root, "add", ".harness/attestations/v3/next-policy.jsonl")
    git(root, "commit", "-qm", "retain the next policy transition")
    next_head = git(root, "rev-parse", "HEAD")
    verified = cli("attest", "verify", "--base", ordinary_head, "--head", next_head,
                   "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert verified.exit_code == 0, verified.output
    assert verify_v2_activation(root, trusted_commit=next_head, repository_id="owner/project",
                                target_ref="refs/heads/main")["policy_digest"] == next_policy[
                                    "policy_digest"]

    git(root, "update-ref", "refs/heads/main", next_head)
    new_key = Ed25519PrivateKey.generate()
    new_public = new_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    new_authority = deepcopy(authority)
    new_authority["keys"] = [{"key_id": sha256(new_public).hexdigest(), "algorithm": "ed25519",
                              "public_key": base64.b64encode(new_public).decode("ascii"),
                              "purposes": ["policy-transition", "plan-decision"]}]
    proposal = root.parent / (root.name + "-rotated-authority.yaml")
    proposal.write_text(yaml.safe_dump(new_authority), encoding="utf-8")
    rotation_subject = prepare_v2_change("rotate-key", ".harness/policy-authority.yaml")
    rotation_authorization = {
        "version": "policy-authorization/v1", "repository_id": "owner/project",
        "target_ref": "refs/heads/main", "base_sha": next_head,
        "predecessor_policy_digest": next_policy["policy_digest"],
        "target_policy_digest": next_policy["policy_digest"], "change_id": "rotate-key",
        "plan_subject_id": rotation_subject, "kind": "rotate_key", "decision": "approve",
        "permitted_paths": ["plan.md", ".harness/policy-authority.yaml"],
        "key_id": authority["keys"][0]["key_id"],
        "predecessor_authority_digest": parse_authority(authority).digest,
        "target_authority_digest": parse_authority(new_authority).digest,
    }
    imported = import_v2_authorization("rotate-key", rotation_authorization, key, proposal)
    assert imported.exit_code == 0, imported.output
    approved = approve_v2_plan("rotate-key", rotation_subject, next_policy["policy_digest"], key,
                               authority["keys"][0]["key_id"])
    assert approved.exit_code == 0, approved.output
    assert cli("implementation", "start", "rotate-key").exit_code == 0
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(new_authority), encoding="utf-8")
    git(root, "add", ".harness/policy-authority.yaml")
    git(root, "commit", "-qm", "propose the rotated key")
    record_implementation("rotate-key", ".harness/policy-authority.yaml")
    completed = cli("done", "rotate-key")
    assert completed.exit_code == 0, completed.output
    rotation_state = derive_state(events_path(root))["rotate-key"]
    assert rotation_state.current_state == "AWAITING_CODE_REVIEW"
    review = {"version": "review-evidence/v1", "evidence_id": "rotation-code", "kind": "code",
              "subject_id": rotation_state.current_code_subject["subject_id"],
              "decision": "approve",
              "process": {"id": "old-review", "version": "v1"}, "issuer": "old-reviewer",
              "form": "json", "original_evidence": {"decision": "approve"},
              "provenance": {"policy_digest": next_policy["policy_digest"]}}
    reviewed = cli("review", "import", "rotate-key", "--evidence", "-", data=json.dumps(review))
    assert reviewed.exit_code == 0, reviewed.output
    exported = cli("attest", "write", "rotate-key", "--format", "v3")
    assert exported.exit_code == 0, exported.output
    git(root, "add", ".harness/attestations/v3/rotate-key.jsonl")
    git(root, "commit", "-qm", "retain the authorized key rotation")
    rotated_head = git(root, "rev-parse", "HEAD")
    verified = cli("attest", "verify", "--base", next_head, "--head", rotated_head,
                   "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert verified.exit_code == 0, verified.output
    rotation = verify_v2_activation(root, trusted_commit=rotated_head,
                                    repository_id="owner/project", target_ref="refs/heads/main")
    assert rotation["authority_rotation"]["change"] == "rotate-key"
    git(root, "update-ref", "refs/heads/main", rotated_head)
    after_subject = prepare_v2_change("after-rotation", ".harness/review-recognition.yaml")
    old_signed = approve_v2_plan("after-rotation", after_subject, next_policy["policy_digest"], key,
                                 authority["keys"][0]["key_id"])
    assert old_signed.exit_code == 2, old_signed.output
    newly_signed = approve_v2_plan("after-rotation", after_subject, next_policy["policy_digest"],
                                   new_key, new_authority["keys"][0]["key_id"])
    assert newly_signed.exit_code == 0, newly_signed.output
    widened = deepcopy(new_authority)
    widened["keys"][0]["purposes"].append("policy-recovery")
    proposal.write_text(yaml.safe_dump(widened), encoding="utf-8")
    widened_subject = prepare_v2_change("widen-purpose", ".harness/policy-authority.yaml")
    widened_authorization = {
        "version": "policy-authorization/v1", "repository_id": "owner/project",
        "target_ref": "refs/heads/main", "base_sha": rotated_head,
        "predecessor_policy_digest": next_policy["policy_digest"],
        "target_policy_digest": next_policy["policy_digest"], "change_id": "widen-purpose",
        "plan_subject_id": widened_subject, "kind": "rotate_key", "decision": "approve",
        "permitted_paths": ["plan.md", ".harness/policy-authority.yaml"],
        "key_id": new_authority["keys"][0]["key_id"],
        "predecessor_authority_digest": parse_authority(new_authority).digest,
        "target_authority_digest": parse_authority(widened).digest,
    }
    widened_result = import_v2_authorization("widen-purpose", widened_authorization,
                                              new_key, proposal)
    assert widened_result.exit_code == 2, widened_result.output
    assert "cannot add purposes" in widened_result.output
    git(root, "switch", "-qc", "recovery-widen-case", active_base)
    git(root, "update-ref", "refs/heads/main", base)
    (root / "business.py").write_text("print('outside recovery')\n", encoding="utf-8")
    git(root, "add", "business.py")
    git(root, "commit", "-qm", "attempt to widen the recovery")
    assert cli("review", "import", "recovery", "--evidence", "-",
               data=json.dumps(code_evidence)).exit_code == 2
    reopened = cli("implementation", "reopen", "recovery", "--reason", "exercise widened scope")
    assert reopened.exit_code == 0, reopened.output
    recorded = cli("implementation", "record", "recovery", "--assessment", "-",
                   data=json.dumps(assessment))
    assert recorded.exit_code == 0, recorded.output
    completed = cli("done", "recovery")
    assert completed.exit_code == 2, completed.output
    assert "authorization" in completed.output
