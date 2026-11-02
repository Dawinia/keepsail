"""Context delivery behavior at the native CLI and pure projection seams."""
import json
from pathlib import Path


def test_reviewed_continuation_requires_exact_frozen_bindings(tmp_path, context_workspace):
    from copy import deepcopy

    from keepsail.core.approval import (
        approval_record,
        continued_approval_lineage,
        make_plan_subject,
    )
    from keepsail.core.reducer import derive_state

    prior = derive_state(tmp_path / ".harness/events.jsonl")["change-a"].effective_approval
    declaration = {
        "schema_version": "obligation-continuation/v1", "current_artifact": "revision.md",
        "scope": "all-current-obligations-with-explicit-historical-replacements",
        "prior_approval": prior["approval_id"], "fallback": "retain-full-uncovered-lineage",
        "prior_approvals": [{"approval_id": prior["approval_id"],
                             "subject_id": prior["subject_id"], "artifacts": [{
                                 "path": "plan.md",
                                 "digest": prior["subject"]["artifacts"][0]["digest"],
                                 "continued_in": "revision.md",
                                 "coverage": "all-current-obligations",
                                 "commitments": ["db"],
                             }]}],
    }

    def project(value, *, duplicate=False):
        block = "```keepsail-obligation-continuation\n" + json.dumps(value) + "\n```\n"
        (tmp_path / "revision.md").write_text("# PostgreSQL remains required\n" + block * (
            2 if duplicate else 1), encoding="utf-8")
        subject = make_plan_subject(
            tmp_path, change_id="change-a", artifacts=[("revision.md", "plan")],
            commitments=[{"id": "db", "text": "Use PostgreSQL", "artifact_path": "revision.md"}],
            prior_approval=prior["approval_id"],
        )
        approval = approval_record(subject=subject, evidence_id="new", evidence_digest="d" * 64)
        return continued_approval_lineage(approval, [prior])

    projected = project(declaration)
    assert projected[0]["schema_version"] == "approval-lineage-projection/v1"
    assert "content" not in projected[0]["artifacts"][0]
    assert projected[0]["artifacts"][0]["digest"] == prior["subject"]["artifacts"][0]["digest"]
    assert project(declaration, duplicate=True) == [prior]
    for key, value in [("schema_version", "unknown"), ("current_artifact", "other.md"),
                       ("prior_approval", "unapproved"), ("scope", "summary")]:
        assert project({**declaration, key: value}) == [prior]
    for key, value in [("digest", "0" * 64), ("path", "other.md"),
                       ("continued_in", "other.md"), ("commitments", ["unknown"]),
                       ("coverage", "partial")]:
        bad = deepcopy(declaration)
        bad["prior_approvals"][0]["artifacts"][0][key] = value
        assert project(bad) == [prior]


def test_gate_replays_once_per_action(tmp_path, context_workspace, monkeypatch):
    from keepsail.core import knowledge
    from keepsail.core.context import context_gate_inputs
    from tests.unit.core import test_knowledge as fixtures

    replay = knowledge.load_ledger
    calls = []

    def counted(*args, **kwargs):
        calls.append(args)
        return replay(*args, **kwargs)

    monkeypatch.setattr(knowledge, "load_ledger", counted)
    context_gate_inputs(tmp_path, "change-a", "unbound", "src/db/file.py")
    assert len(calls) == 1
    context_workspace.recognize(fixtures.version())
    calls.clear()
    state, _ = context_gate_inputs(tmp_path, "change-a", "unbound", "src/db/file.py")
    assert len(calls) == 1
    assert state.effective_approval is not None


