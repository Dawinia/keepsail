"""A candidate cannot remove the checks used to evaluate its own delivery."""

import json
import subprocess
import sys

import yaml
from click.testing import CliRunner

from keepsail.cli import main
from keepsail.core.approval import recognition_policy_digest
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state
from keepsail.core.verification_config import parse_verification_config, required_check_contract
from keepsail.engineering.attestation import parse_name_status_z, verify_attestations


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_candidate_check_removal_runs_old_check_and_blocks_done(tmp_path):
    root = tmp_path
    harness = root / ".harness"
    harness.mkdir()
    policy = {"version": "review-recognition/v1", "enabled": True, "process": {
        "id": "owner", "version": "v1", "kinds": ["plan", "code"],
        "issuers": ["owner"], "evidence_forms": ["json"]}}
    policy["process"]["policy_digest"] = recognition_policy_digest(policy)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    marker = root.parent / (root.name + "-trusted-check")
    script = f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')"
    config = {"layers": {"baseline": {"enabled": False}, "framework_adapter": {"enabled": False},
                         "user_checks": {"enabled": True}},
              "checks": [{"id": "trusted-test", "command": [sys.executable, "-c", script]}]}
    original = yaml.safe_dump(config)
    (harness / "verification.yaml").write_text(original, encoding="utf-8")
    (root / "plan.md").write_text("# Implement the product change\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "add", ".")
    git(root, "commit", "-qm", "trusted policy and required check")
    base = git(root, "rev-parse", "HEAD")
    git(root, "switch", "-qc", "candidate")
    runner = CliRunner()

    def cli(*args, data=None):
        return runner.invoke(main, ["--workspace", str(root), *args], input=data)

    assert cli("change", "start", "feature", "--framework", "plain").exit_code == 0
    ready = cli("plan", "ready", "feature", "--plan", "plan.md", "--scope", "[plan.md]",
                "--commitment", "goal=Implement the product change")
    assert ready.exit_code == 0, ready.output
    subject = derive_state(events_path(root))["feature"].pending_revision["subject"]["subject_id"]
    evidence = {"version": "review-evidence/v1", "evidence_id": "plan", "kind": "plan",
                "subject_id": subject, "decision": "approve", "issuer": "owner",
                "process": {"id": "owner", "version": "v1"},
                "original_evidence": {"decision": "approve"},
                "provenance": {"policy_digest": policy["process"]["policy_digest"]}}
    imported = cli("review", "import", "feature", "--evidence", "-", data=json.dumps(evidence))
    assert imported.exit_code == 0, imported.output
    assert cli("implementation", "start", "feature").exit_code == 0
    (harness / "verification.yaml").write_text("checks: []\n", encoding="utf-8")
    (root / "product.txt").write_text("changed\n", encoding="utf-8")
    git(root, "add", ".harness/verification.yaml", "product.txt")
    git(root, "commit", "-qm", "candidate removes required check")
    raw_diff = subprocess.check_output(
        ["git", "diff", "--name-status", "-z", "--find-renames", f"{base}...HEAD"], cwd=root,
    ).decode("utf-8")
    verdict = verify_attestations(root, parse_name_status_z(raw_diff), base=base, head="HEAD")
    assert any("require a verified v3 transition" in item for item in verdict.blockers)
    assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                  "reasons": ["Test the check policy boundary."], "references": ["product.txt"]}
    recorded = cli("implementation", "record", "feature", "--assessment", "-",
                   data=json.dumps(assessment))
    assert recorded.exit_code == 0, recorded.output
    verified = cli("verify", "feature")
    assert verified.exit_code == 0, verified.output
    assert marker.read_text() == "ran"
    verification = derive_state(events_path(root))["feature"].current_verification
    assert verification["check_evidence"]["required_checks_digest"] == required_check_contract(
        parse_verification_config(original))["digest"]
    blocked = cli("done", "feature")
    assert blocked.exit_code == 2, blocked.output
    assert "required check changes" in blocked.output
