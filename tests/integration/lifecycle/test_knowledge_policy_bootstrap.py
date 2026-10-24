"""First policy delivery uses normal work authorization, never candidate authority."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from keepsail.cli import main
from keepsail.core.approval import ApprovalError, make_code_subject, recognition_policy_digest
from keepsail.core.knowledge import KnowledgeError, load_policy, policy_digest
from keepsail.core.reducer import derive_state
from keepsail.engineering.attestation import (
    _knowledge_attestation,
    parse_name_status,
    verify_attestations,
)
from tests.unit.core.test_knowledge import Workspace, git, policy, version


class BootstrapWorkspace(Workspace):
    def __init__(self, root: Path):
        self.root, self.runner, self.counter = root, CliRunner(), 0
        (root / ".harness").mkdir()
        self.review = {
            "version": "review-recognition/v1", "enabled": True,
            "process": {"id": "owner-review", "version": "1", "kinds": ["plan", "code"],
                        "issuers": ["owner"], "evidence_forms": ["json"]},
        }
        self.review["process"]["policy_digest"] = recognition_policy_digest(self.review)
        (root / ".harness/review-recognition.yaml").write_text(
            yaml.safe_dump(self.review), encoding="utf-8"
        )
        (root / "plan.md").write_text("# Deliver a first policy candidate\n", encoding="utf-8")
        (root / ".gitignore").write_text(
            ".harness/events.jsonl\n.harness/state.yaml\n.harness/.*.lock\ninput*.json\n",
            encoding="utf-8",
        )
        self.marker = root.parent / (root.name + "-check-ran")
        (root / "check.py").write_text(
            "from pathlib import Path\nimport sys, yaml\n"
            "from keepsail.core.knowledge import validate_policy\n"
            "validate_policy(yaml.safe_load(Path('.harness/knowledge-recognition.yaml').read_text()))\n"
            "Path(sys.argv[1]).write_text('validated candidate')\n", encoding="utf-8",
        )
        config = {
            "layers": {"baseline": {"enabled": False}, "framework_adapter": {"enabled": False},
                       "user_checks": {"enabled": True}},
            "defaults": {"timeout_seconds": 30, "must_pass": True, "capture": "both",
                         "workdir": ".", "env": {}},
            "execution": {"mode": "sequential", "max_parallelism": 1, "fail_fast": False},
            "checks": [{"id": "candidate-schema", "command": [sys.executable, "-B", "check.py",
                                                               str(self.marker)]}],
            "adapter_provided": [],
        }
        (root / ".harness/verification.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "fixture@example.invalid")
        git(root, "config", "user.name", "Bootstrap fixture")
        git(root, "add", ".")
        git(root, "commit", "-qm", "baseline without knowledge policy")
        git(root, "switch", "-qc", "candidate")
        self.cli("change", "start", "change-a", "--framework", "plain")

    def candidate(self, raw: dict | None = None) -> Path:
        path = self.root / ".harness/knowledge-recognition.yaml"
        path.write_text(yaml.safe_dump(policy() if raw is None else raw), encoding="utf-8")
        return path

    def approve(self, slug: str, kind: str, subject: str) -> None:
        evidence = {
            "version": "review-evidence/v1", "evidence_id": f"fixture-{slug}-{kind}",
            "kind": kind, "subject_id": subject, "decision": "approve", "issuer": "owner",
            "process": {"id": "owner-review", "version": "1"},
            "original_evidence": {"decision": "approve", "source": "isolated test fixture only"},
            "provenance": {"policy_digest": self.review["process"]["policy_digest"]},
        }
        self.cli("review", "import", slug, "--evidence", str(self.write(evidence)))

    def plan(self, slug: str = "change-a") -> None:
        self.cli("plan", "ready", slug, "--plan", "plan.md", "--scope",
                 "[plan.md, .harness/knowledge-recognition.yaml]", "--commitment",
                 "P1=Deliver an owner-controlled first policy candidate")
        state = derive_state(self.root / ".harness/events.jsonl")[slug]
        self.approve(slug, "plan", state.pending_revision["subject"]["subject_id"])


@pytest.mark.parametrize("before_plan", [True, False])
def test_first_candidate_completes_normal_delivery_without_authority(tmp_path, before_plan):
    w = BootstrapWorkspace(tmp_path)
    if before_plan:
        w.candidate()
    w.plan()
    w.cli("implementation", "start", "change-a")
    if not before_plan:
        w.candidate()
    git(tmp_path, "add", ".harness/knowledge-recognition.yaml")
    git(tmp_path, "commit", "-qm", "deliver candidate without activating it")
    log = tmp_path / ".harness/events.jsonl"
    state = derive_state(log)["change-a"]
    original_plan = state.effective_approval.copy()
    assert "knowledge_basis" not in state.effective_approval["subject"]
    subject = make_code_subject(tmp_path, change_id="change-a",
                                approval_id=state.effective_approval["approval_id"], base="main")
    assert ".harness/knowledge-recognition.yaml" in {r["path"] for r in subject["manifest"]}
    assert "knowledge_basis" not in subject
    assessment = {
        "assessment": {"approval_id": state.effective_approval["approval_id"],
                       "affected_commitments": ["P1"], "conclusion": "within_approval",
                       "reasons": ["First candidate within the approved commitment"],
                       "references": [".harness/knowledge-recognition.yaml"]},
        "coverage": [{"path": r["path"]} for r in subject["manifest"]],
    }
    w.cli("implementation", "record", "change-a", "--assessment", str(w.write(assessment)))
    before = log.read_bytes()
    shown = w.cli("knowledge", "show")["data"]
    assert shown["coverage"] == "not_recorded"
    assert shown["policy_candidate"] == {
        "status": "candidate", "policy_digest": policy()["policy_digest"]
    }
    w.submit("propose", w.operation(version=version()), code=2)
    w.submit("import", w.operation(evidence={}), code=2)
    w.cli("knowledge", "deliver", "change-a", "--operation-id", "no-authority",
          "--expected-revision", w.revision(), code=3)
    assert log.read_bytes() == before
    w.cli("done", "change-a")
    assert w.marker.read_text() == "validated candidate"
    state = derive_state(log)["change-a"]
    assert state.current_verification["outcome"] == "passed"
    w.approve("change-a", "code", state.current_code_subject["subject_id"])
    w.cli("attest", "write", "change-a")
    att = tmp_path / ".harness/attestations/change-a.jsonl"
    assert not any(json.loads(line)["type"].startswith("knowledge_")
                   for line in att.read_text().splitlines())
    git(tmp_path, "add", ".harness/attestations/change-a.jsonl")
    git(tmp_path, "commit", "-qm", "retain ordinary delivery evidence")
    diff = parse_name_status(git(tmp_path, "diff", "--name-status", "main...HEAD"))
    inactive_base = git(tmp_path, "rev-parse", "main")
    # The committed verifier must ignore mutable candidate configuration.
    candidate = w.candidate({"enabled": False})
    verdict = verify_attestations(tmp_path, diff, base="main", head="HEAD")
    assert verdict.ok, verdict.blockers
    valid_head = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "add", ".harness/knowledge-recognition.yaml")
    git(tmp_path, "commit", "-qm", "invalid candidate negative fixture")
    # Explicit target, rather than checkout HEAD or worktree, selects the candidate.
    verdict = verify_attestations(tmp_path, diff, base="main", head=valid_head)
    assert verdict.ok, verdict.blockers
    with pytest.raises(KnowledgeError, match="explicitly enable"):
        _knowledge_attestation(tmp_path, att, state, base="main", head="HEAD")
    # Forged basis/checkpoint must not confer authority, even for a valid candidate.
    forged = deepcopy(state)
    forged.current_code_subject["knowledge_basis"] = {"digest": "forged"}
    with pytest.raises(ApprovalError, match="not activated"):
        _knowledge_attestation(tmp_path, att, forged, base="main", head=valid_head)
    original_attestation = att.read_text(encoding="utf-8")
    event = json.loads(original_attestation.splitlines()[-1])
    event.update(type="knowledge_checkpointed", payload={})
    att.write_text(original_attestation + json.dumps(event) + "\n", encoding="utf-8")
    with pytest.raises(ApprovalError, match="not activated"):
        _knowledge_attestation(tmp_path, att, state, base="main", head=valid_head)
    att.write_text(original_attestation, encoding="utf-8")
    w.candidate()
    git(tmp_path, "add", ".harness/knowledge-recognition.yaml")
    git(tmp_path, "commit", "-qm", "restore valid candidate fixture")
    # Simulate owner-controlled baseline advancement only inside this fixture.
    git(tmp_path, "branch", "-f", "main", "HEAD")
    assert load_policy(tmp_path) == policy()
    assert derive_state(log)["change-a"].effective_approval == original_plan
    w.cli("change", "start", "change-b", "--framework", "plain")
    w.plan("change-b")
    w.cli("implementation", "start", "change-b", code=2)
    w.cli("knowledge", "deliver", "change-b", "--operation-id", "empty-set-delivery",
          "--expected-revision", w.revision())
    w.cli("implementation", "start", "change-b")
    candidate.unlink()
    w.cli("knowledge", "show", code=3)
    log.unlink()
    (tmp_path / ".harness/state.yaml").unlink(missing_ok=True)
    verdict = verify_attestations(tmp_path, diff, base=inactive_base, head="HEAD")
    assert verdict.ok, verdict.blockers


@pytest.mark.parametrize("mutation", ["schema", "digest", "requirements", "yaml", "unreadable"])
def test_invalid_first_candidate_fails_without_lifecycle_append(tmp_path, mutation):
    w = BootstrapWorkspace(tmp_path)
    raw = policy()
    if mutation == "schema":
        raw["enabled"] = False
    elif mutation == "digest":
        raw["policy_digest"] = "incorrect"
    elif mutation == "requirements":
        raw["requirements"] = {"silently-enable": True}
        raw["policy_digest"] = policy_digest(raw)
    path = w.candidate(raw)
    if mutation == "yaml":
        path.write_text("version: [", encoding="utf-8")
    elif mutation == "unreadable":
        path.unlink()
        path.mkdir()
    log = tmp_path / ".harness/events.jsonl"
    before = log.read_bytes()
    w.cli("knowledge", "show", code=3)
    result = w.runner.invoke(main, [
        "--workspace", str(tmp_path), "plan", "ready", "change-a", "--plan", "plan.md",
        "--scope", "[plan.md]", "--commitment", "P1=test",
    ])
    assert result.exit_code != 0
    assert log.read_bytes() == before


def test_missing_trusted_base_is_not_inactive_configuration(tmp_path):
    BootstrapWorkspace(tmp_path)
    with pytest.raises(KnowledgeError) as error:
        load_policy(tmp_path, ref="nonexistent-trusted-commit")
    assert error.value.exit_code == 4
    git(tmp_path, "branch", "-D", "main")
    with pytest.raises(KnowledgeError) as error:
        load_policy(tmp_path)
    assert error.value.exit_code == 4


def test_first_candidate_cannot_hide_corrupt_knowledge_ledger(tmp_path):
    w = BootstrapWorkspace(tmp_path)
    w.candidate()
    log = tmp_path / ".harness/events.jsonl"
    with log.open("a", encoding="utf-8") as stream:
        stream.write('{"type":"knowledge_imported"')
    before = log.read_bytes()
    w.cli("knowledge", "show", code=2)
    assert log.read_bytes() == before


def test_malformed_trusted_policy_is_not_inactive_configuration(tmp_path):
    w = BootstrapWorkspace(tmp_path)
    w.candidate({"enabled": True})
    git(tmp_path, "add", ".harness/knowledge-recognition.yaml")
    git(tmp_path, "commit", "-qm", "corrupt trusted policy negative fixture")
    git(tmp_path, "branch", "-f", "main", "HEAD")
    w.candidate()
    log = tmp_path / ".harness/events.jsonl"
    before = log.read_bytes()
    w.cli("knowledge", "show", code=3)
    assert log.read_bytes() == before