def test_authority_identity_ignores_presentation_and_head_but_tracks_real_changes(
    tmp_path, context_workspace,
):
    from copy import deepcopy

    from keepsail.core.context import context_authority_digest, project_context
    from tests.unit.core.test_knowledge import git

    before = project_context(tmp_path, "change-a")
    (tmp_path / "implementation.txt").write_text("Approved implementation edit\n")
    git(tmp_path, "add", "implementation.txt")
    git(tmp_path, "commit", "-qm", "implementation fixture")
    after = project_context(tmp_path, "change-a")
    assert before["identity"]["head"] != after["identity"]["head"]
    assert before["authority_digest"] == after["authority_digest"]
    presentation = deepcopy(after)
    presentation["knowledge"]["context"] = {"presentation": "new compact layout"}
    presentation["identity"]["current_state"] = "display-only historical state"
    assert context_authority_digest(presentation) == after["authority_digest"]
    for key, value in (("authorization", None), ("policy_digest", "changed"),
                       ("pending_revision", {"status": "pending"}),
                       ("problems", ["constraint unavailable"])):
        assert context_authority_digest({**after, key: value}) != after["authority_digest"]
    changed = deepcopy(after)
    changed["knowledge"]["basis_digest"] = "changed-mechanical-coverage"
    assert context_authority_digest(changed) == after["authority_digest"]
    assert context_authority_digest(changed, schema="context-authority/v2") != (
        context_authority_digest(after, schema="context-authority/v2"))
    changed["knowledge"]["evaluated"] = [{"match": "changed-applicability"}]
    assert context_authority_digest(changed) != after["authority_digest"]


def test_cleanup_keeps_legacy_raw_and_cleanup_failure_cannot_keep_old_epoch(
    tmp_path, context_workspace, monkeypatch,
):
    import pytest

    from keepsail.core import context

    w = context_workspace
    entry = context.new_entry(tmp_path, "change-a", "fixture-cleanup", "startup", "keepsail")
    packet = w.cli("change", "context", "change-a", "--entry", entry["entry_id"])["data"]
    manifest = context.read_manifest(tmp_path, entry)
    legacy = {k: v for k, v in manifest.items() if k != "observation_schema"}
    legacy_parts = (entry["entry_id"], "receipts", packet["manifest_id"], "legacy.json")
    context.save_context_record(tmp_path, legacy_parts, {"fixture": "legacy original"})
    before = context.context_path(tmp_path, *legacy_parts).read_bytes()
    context.cleanup_context_returns(tmp_path, entry, legacy)
    assert context.context_path(tmp_path, *legacy_parts).read_bytes() == before
    v2_parts = (*context.receipt_parts(entry, manifest), "a" * 64 + ".json")
    context.save_context_record(tmp_path, v2_parts, {"fixture": "incomplete temporary return"})

    def failed_cleanup(*args, **kwargs):
        raise PermissionError("fixture cleanup failure")

    with monkeypatch.context() as patch:
        patch.setattr(context, "cleanup_context_returns", failed_cleanup)
        resumed = context.new_entry(tmp_path, "change-a", "fixture-cleanup", "resume", "keepsail")
    assert resumed["entry_id"] != entry["entry_id"]
    assert resumed["previous_raw_cleanup"] == "retained-after-cleanup-failure:PermissionError"
    with pytest.raises(ValueError, match="new session epoch"):
        context.read_entry(tmp_path, entry["entry_id"])
    assert not context.entry_readiness(tmp_path, "change-a", "fixture-cleanup")["ready"]
    assert context.context_path(tmp_path, *legacy_parts).read_bytes() == before
    assert context.context_path(tmp_path, *v2_parts).exists()
    context.retire_context_returns(tmp_path, "claude-code")
    assert not context.context_path(tmp_path, *v2_parts).exists()
    assert context.context_path(tmp_path, *legacy_parts).read_bytes() == before


