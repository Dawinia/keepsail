"""Candidate review policies cannot supply the authority that approves them."""

import json
import subprocess
from pathlib import Path

import yaml
from click.testing import CliRunner

from keepsail.cli import main
from keepsail.core.approval import recognition_policy_digest
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def recognition(process, issuer):
    result = {"version": "review-recognition/v1", "enabled": True,
              "process": {"id": process, "version": "v1", "kinds": ["plan", "code"],
                          "issuers": [issuer], "evidence_forms": ["json"]}}
    result["process"]["policy_digest"] = recognition_policy_digest(result)
    return result


def test_import_uses_committed_base_despite_candidate_policy_replacement(tmp_path: Path):
    root = tmp_path
    (root / ".harness").mkdir()
    baseline = recognition("old", "old-owner")
    path = root / ".harness/review-recognition.yaml"
    path.write_text(yaml.safe_dump(baseline), encoding="utf-8")
    (root / "plan.md").write_text("# Approved objective\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "add", ".")
    git(root, "commit", "-qm", "trusted base")
    base = git(root, "rev-parse", "HEAD")
    git(root, "switch", "-qc", "candidate")
    candidate = recognition("new", "new-owner")
    path.write_text(yaml.safe_dump(candidate), encoding="utf-8")
    runner = CliRunner()

    def cli(*args):
        return runner.invoke(main, ["--workspace", str(root), *args])

    started = cli("change", "start", "test", "--framework", "plain")
    assert started.exit_code == 0, started.output
    ready = cli("plan", "ready", "test", "--plan", "plan.md", "--scope", "[plan.md]",
                "--commitment", "goal=Approved objective")
    assert ready.exit_code == 0, ready.output
    subject = derive_state(events_path(root))["test"].pending_revision["subject"]["subject_id"]

    def evidence(policy, evidence_id):
        process = policy["process"]
        return json.dumps({
            "version": "review-evidence/v1", "evidence_id": evidence_id, "kind": "plan",
            "subject_id": subject, "decision": "approve",
            "process": {"id": process["id"], "version": process["version"]},
            "issuer": process["issuers"][0], "original_evidence": {"decision": "approve"},
            "provenance": {"policy_digest": process["policy_digest"]},
        })

    rejected = runner.invoke(main, ["--workspace", str(root), "review", "import", "test",
                                    "--evidence", "-"], input=evidence(candidate, "candidate"))
    assert rejected.exit_code == 2, rejected.output
    accepted = runner.invoke(main, ["--workspace", str(root), "--json", "review", "import",
                                   "test", "--evidence", "-"], input=evidence(baseline, "old"))
    assert accepted.exit_code == 0, accepted.output
    assert json.loads(accepted.output)["data"]["trusted_base"] == base
    assert derive_state(events_path(root))["test"].current_state == "PLAN_APPROVED"
