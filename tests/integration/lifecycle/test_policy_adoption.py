"""Adoption (cold start): the owner's first enabled policy, then ordinary deliveries."""

import json
import subprocess

import pytest
import yaml
from click.testing import CliRunner

from keepsail.cli import main
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def cli(root, *args, data=None):
    text = json.dumps(data) if isinstance(data, dict) else data
    return CliRunner().invoke(main, ["--workspace", str(root), *args], input=text)


def ok(root, *args, data=None):
    result = cli(root, *args, data=data)
    assert result.exit_code == 0, (args, result.output)
    return result


def empty_repo(path):
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "fixture@example.invalid")
    git(path, "config", "user.name", "fixture")
    git(path, "config", "core.autocrlf", "false")
    return path


def policy(root):
    return yaml.safe_load((root / ".harness/review-recognition.yaml").read_text(encoding="utf-8"))


def commit(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


def first_delivery(root, process):
    """change start -> plan ready -> owner review import -> implement -> done -> verify."""
    adopted = policy(root)
    ok(root, "change", "start", "first-change", "--framework", "plain")
    (root / "plan.md").write_text("# First change\n", encoding="utf-8")
    ok(root, "plan", "ready", "first-change", "--plan", "plan.md", "--scope", "[plan.md]",
       "--commitment", "goal=Deliver the first change")
    subject = derive_state(events_path(root))["first-change"].pending_revision["subject"][
        "subject_id"]
    ok(root, "review", "import", "first-change", "--evidence", "-", data={
        "version": "review-evidence/v1", "evidence_id": "first-plan", "kind": "plan",
        "subject_id": subject, "decision": "approve",
        "process": {"id": process["id"], "version": process["version"]},
        "issuer": process["issuer"], "form": "json", "original_evidence": {"decision": "approve"},
        "provenance": {"policy_digest": adopted["policy_digest"]}})
    ok(root, "implementation", "start", "first-change")
    (root / "feature.txt").write_text("feature\n", encoding="utf-8")
    commit(root, "first change")
    ok(root, "implementation", "record", "first-change", "--assessment", "-", data={
        "affected_commitments": ["goal"], "conclusion": "within_approval",
        "reasons": ["Implement the first change."], "references": ["feature.txt", "plan.md"]})
    ok(root, "verify")
    ok(root, "done", "first-change")
    assert derive_state(events_path(root))["first-change"].current_state == "READY_TO_MERGE"
    ok(root, "attest", "write", "first-change")
    commit(root, "retain the first delivery")


@pytest.mark.parametrize("entry", ["init", "policy-enable"])
def test_owner_adoption_then_the_first_change_reaches_the_merge_gate(tmp_path, entry):
    root = empty_repo(tmp_path / "repo")
    if entry == "init":
        result = ok(root, "init", "--no-agent", "--recognize", "owner", "--code-review", "off")
        assert "adopted the enabled policy" in result.output
    else:
        ok(root, "init", "--no-agent")
        assert policy(root)["enabled"] is False
        result = ok(root, "policy", "enable", "--code-review", "off")
        assert "adoption commit" in result.output
    adopted = policy(root)
    assert adopted["version"] == "review-recognition/v2" and adopted["enabled"] is True
    assert "activation" not in adopted
    assert adopted["processes_by_kind"] == {"plan": {
        "id": "owner-plan-review", "version": "owner-plan-review/v1", "issuers": ["owner"],
        "evidence_forms": ["json"], "requirements": {}}}
    assert not (root / ".harness/policy-authority.yaml").exists()
    # The owner commits the adoption to the target branch; trust starts here.
    base = commit(root, "adopt keepsail")
    git(root, "switch", "-qc", "first-change")
    first_delivery(root, {"id": "owner-plan-review", "version": "owner-plan-review/v1",
                          "issuer": "owner"})
    verified = cli(root, "--json", "attest", "verify", "--base", base, "--head", "HEAD")
    assert verified.exit_code == 0, verified.output
    # Once a policy is enabled on the trusted base, adoption cannot be repeated.
    refused = cli(root, "policy", "enable", "--code-review", "full")
    assert refused.exit_code == 2 and "policy accept" in refused.output


def test_external_process_choice_records_that_process_for_plan_and_code(tmp_path):
    root = empty_repo(tmp_path / "repo")
    ok(root, "init", "--no-agent", "--recognize", "external", "--process-id", "team-review",
       "--process-version", "team-review/v3", "--issuer", "review-bot",
       "--code-review", "scope", "--code-review-scope", "src")
    adopted = policy(root)
    expected = {"id": "team-review", "version": "team-review/v3", "issuers": ["review-bot"],
                "evidence_forms": ["json"], "requirements": {}}
    assert adopted["processes_by_kind"] == {"plan": expected, "code": expected}
    assert adopted["code_review"] == {"mode": "scope", "scope": ["src"]}
    incomplete = empty_repo(tmp_path / "incomplete")
    result = cli(incomplete, "init", "--no-agent", "--recognize", "external",
                 "--code-review", "off")
    assert result.exit_code != 0 and "id, version and issuer" in result.output


def test_non_interactive_init_without_a_choice_keeps_the_disabled_skeleton(tmp_path):
    root = empty_repo(tmp_path / "repo")
    result = ok(root, "init", "--no-agent")
    assert "policy enable" in result.output
    assert policy(root)["enabled"] is False
    assert cli(root, "policy", "enable").exit_code == 2  # a code review choice is required


@pytest.mark.parametrize("enabled", [False, True])
def test_init_force_preserves_an_existing_policy_and_never_asks(tmp_path, enabled):
    root = empty_repo(tmp_path / "repo")
    ok(root, "init", "--no-agent")
    if enabled:
        ok(root, "policy", "enable", "--code-review", "off")
    before = (root / ".harness/review-recognition.yaml").read_bytes()
    result = ok(root, "init", "--force", "--no-agent", "--recognize", "owner",
                "--code-review", "full")
    assert (root / ".harness/review-recognition.yaml").read_bytes() == before
    hint = "policy enable" if not enabled else "policy accept"
    assert hint in result.output