def test_same_entry_keeps_exact_acquisition_after_mechanical_coverage_update(
    tmp_path, context_workspace,
):
    from keepsail.core.context import entry_command, entry_readiness, read_manifest
    from keepsail.core.knowledge import load_ledger, load_policy
    from keepsail.daemon.context_hook import observe_return, start_session
    from tests.unit.core import test_knowledge as fixtures

    w = context_workspace
    w.recognize(fixtures.version())
    identity = {"session_id": "fixture-coverage-continuity", "cwd": str(tmp_path)}
    entry = start_session(tmp_path, {**identity, "hook_event_name": "SessionStart",
                                    "source": "startup"}, cli_executable="keepsail",
                          change="change-a")
    result = w.runner.invoke(fixtures.main, ["--workspace", str(tmp_path), "--json", "change",
        "context", "change-a", "--entry", entry["entry_id"]])
    assert result.exit_code == 0, result.output
    observe_return(tmp_path, {**identity, "hook_event_name": "PostToolUse", "tool_name": "Bash",
        "tool_use_id": "fixture-coverage-return", "tool_input": {"command": entry_command(entry)},
        "tool_response": {"stdout": result.stdout, "stderr": "", "interrupted": False}})
    assert entry_readiness(tmp_path, "change-a", identity["session_id"])["ready"]
    original = read_manifest(tmp_path, entry)
    ledger, _ = load_ledger(tmp_path / ".harness/events.jsonl", load_policy(tmp_path))
    acquisitions = len(ledger["observations"])
    (tmp_path / "implementation.txt").write_text("PostgreSQL\n", encoding="utf-8")
    fixtures.git(tmp_path, "add", "implementation.txt")
    fixtures.git(tmp_path, "commit", "-qm", "within-approval fixture")
    assessment = {"affected_commitments": ["db"], "conclusion": "within_approval",
                  "reasons": ["Same approved persistence"], "references": ["implementation.txt"]}
    recorded = w.runner.invoke(fixtures.main, ["--workspace", str(tmp_path), "--json",
        "implementation", "record", "change-a", "--assessment", "-"], input=json.dumps(assessment))
    assert recorded.exit_code == 0, recorded.output
    pending = entry_readiness(tmp_path, "change-a", identity["session_id"])
    assert set(pending["blocking_reasons"]) == {
        "current constraints require an exact retained delivery"}
    assert "knowledge deliver" in pending["next_command"]
    supplied = w.deliver()
    assert entry_readiness(tmp_path, "change-a", identity["session_id"])["ready"]
    assert read_manifest(tmp_path, entry)["manifest_id"] == original["manifest_id"]
    ledger, _ = load_ledger(tmp_path / ".harness/events.jsonl", load_policy(tmp_path))
    assert len(ledger["observations"]) == acquisitions
    assert not any(o["delivery_id"] == supplied["delivery_id"] for o in ledger["observations"])
    w.recognize(fixtures.version(body="Changed constraint", previous=supplied["constraints"][0][
        "version_digest"]))
    assert not entry_readiness(tmp_path, "change-a", identity["session_id"])["ready"]


def test_preview_restores_frozen_approval_without_recording_supply(
    tmp_path: Path, context_workspace,
):
    workspace = context_workspace
    (tmp_path / "plan.md").write_text("Changed candidate, not approved\n", encoding="utf-8")
    events = tmp_path / ".harness/events.jsonl"
    before = events.read_bytes()
    data = workspace.cli("change", "context", "change-a", "--preview")["data"]
    assert data["identity"]["change_id"] == "change-a"
    assert data["authorization"]["subject"]["commitments"][0]["id"] == "db"
    assert data["authorization"]["subject"]["artifacts"][0]["content"] == (
        "# Persist with PostgreSQL\n"
    )
    assert data["supply_status"] == "not_supplied"
    assert data["acquisition_status"] == "not_observed"
    assert events.read_bytes() == before


def test_revision_restores_referenced_frozen_approval_and_unreplaced_restrictions(
    tmp_path, context_workspace,
):
    from keepsail.core.reducer import derive_state

    workspace = context_workspace
    (tmp_path / "revision.md").write_text("Change entry; preserve prior restrictions.\n")
    workspace.cli("plan", "redeclare", "change-a", "--plan", "revision.md",
                   "--commitment", "db=Use PostgreSQL")
    pending = derive_state(tmp_path / ".harness/events.jsonl")["change-a"].pending_revision
    subject = pending["subject"]
    evidence = {"version": "review-evidence/v1", "evidence_id": "revision-review-1",
                "kind": "plan", "subject_id": subject["subject_id"], "decision": "approve",
                "process": {"id": "owner-review", "version": "1"}, "issuer": "owner",
                "original_evidence": {"decision": "approve"},
                "provenance": {"policy_digest": workspace.review["process"]["policy_digest"]}}
    workspace.cli("review", "import", "change-a", "--evidence", str(workspace.write(evidence)))
    (tmp_path / "plan.md").write_text("Unapproved disk text\n")
    preview = workspace.cli("change", "context", "change-a", "--preview")["data"]
    prior = preview["authorization_lineage"][0]
    assert prior["approval_id"] == "approval:plan-1"
    assert prior["subject"]["artifacts"][0]["content"] == "# Persist with PostgreSQL\n"
    assert preview["authorization"]["subject"]["prior_approval"] == prior["approval_id"]


