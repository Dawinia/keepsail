"""The PostgreSQL slice uses real Git, real checks and replacement CLI processes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from keepsail.core.approval import make_code_subject
from keepsail.core.knowledge import report
from keepsail.core.reducer import derive_state
from keepsail.engineering.attestation import (
    _knowledge_attestation,
    parse_name_status,
    verify_attestations,
)
from tests.unit.core.test_knowledge import Workspace, git, version


def process(w: Workspace, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            "-c",
            "from keepsail.cli import main; main()",
            "--workspace",
            str(w.root),
            "--json",
            *args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def review(w: Workspace, slug: str, kind: str, subject: str, eid: str) -> None:
    evidence = {
        "version": "review-evidence/v1",
        "evidence_id": eid,
        "kind": kind,
        "subject_id": subject,
        "decision": "approve",
        "issuer": "owner",
        "process": {"id": "owner-review", "version": "1"},
        "original_evidence": {"decision": "approve", "source": "isolated test fixture"},
        "provenance": {"policy_digest": w.review["process"]["policy_digest"]},
    }
    w.cli("review", "import", slug, "--evidence", str(w.write(evidence)))


@pytest.mark.parametrize(
    "selector", [{"global": True}, {"repository_ids": ["test-repo"], "change_ids": ["change-a"]}]
)
def test_coverage_refresh_preserves_exact_recognized_impact(tmp_path: Path, selector):
    w = Workspace(tmp_path)
    first = w.recognize(version(selector=selector))
    w.deliver()
    w.deliver()  # Multiple supplies must not choose a different impact identity.
    second = w.recognize(version(body="PostgreSQL 17+", previous=first, selector=selector))
    impact = report(w.root, "change-a")["impacts"][0]
    frozen = {
        k: v
        for k, v in impact.items()
        if k not in {"impact_id", "status", "disposition_id", "disposition"}
    }
    evidence = w.evidence(
        "disposition", impact["impact_id"], "continue", impact=frozen, use_version=second
    )
    w.submit("import", w.operation(evidence=evidence))
    w.deliver()
    assert process(w, "knowledge", "check", "change-a").returncode == 0
    assessment = {
        "assessment": {
            "approval_id": impact["approval_id"],
            "affected_commitments": ["db"],
            "conclusion": "within_approval",
            "reasons": ["Additional documentation fixture"],
            "references": ["plan.md"],
        },
        "coverage": [{"path": "plan.md"}, {"path": "docs/extra.md"}],
    }
    w.cli("implementation", "record", "change-a", "--assessment", str(w.write(assessment)))
    missing = process(w, "knowledge", "check", "change-a")
    assert missing.returncode == 2
    assert "exact retained delivery" in missing.stdout
    w.deliver()
    current = process(w, "knowledge", "check", "change-a")
    assert current.returncode == 0, current.stdout
    retained = json.loads(current.stdout)["data"]["impacts"][0]
    assert retained["impact_id"] == impact["impact_id"]
    assert retained["disposition"] == evidence
    assert retained["status"] == "resolved"


@pytest.mark.parametrize("disposition", ["adjust", "reapprove"])
@pytest.mark.parametrize("legacy", [False, True])
def test_postgresql_adjustment_cross_change_attestation_and_new_session(
    tmp_path: Path, disposition, legacy, monkeypatch
):
    w = Workspace(tmp_path)
    if legacy:
        # Exercise retained v1 writer records, not rewritten v2 lookalikes.
        import importlib

        module = importlib.import_module("keepsail.cli.knowledge")
        submit = module._submit

        def old_writer(root, event_type, request):
            if event_type == module.TRIGGER_EVENT:
                event_type = "knowledge_imported" if "evidence" in request else "knowledge_recorded"
            return submit(root, event_type, request)

        monkeypatch.setattr(module, "_submit", old_writer)
    log = w.root / ".harness/events.jsonl"
    first = w.recognize(version())
    w.deliver()
    marker = tmp_path.parent / (tmp_path.name + "-executed.txt")
    (w.root / "database.txt").write_text("postgresql:16", encoding="utf-8")
    (w.root / "check.py").write_text(
        "from pathlib import Path\nimport sys\n"
        "Path(sys.argv[1]).write_text('executed')\n"
        "assert Path('database.txt').read_text() == 'postgresql:17'\n",
        encoding="utf-8",
    )
    config = {
        "layers": {
            "baseline": {"enabled": False},
            "framework_adapter": {"enabled": False},
            "user_checks": {"enabled": True},
        },
        "defaults": {
            "timeout_seconds": 30,
            "must_pass": True,
            "capture": "both",
            "workdir": ".",
            "env": {},
        },
        "execution": {"mode": "sequential", "max_parallelism": 1, "fail_fast": False},
        "checks": [
            {
                "id": "postgresql-version",
                "command": [sys.executable, "-X", "utf8", "check.py", str(marker)],
            }
        ],
        "adapter_provided": [],
    }
    (w.root / ".harness/verification.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    git(w.root, "add", "database.txt", "check.py", ".harness/verification.yaml")
    git(w.root, "commit", "-qm", "implement database selection fixture")
    approval = derive_state(log)["change-a"].effective_approval["approval_id"]

    def assess():
        subject = make_code_subject(w.root, change_id="change-a", approval_id=approval, base="main")
        assessment = {
            "assessment": {
                "approval_id": approval,
                "affected_commitments": ["db"],
                "conclusion": "within_approval",
                "reasons": ["Implement the approved database choice."],
                "references": ["database.txt"],
            },
            "coverage": [{"path": row["path"]} for row in subject["manifest"]],
        }
        w.cli("implementation", "record", "change-a", "--assessment", str(w.write(assessment)))

    assess()
    # A second governing Change performs the correction. Its events are not in
    # A's normal attestation slice; the knowledge checkpoint must retain them.
    w.cli("change", "start", "change-b", "--framework", "plain")
    w.cli(
        "plan",
        "ready",
        "change-b",
        "--plan",
        "plan.md",
        "--scope",
        "[plan.md]",
        "--commitment",
        "db=Correct the database knowledge",
    )
    pending = derive_state(log)["change-b"].pending_revision["subject"]["subject_id"]
    review(w, "change-b", "plan", pending, "plan-b")
    w.cli(
        "knowledge",
        "deliver",
        "change-b",
        "--operation-id",
        "delivery-b",
        "--expected-revision",
        w.revision(),
    )
    w.cli("implementation", "start", "change-b")
    second = w.submit(
        "propose",
        w.operation(
            change_id="change-b", version=version(body="持久化统一 PostgreSQL 17+", previous=first)
        ),
    )["version_digest"]
    w.submit(
        "import",
        w.operation(change_id="change-b", evidence=w.evidence("recognition", second, "recognize")),
    )
    impact = report(w.root, "change-a")["impacts"][0]
    subject = {
        k: v
        for k, v in impact.items()
        if k not in {"impact_id", "status", "disposition_id", "disposition"}
    }
    e = w.evidence(
        "disposition",
        impact["impact_id"],
        disposition,
        impact=subject,
        use_version=second,
        obligations=["select PostgreSQL 17+"],
    )
    w.submit("import", w.operation(evidence=e))
    w.deliver()
    w.cli("done", "change-a", code=2)
    assert marker.read_text() == "executed"
    assert derive_state(log)["change-a"].current_verification["outcome"] == "failed"
    old_approval = approval
    if disposition == "reapprove":
        w.cli(
            "plan",
            "redeclare",
            "change-a",
            "--plan",
            "plan.md",
            "--commitment",
            "db=Persist with PostgreSQL 17+",
        )
        candidate = derive_state(log)["change-a"].pending_revision["subject"]["subject_id"]
        review(w, "change-a", "plan", candidate, "plan-a-v2")
        approval = derive_state(log)["change-a"].effective_approval["approval_id"]
        assert approval != old_approval
    (w.root / "database.txt").write_text("postgresql:17", encoding="utf-8")
    git(w.root, "add", "database.txt")
    git(w.root, "commit", "-qm", "apply recognized PostgreSQL correction")
    assess()
    # Current delivery/attestation must include the expanded actual coverage,
    # without reinterpreting the already recognized adjustment subject.
    before_expansion = report(w.root, "change-a")["impacts"][0]["impact_id"]
    (w.root / "docs").mkdir()
    (w.root / "docs/coverage-note.md").write_text("Additional fixture evidence\n", encoding="utf-8")
    git(w.root, "add", "docs/coverage-note.md")
    git(w.root, "commit", "-qm", "extend within-approval coverage")
    assess()
    assert report(w.root, "change-a")["impacts"][0]["impact_id"] == before_expansion
    w.deliver()
    w.cli("done", "change-a")
    state = derive_state(log)["change-a"]
    assert state.current_state == "AWAITING_CODE_REVIEW"
    assert state.effective_approval["approval_id"] == approval
    review(w, "change-a", "code", state.current_code_subject["subject_id"], "code-a")
    # A reported execution cannot close a recognized adjustment.
    execution = {
        "kind": "execution",
        "disposition_id": e["evidence_id"],
        "outcome": "reported",
        "subject_id": state.current_code_subject["subject_id"],
        "fulfilled_obligations": ["select PostgreSQL 17+"],
        "evidence": {"check": "postgresql-version", "marker": "executed"},
    }
    w.submit("record", w.operation(record=execution))
    w.cli("knowledge", "check", "change-a", code=2)
    execution["outcome"] = "verified"
    w.submit("record", w.operation(record=execution))
    w.deliver()
    w.cli("attest", "write", "change-a")
    att = w.root / ".harness/attestations/change-a.jsonl"
    assert not any(
        json.loads(line)["change_id"] == "change-b" for line in att.read_text().splitlines()
    )
    retained = [json.loads(line) for line in att.read_text(encoding="utf-8").splitlines()]
    assert any(
        v["body"] == "持久化统一 PostgreSQL"
        for v in retained[-1]["payload"]["view"]["supply_history"]
    )
    # No local event/state cache is needed by the pure Git verifier.
    git(w.root, "add", ".harness/attestations/change-a.jsonl")
    git(w.root, "commit", "-qm", "retain cross-change knowledge evidence")
    before = log.read_bytes()
    snapshot = json.loads(process(w, "change", "resume", "change-a").stdout)["data"]["knowledge"]
    assert snapshot["impacts"][0]["status"] == "resolved"
    assert snapshot["supply_history"][0]["version_digest"] == first
    assert log.read_bytes() == before
    log.unlink()
    (w.root / ".harness/state.yaml").unlink(missing_ok=True)
    diff = parse_name_status(git(w.root, "diff", "--name-status", "main...HEAD"))
    verdict = verify_attestations(w.root, diff, base="main", head="HEAD")
    assert verdict.ok, verdict.blockers
    # Tampering with the retained version must fail even with a valid lifecycle.
    text = att.read_text(encoding="utf-8")
    att.write_text(text.replace("PostgreSQL 17+", "SQLite"), encoding="utf-8")
    try:
        _knowledge_attestation(w.root, att, derive_state(att)["change-a"], base="main")
    except ValueError as exc:
        assert "digest" in str(exc) or "mismatch" in str(exc)
    else:
        raise AssertionError("corrupted knowledge checkpoint passed")


def test_two_processes_cannot_overwrite_the_same_knowledge_revision(tmp_path: Path):
    w = Workspace(tmp_path)
    first = w.operation(version=version())
    second = {
        **first,
        "operation_id": "different-operation",
        "version": version(body="another candidate"),
    }
    p1, p2 = w.write(first), w.write(second)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}
    base = [
        sys.executable,
        "-X",
        "utf8",
        "-B",
        "-c",
        "from keepsail.cli import main; main()",
        "--workspace",
        str(w.root),
        "--json",
        "knowledge",
        "propose",
        "--record",
    ]
    one = subprocess.Popen(
        [*base, str(p1)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    two = subprocess.Popen(
        [*base, str(p2)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    a, _ = one.communicate(timeout=60)
    b, _ = two.communicate(timeout=60)
    assert sorted([one.returncode, two.returncode]) == [0, 5], (a, b)
    assert len(w.cli("knowledge", "show")["data"]["versions"]) == 1
