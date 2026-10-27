"""Context delivery behavior at the native CLI and pure projection seams."""
import json
from pathlib import Path

from tests.unit.core.test_knowledge import Workspace


def test_preview_restores_frozen_approval_without_recording_supply(tmp_path: Path):
    workspace = Workspace(tmp_path)
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


def test_only_complete_actual_cli_returns_make_current_entry_ready(tmp_path, monkeypatch):
    from tests.unit.core import test_knowledge as fixtures

    policy = fixtures.policy()
    policy["observation_issuers"].append("keepsail-cli-observer")
    policy["policy_digest"] = fixtures.policy_digest(policy)
    monkeypatch.setattr(fixtures, "policy", lambda: policy)
    workspace = Workspace(tmp_path)
    version = workspace.recognize(fixtures.version(body="知识原文 " * 6000))
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


def test_action_path_exposes_constraints_beyond_estimated_scope(tmp_path, monkeypatch):
    from keepsail.core.context import entry_command, entry_readiness
    from keepsail.daemon.context_hook import observe_return, start_session
    from tests.unit.core import test_knowledge as fixtures

    policy = fixtures.policy()
    policy["observation_issuers"].append("keepsail-cli-observer")
    policy["policy_digest"] = fixtures.policy_digest(policy)
    monkeypatch.setattr(fixtures, "policy", lambda: policy)
    workspace = Workspace(tmp_path)
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


def test_dependent_challenge_waits_while_independent_approved_work_continues(tmp_path, monkeypatch):
    from keepsail.core.context import entry_command, entry_readiness
    from keepsail.daemon.context_hook import observe_return, start_session
    from tests.unit.core import test_knowledge as fixtures

    policy = fixtures.policy()
    policy["observation_issuers"].append("keepsail-cli-observer")
    policy["policy_digest"] = fixtures.policy_digest(policy)
    monkeypatch.setattr(fixtures, "policy", lambda: policy)
    workspace = Workspace(tmp_path)
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