def test_only_complete_actual_cli_returns_make_current_entry_ready(tmp_path, context_workspace):
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    version = workspace.recognize(fixtures.version(body="知识原文 " * 2500))
    from keepsail.core.context import entry_command, entry_readiness
    from keepsail.daemon.context_hook import observe_return, start_session

    payload = {"hook_event_name": "SessionStart", "session_id": "session-a",
               "cwd": str(tmp_path), "source": "startup"}
    entry = start_session(tmp_path, payload, cli_executable="C:/tools/keepsail.exe",
                          change="change-a")
    assert not entry_readiness(tmp_path, "change-a", "session-a")["ready"]
    first = workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"])
    count = first["data"]["total_pages"]
    assert count > 1
    for page in range(1, count + 1):
        result = workspace.runner.invoke(
            fixtures.main, ["--workspace", str(tmp_path), "--json", "change", "context",
                            "change-a", "--entry", entry["entry_id"], "--page", str(page)]
        )
        assert result.exit_code == 0, result.output
        assert len(result.stdout.encode("utf-8")) <= 24 * 1024
        observe_return(tmp_path, {
            "hook_event_name": "PostToolUse", "session_id": "session-a", "cwd": str(tmp_path),
            "tool_name": "Bash", "tool_use_id": f"tool-{page}",
            "tool_input": {"command": entry_command(entry, page)},
            "tool_response": {"stdout": result.stdout, "stderr": "", "interrupted": False},
        })
        assert entry_readiness(tmp_path, "change-a", "session-a")["ready"] == (page == count)
    allowed = workspace.cli("gate", "check", "pre-tool-use", "--agent", "claude-code",
                            "--session-id", "session-a", "--change-id", "change-a",
                            "--tool", "Edit", "--file", str(tmp_path / "src/db/file.py"))
    assert allowed["data"]["decision"] == "allow"
    statement = {"schema_version": "entry-statement/v1", "entry_id": entry["entry_id"],
                 "manifest_id": first["data"]["manifest_id"], "actor": "fixture-executor",
                 "decision": "adopt", "reason": "Use the returned approved context",
                 "knowledge_versions": [version], "project_context": True}
    declared = workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                              "--statement", str(workspace.write(statement)))["data"]
    assert declared["recorded"]
    assert declared["authority_effect"] == "unchanged"
    knowledge = workspace.cli("knowledge", "show")["data"]
    assert knowledge["statements"][-1]["decision"] == "adopt"
    start_session(tmp_path, {**payload, "source": "compact"},
                  cli_executable="C:/tools/keepsail.exe", change="change-a")
    assert not entry_readiness(tmp_path, "change-a", "session-a")["ready"]
    denied = workspace.cli("gate", "check", "pre-tool-use", "--agent", "claude-code",
                           "--session-id", "session-a", "--change-id", "change-a",
                           "--tool", "Edit", "--file", str(tmp_path / "src/db/file.py"), code=2)
    assert denied["data"]["decision"] == "block"


def test_action_path_exposes_constraints_beyond_estimated_scope(tmp_path, context_workspace):
    from keepsail.core.context import entry_command, entry_readiness
    from keepsail.daemon.context_hook import observe_return, start_session
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    workspace.recognize(fixtures.version(selector={"paths": ["docs/new"]}))
    entry = start_session(tmp_path, {"hook_event_name": "SessionStart", "session_id": "executor-a",
                                    "source": "startup", "cwd": str(tmp_path)},
                          cli_executable="/tools/keepsail", change="change-a")
    result = workspace.runner.invoke(fixtures.main, [
        "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
        "--entry", entry["entry_id"],
    ])
    assert result.exit_code == 0, result.output
    observe_return(tmp_path, {"hook_event_name": "PostToolUse", "session_id": "executor-a",
                             "cwd": str(tmp_path), "tool_name": "Bash", "tool_use_id": "tool-1",
                             "tool_input": {"command": entry_command(entry)},
                             "tool_response": {"stdout": result.stdout, "stderr": "",
                                               "interrupted": False}})
    assert entry_readiness(tmp_path, "change-a", "executor-a", "src/db/file.py")["ready"]
    exposed = entry_readiness(tmp_path, "change-a", "executor-a", "docs/new/file.md")
    assert not exposed["ready"]
    assert "coverage" in " ".join(exposed["blocking_reasons"])


