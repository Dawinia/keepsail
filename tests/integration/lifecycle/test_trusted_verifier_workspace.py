"""Execute the workflow's actual evidence projection against real Git objects."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from keepsail.core.knowledge import KnowledgeError, read_inputs, validate_checkpoint
from keepsail.core.knowledge_checkpoint import make_checkpoint, resolve_facts
from keepsail.engineering.attestation import write_attestation
from tests.unit.core.test_knowledge import Workspace, git, policy, version


def projection_program() -> str:
    workflow = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / ".github/workflows/merge-gate.yml").read_text()
    )
    step = next(
        s
        for s in workflow["jobs"]["attest-verify"]["steps"]
        if s.get("name") == "Prepare trusted BASE workspace with exact target evidence"
    )
    return step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled", "skipped", ""])
def test_required_verifier_rejects_unsuccessful_candidate_acceptance(outcome):
    workflow = Path(__file__).resolve().parents[3] / ".github/workflows/merge-gate.yml"
    job = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]["attest-verify"]
    assert job["needs"] == "candidate-acceptance"
    assert job["if"] == "${{ always() }}"
    guard = next(
        step
        for step in job["steps"]
        if step.get("name") == "Require successful candidate acceptance"
    )
    assert guard["env"]["CANDIDATE_RESULT"] == "${{ needs.candidate-acceptance.result }}"
    bash = shutil.which("bash")
    if os.name == "nt":
        executable = shutil.which("git")
        git_bash = Path(executable).resolve().parents[1] / "bin/bash.exe" if executable else None
        bash = str(git_bash) if git_bash and git_bash.is_file() else None
    if bash is None:
        pytest.skip("workflow guard execution requires bash")
    result = subprocess.run(
        [bash, "-e", "-c", guard["run"]],
        env={**os.environ, "CANDIDATE_RESULT": outcome},
        capture_output=True,
    )
    assert (result.returncode == 0) == (outcome == "success")


@pytest.mark.parametrize("case", ["valid", "v2", "unknown-directory", "deep-directory",
                                  "missing-object", "symlink", "wrong-base"])
def test_workflow_projects_only_regular_target_evidence(tmp_path, case):
    source = tmp_path / "source"
    source.mkdir()
    (source / ".harness").mkdir()
    (source / "source.py").write_text("trusted source\n")
    git(source, "init", "-q", "-b", "main")
    git(source, "config", "user.email", "fixture@example.invalid")
    git(source, "config", "user.name", "Projection fixture")
    git(source, "add", ".")
    git(source, "commit", "-qm", "trusted base")
    base = git(source, "rev-parse", "HEAD")
    relative = {"v2": ".harness/attestations/v2/probe.jsonl",
                "unknown-directory": ".harness/attestations/unknown/probe.jsonl",
                "deep-directory": ".harness/attestations/v2/deep/probe.jsonl"}.get(
                    case, ".harness/attestations/probe.jsonl")
    attest = source / relative
    attest.parent.mkdir(parents=True)
    original = b'{"fixture":"exact original bytes"}\n'
    attest.write_bytes(original)
    (source / "source.py").write_text("candidate source must not be projected\n")
    (source / ".harness/knowledge-recognition.yaml").write_text("candidate policy\n")
    git(source, "add", ".")
    if case == "symlink":
        blob = (
            subprocess.check_output(
                ["git", "hash-object", "-w", "--stdin"], cwd=source, input=b"../../source.py"
            )
            .decode()
            .strip()
        )
        git(
            source,
            "update-index",
            "--cacheinfo",
            f"120000,{blob},.harness/attestations/probe.jsonl",
        )
    git(source, "commit", "-qm", "target evidence and candidate")
    head = git(source, "rev-parse", "HEAD")
    trusted = source / ".harness-trusted-base"
    subprocess.run(["git", "clone", "-q", "--shared", str(source), str(trusted)], check=True)
    git(trusted, "checkout", "-q", "--detach", base)
    result = subprocess.run(
        [sys.executable, "-c", projection_program()],
        capture_output=True,
        env={
            **os.environ,
            "GITHUB_WORKSPACE": str(source),
            "BASE_SHA": head if case == "wrong-base" else base,
            "HEAD_SHA": "0" * 40 if case == "missing-object" else head,
        },
    )
    assert (result.returncode == 0) == (case in {"valid", "v2"}), result.stderr
    assert (trusted / "source.py").read_text() == "trusted source\n"
    assert not (trusted / ".harness/knowledge-recognition.yaml").exists()
    assert git(trusted, "rev-parse", "HEAD") == base
    target = trusted / relative
    if case in {"valid", "v2"}:
        assert target.read_bytes() == original
    else:
        assert not target.exists()


def test_reader_bootstrap_legacy_output_preserves_native_fact_identity(
    tmp_path,
):
    from keepsail.core.knowledge_checkpoint import compact_facts

    w = Workspace(tmp_path)
    w.deliver()
    log = w.root / ".harness/events.jsonl"
    original = log.read_bytes()
    expected = compact_facts(read_inputs(w.root).ledger["events"])
    out = write_attestation(log, w.root / ".harness/attestations", "change-a",
                            format_version="v1-bootstrap")
    assert out.relative_to(w.root).as_posix() == ".harness/attestations/change-a.jsonl"
    assert log.read_bytes().startswith(original)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    approval = next(r for r in rows if r["type"] == "plan_approved")
    assert "review_reference_version" not in approval["payload"]
    assert approval["payload"]["evidence"]["decision"] == "approve"
    cp = next(r["payload"] for r in reversed(rows) if r["type"] == "knowledge_checkpointed")
    assert cp["schema_version"] == "knowledge-checkpoint/v1"
    assert cp["representation"] == "legacy-bootstrap-derived-not-original-event-bytes"
    assert resolve_facts(w.root, cp, policy()) == expected
    inputs = read_inputs(w.root)
    state = inputs.states["change-a"]
    state.current_code_subject = {"knowledge_basis": {"digest": cp["view"]["basis_digest"]}}
    assert validate_checkpoint(cp, policy(), state)["constraints"] == []
    git(w.root, "add", str(out.relative_to(w.root)))
    git(w.root, "commit", "-qm", "reader bootstrap legacy evidence")
    base = git(w.root, "rev-parse", "HEAD")
    git(w.root, "branch", "-f", "main", base)
    w.deliver()
    new = make_checkpoint(w.root, "change-a", read_inputs(w.root), base)
    assert len(new["delta"]) == 1
    assert resolve_facts(w.root, new, policy())[:len(expected)] == expected


def test_reader_bootstrap_cannot_drop_target_knowledge_or_acquisition(
    tmp_path,
):
    w = Workspace(tmp_path)
    w.recognize(version())
    w.deliver()
    log = w.root / ".harness/events.jsonl"
    before = log.read_bytes()
    with pytest.raises(KnowledgeError, match="empty finite set"):
        write_attestation(log, w.root / ".harness/attestations", "change-a",
                           format_version="v1-bootstrap")
    assert log.read_bytes() == before


def test_reader_only_release_rejects_explicit_v2_before_append(tmp_path, monkeypatch):
    from keepsail.engineering import attestation

    w = Workspace(tmp_path)
    log = w.root / ".harness/events.jsonl"
    before = log.read_bytes()
    monkeypatch.setattr(attestation, "ATTESTATION_FORMAT", "v1")
    with pytest.raises(ValueError, match="reader-only release"):
        write_attestation(log, w.root / ".harness/attestations", "change-a",
                           format_version="v2")
    assert log.read_bytes() == before
    assert not (w.root / ".harness/attestations/v2/change-a.jsonl").exists()


def test_reader_bootstrap_preserves_other_task_statement_source_without_rehash(
    tmp_path,
):
    from keepsail.core.approval import resolve_contract_base
    from keepsail.core.knowledge_checkpoint import compact_facts

    w = Workspace(tmp_path)
    digest = w.recognize(version(selector={"change_ids": ["change-a"]}))
    delivery = w.deliver()
    w.submit("record", w.operation(record={"kind": "statement", "decision": "adopt",
        "version_digest": digest, "delivery_id": delivery["delivery_id"],
        "reason": "Declaration only.", "session_id": "fixture-original-session",
        "root_turn_id": "fixture-original-turn", "tool_use_id": "fixture-original-tool"}))
    w.cli("change", "start", "reader-bootstrap")
    w.cli("knowledge", "deliver", "reader-bootstrap", "--operation-id", "bootstrap-empty",
          "--expected-revision", w.revision())
    log = w.root / ".harness/events.jsonl"
    original = compact_facts(read_inputs(w.root).ledger["events"])
    out = write_attestation(log, w.root / ".harness/attestations", "reader-bootstrap",
                            format_version="v1-bootstrap")
    cp = next(json.loads(line)["payload"] for line in reversed(out.read_text(
        encoding="utf-8").splitlines()) if json.loads(line)["type"] == "knowledge_checkpointed")
    assert resolve_facts(w.root, cp, policy()) == original
    git(w.root, "add", str(out.relative_to(w.root)))
    git(w.root, "commit", "-qm", "bootstrap with unrelated source statement")
    git(w.root, "branch", "-f", "main", git(w.root, "rev-parse", "HEAD"))
    w.deliver()
    new = make_checkpoint(w.root, "change-a", read_inputs(w.root), resolve_contract_base(w.root))
    assert len(new["delta"]) == 1
    assert resolve_facts(w.root, new, policy())[:len(original)] == original


def test_v2_reader_round_trip_and_malformed_structures(tmp_path, monkeypatch):
    from copy import deepcopy

    from keepsail.core.approval import ApprovalError, digest_record
    from keepsail.core.attestation_format import expand_attestation
    from keepsail.core.reducer import derive_state
    from keepsail.engineering import attestation

    # Exercise the future producer seam even in the reader-only release.
    monkeypatch.setattr(attestation, "ATTESTATION_FORMAT", "v2")
    w = Workspace(tmp_path)
    out = write_attestation(w.root / ".harness/events.jsonl", w.root / ".harness/attestations",
                            "change-a", format_version="v2")
    original = json.loads(out.read_text(encoding="utf-8"))
    assert out.parent.name == "v2"
    assert expand_attestation(original)
    assert derive_state(out)["change-a"].current_state == "IMPLEMENTATION_IN_PROGRESS"
    mutations = [
        ("lifecycle", []), ("lifecycle", None), ("lifecycle", [None]),
        ("authorization_lineage", None), ("authorization_lineage", [None]),
        ("knowledge_checkpoint", None), ("knowledge_checkpoint", {}),
        ("historical_lifecycle_index", None),
    ]
    for key, value in mutations:
        bad = deepcopy(original)
        bad[key] = value
        bad["digest"] = digest_record({k: v for k, v in bad.items() if k != "digest"})
        with pytest.raises(ApprovalError):
            expand_attestation(bad)
    for value in (None, [], "not-an-object", 1):
        bad = deepcopy(original)
        bad["lifecycle"][0]["payload"] = value
        bad["digest"] = digest_record({k: v for k, v in bad.items() if k != "digest"})
        with pytest.raises(ApprovalError):
            expand_attestation(bad)
        out.write_text(json.dumps(bad) + "\n", encoding="utf-8")
        blockers = attestation.check_attestation(out, "change-a")
        assert blockers and "invalid" in blockers[0]
    from keepsail.cli import attest as attest_cli

    monkeypatch.setattr(attest_cli, "_git_name_status", lambda *args:
                        "A\t.harness/attestations/v2/change-a.jsonl\nM\tplan.md\n")
    failure = w.cli("attest", "verify", "--base", "main", "--head", "HEAD", code=2)
    assert any("invalid lifecycle evidence" in row["message"] for row in failure["errors"])


@pytest.mark.parametrize("declaration", ["{", "null", "[]", "1",
                                         '{"prior_approvals":null}',
                                         '{"prior_approvals":[null]}'])
def test_retained_lineage_rejects_malformed_reviewed_json(tmp_path, declaration):
    from keepsail.core.approval import (
        ApprovalError,
        approval_record,
        make_plan_subject,
        validate_retained_lineage,
    )

    if declaration.startswith("{") and declaration != "{":
        declaration = json.dumps({
            "schema_version": "obligation-continuation/v1", "current_artifact": "plan.md",
            "scope": "all-current-obligations-with-explicit-historical-replacements",
            "prior_approval": "approval:previous", "fallback": "retain-full-uncovered-lineage",
            **json.loads(declaration),
        })
    (tmp_path / "plan.md").write_text(
        "# Fixture\n```keepsail-obligation-continuation\n" + declaration + "\n```\n",
        encoding="utf-8",
    )
    subject = make_plan_subject(tmp_path, change_id="fixture", artifacts=[("plan.md", "plan")],
                                commitments=[], prior_approval="approval:previous")
    approval = approval_record(subject=subject, evidence_id="fixture", evidence_digest="0" * 64)
    with pytest.raises(ApprovalError):
        validate_retained_lineage(approval, [{"schema_version": "approval-lineage-projection/v1",
                                              "approval_id": "approval:previous"}])


@pytest.mark.parametrize("path,accepted", [
    (".harness/attestations/probe.jsonl", True),
    (".harness/attestations/v2/probe.jsonl", True),
    (".harness/attestations/unknown/probe.jsonl", False),
    (".harness/attestations/v2/deep/probe.jsonl", False),
    (".harness/attestations/.jsonl", False),
])
def test_python_evidence_classification_matches_workflow_depth(path, accepted):
    from keepsail.core.approval import _attestation_only
    from keepsail.engineering.attestation import _is_attestation_path

    assert _is_attestation_path(path) is accepted
    assert _attestation_only([path]) is accepted
