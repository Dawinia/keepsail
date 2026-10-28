"""Context delivery behavior at the native CLI and pure projection seams."""
import json
from pathlib import Path


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