def test_dependent_challenge_waits_while_independent_approved_work_continues(
    tmp_path, context_workspace,
):
    from keepsail.core.context import entry_command, entry_readiness
    from keepsail.daemon.context_hook import observe_return, start_session
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    version = workspace.recognize(fixtures.version(selector={"paths": ["src/db"]}))
    entry = start_session(tmp_path, {"hook_event_name": "SessionStart", "session_id": "executor-a",
                                    "source": "startup", "cwd": str(tmp_path)},
                          cli_executable="/tools/keepsail", change="change-a")

    def consume():
        result = workspace.runner.invoke(fixtures.main, [
            "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
            "--entry", entry["entry_id"],
        ])
        assert result.exit_code == 0, result.output
        packet = json.loads(result.stdout)["data"]
        assert packet["total_pages"] == 1
        observe_return(tmp_path, {"hook_event_name": "PostToolUse", "session_id": "executor-a",
                                 "cwd": str(tmp_path), "tool_name": "Bash",
                                 "tool_use_id": "tool-" + packet["manifest_id"],
                                 "tool_input": {"command": entry_command(entry)},
                                 "tool_response": {"stdout": result.stdout, "stderr": "",
                                                   "interrupted": False}})
        return packet

    packet = consume()
    workspace.submit("record", workspace.operation(record={
        "kind": "challenge", "delivery_id": packet["delivery_id"], "version_digest": version,
        "decision": "challenge", "reason": "Needs recognized database decision",
        "dependent_paths": ["src/db"],
    }))
    consume()
    assert entry_readiness(tmp_path, "change-a", "executor-a", "docs/independent.md")["ready"]
    assert not entry_readiness(tmp_path, "change-a", "executor-a", "src/db/file.py")["ready"]


def test_project_only_declarations_recover_as_self_reports_in_new_epoch(
    tmp_path, context_workspace,
):
    from keepsail.daemon.context_hook import start_session

    workspace = context_workspace
    callback = {"hook_event_name": "SessionStart", "session_id": "executor-a",
                "source": "startup", "cwd": str(tmp_path)}
    entry = start_session(tmp_path, callback, cli_executable="/tools/keepsail", change="change-a")
    packet = workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"])["data"]
    for decision, reason in [("challenge", "unresolved convention question"),
                             ("adopt", "explicit empty-set project adoption")]:
        record = {"schema_version": "entry-statement/v1", "entry_id": entry["entry_id"],
                  "manifest_id": packet["manifest_id"], "actor": "fixture-executor-a",
                  "decision": decision, "reason": reason, "knowledge_versions": [],
                  "project_context": True, "dependent_paths": ["src/db"]}
        workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                       "--statement", str(workspace.write(record)))
    next_entry = start_session(tmp_path, {**callback, "source": "compact"},
                               cli_executable="/tools/keepsail", change="change-a")
    projected = workspace.cli("change", "context", "change-a", "--preview")["data"]
    declarations = projected["trace"]["project_statements"]
    assert {d["declaration"]["reason"] for d in declarations} == {
        "unresolved convention question", "explicit empty-set project adoption",
    }
    challenge = next(d for d in declarations if d["declaration"]["decision"] == "challenge")
    assert challenge["status"] == "unresolved"
    assert challenge["recognized_disposition"] is None
    assert all(d["source_entry_id"] == entry["entry_id"] for d in declarations)
    assert all(d["source_entry_id"] != next_entry["entry_id"] for d in declarations)
    assert workspace.cli("knowledge", "show")["data"]["statements"] == []
