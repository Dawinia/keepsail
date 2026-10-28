"""Codex callback fixtures at the hook/CLI seam, not real desktop acceptance."""

import pytest


def _completed_output(stdout, entry, page=1):
    return stdout + "__KEEPSAIL_CONTEXT_EXIT_V1__:" + entry["entry_id"] + ":" + str(page) + ":0\n"


def test_cli_finalization_requires_actual_returns_and_prompt_reminds_pending_acquisition(
    tmp_path, monkeypatch, context_workspace,
):
    import json

    from keepsail.core.context import entry_command, read_entry
    from keepsail.daemon.codex_context_hook import observe_return, record_prompt, start_session
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    workspace.recognize(fixtures.version())
    identity = {"session_id": "codex-a", "cwd": str(tmp_path)}
    startup = start_session(tmp_path, {**identity, "hook_event_name": "SessionStart",
                                      "source": "startup"}, cli_executable="/tools/keepsail")
    record_prompt(tmp_path, {**identity, "hook_event_name": "UserPromptSubmit", "turn_id": "root"})
    response = workspace.runner.invoke(fixtures.main, [
        "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
        "--bind-startup", startup["startup_id"],
    ])
    packet = json.loads(response.stdout)["data"]
    assert packet["total_pages"] == 1
    entry = read_entry(tmp_path, packet["entry_id"])
    workspace.cli("change", "context", "change-a", "--entry", packet["entry_id"],
                   "--finalize-acquisition", code=2)  # Supply alone cannot acknowledge itself.
    observed = observe_return(tmp_path, {
        **identity, "hook_event_name": "PostToolUse", "turn_id": "root", "tool_name": "Bash",
        "tool_use_id": "fixture-bind", "tool_input": {"command": entry_command(entry, bind=True)},
        "tool_response": {"output": _completed_output(response.stdout, entry),
                                                       "exit_code": 0},
    })
    assert observed["complete"] is True
    assert observed["native_acquisition"] == "pending"
    assert "--finalize-acquisition" in observed["next_command"]
    assert workspace.cli("knowledge", "show")["data"]["observations"] == []
    # Exercise the real prompt dispatch: complete outer pages must not silence this hint.
    from io import StringIO

    from keepsail.daemon.codex_context_hook import run_context_hook

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.stdin", StringIO(json.dumps({
        **identity, "hook_event_name": "UserPromptSubmit", "turn_id": "next-root",
    })))
    output = StringIO()
    monkeypatch.setattr("sys.stdout", output)
    run_context_hook("user-prompt-submit", None)
    assert "--finalize-acquisition" in output.getvalue()
    result = workspace.cli("change", "context", "change-a", "--entry", packet["entry_id"],
                            "--finalize-acquisition")["data"]
    assert result["native_acquisition"] == "recorded"
    assert len(workspace.cli("knowledge", "show")["data"]["observations"]) == 1
    workspace.cli("change", "context", "change-a", "--entry", packet["entry_id"],
                   "--finalize-acquisition")
    assert len(workspace.cli("knowledge", "show")["data"]["observations"]) == 1


def test_startup_binds_once_and_compact_invalidates_old_entry(tmp_path, context_workspace):
    from keepsail.core.context import read_entry
    from keepsail.daemon.codex_context_hook import start_session

    workspace = context_workspace
    callback = {"hook_event_name": "SessionStart", "session_id": "codex-a",
                "cwd": str(tmp_path), "source": "startup"}
    startup = start_session(tmp_path, callback, cli_executable="C:/tools/keepsail.exe")
    packet = workspace.cli("change", "context", "change-a",
                           "--bind-startup", startup["startup_id"])["data"]
    entry = read_entry(tmp_path, packet["entry_id"])
    assert entry["harness"] == "codex"
    assert entry["change_id"] == "change-a"
    assert workspace.cli("change", "context", "change-a", "--bind-startup",
                         startup["startup_id"])["data"]["entry_id"] == entry["entry_id"]
    workspace.cli("change", "context", "other-change", "--bind-startup",
                   startup["startup_id"], code=2)
    start_session(tmp_path, {**callback, "source": "compact"},
                  cli_executable="C:/tools/keepsail.exe")
    with pytest.raises(ValueError, match="replaced"):
        read_entry(tmp_path, entry["entry_id"])
    workspace.cli("change", "context", "change-a", "--bind-startup",
                   startup["startup_id"], code=2)


def test_automatic_compact_keeps_root_turn_but_requires_new_entry_returns(
    tmp_path, context_workspace,
):
    from keepsail.core.context import entry_command, entry_readiness, read_entry
    from keepsail.daemon.codex_context_hook import observe_return, record_prompt, start_session
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    identity = {"session_id": "codex-a", "cwd": str(tmp_path)}
    start_session(tmp_path, {**identity, "hook_event_name": "SessionStart", "source": "startup"},
                  cli_executable="/tools/keepsail")
    record_prompt(tmp_path, {**identity, "hook_event_name": "UserPromptSubmit",
                             "turn_id": "turn-a"})
    startup = start_session(tmp_path, {**identity, "hook_event_name": "SessionStart",
                                      "source": "compact"}, cli_executable="/tools/keepsail")
    packet = workspace.cli("change", "context", "change-a", "--bind-startup",
                           startup["startup_id"])["data"]
    entry = read_entry(tmp_path, packet["entry_id"])
    assert not entry_readiness(tmp_path, "change-a", "codex-a")["ready"]
    # No new UserPromptSubmit: the actual compact continuation must reacquire now.
    result = workspace.runner.invoke(fixtures.main, [
        "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
        "--entry", entry["entry_id"],
    ])
    assert observe_return(tmp_path, {**identity, "hook_event_name": "PostToolUse",
                                     "turn_id": "turn-a", "tool_name": "Bash",
                                     "tool_use_id": "fixture-after-compact",
                                     "tool_input": {"command": entry_command(entry)},
                                     "tool_response": {
                                         "output": _completed_output(result.stdout, entry),
                                         "exit_code": 0}})[
        "complete"]
    assert entry_readiness(tmp_path, "change-a", "codex-a")["ready"]


def test_codex_complete_cli_returns_require_observed_root_turn(tmp_path, context_workspace):
    from keepsail.core.context import entry_command, entry_readiness, read_entry
    from keepsail.daemon.codex_context_hook import observe_return, record_prompt, start_session
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    version = workspace.recognize(fixtures.version(body="完整知识 " * 2500))
    startup = start_session(tmp_path, {"hook_event_name": "SessionStart", "session_id": "codex-a",
                                      "cwd": str(tmp_path), "source": "startup"},
                            cli_executable="C:/tools/keepsail.exe")
    record_prompt(tmp_path, {"hook_event_name": "UserPromptSubmit", "session_id": "codex-a",
                             "turn_id": "root-turn-a", "cwd": str(tmp_path), "prompt": "private"})
    packet = workspace.cli("change", "context", "change-a", "--bind-startup",
                           startup["startup_id"])["data"]
    entry = read_entry(tmp_path, packet["entry_id"])
    assert packet["total_pages"] > 1
    assert "PYTHONUTF8" in entry_command(entry)
    for page in range(1, packet["total_pages"] + 1):
        result = workspace.runner.invoke(fixtures.main, [
            "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
            "--entry", entry["entry_id"], "--page", str(page),
        ])
        callback = {"hook_event_name": "PostToolUse", "session_id": "codex-a",
                    "turn_id": "root-turn-a", "cwd": str(tmp_path), "tool_name": "Bash",
                    "tool_use_id": f"fixture-codex-tool-{page}",
                    "tool_input": {"command": entry_command(entry, page)},
                    "tool_response": {"output": _completed_output(result.stdout, entry, page),
                                                       "exit_code": 0}}
        for change in ({"turn_id": "child-turn"},
                       {"tool_response": {"output": result.stdout, "session_id": 123}},
                       {"tool_response": {"output": result.stdout, "exit_code": 1}}):
            with pytest.raises(ValueError):
                observe_return(tmp_path, {**callback, **change})
        observed = observe_return(tmp_path, callback)
        assert observed["complete"] == (page == packet["total_pages"])
    assert not entry_readiness(tmp_path, "change-a", "codex-a", "src/db/file.py")["ready"]
    workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                   "--finalize-acquisition")
    assert entry_readiness(tmp_path, "change-a", "codex-a", "src/db/file.py")["ready"]
    observations = workspace.cli("knowledge", "show")["data"]["observations"]
    assert observations[-1]["version_digest"] == version
    receipt = observations[-1]["original_receipt"]
    assert receipt["boundary"] == "codex-native-cli-tool-return"
    assert receipt["callbacks"][0]["tool_response"].keys() == {"output", "exit_code"}
    assert "private" not in "".join(p.read_text(encoding="utf-8") for p in (
        tmp_path / ".harness/operation-logs/context/turns"
    ).glob("*.json"))


def test_patch_gate_checks_entire_move_and_preserves_independent_work(tmp_path, context_workspace):
    from keepsail.core.context import entry_command, read_entry
    from keepsail.daemon.codex_context_hook import observe_return, record_prompt, start_session
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    version = workspace.recognize(fixtures.version(selector={"paths": ["src/db"]}))
    startup = start_session(tmp_path, {"hook_event_name": "SessionStart", "session_id": "codex-a",
                                      "source": "startup", "cwd": str(tmp_path)},
                            cli_executable="/tools/keepsail")
    record_prompt(tmp_path, {"hook_event_name": "UserPromptSubmit", "session_id": "codex-a",
                             "turn_id": "root-turn", "cwd": str(tmp_path)})
    packet = workspace.cli("change", "context", "change-a", "--bind-startup",
                           startup["startup_id"])["data"]
    workspace.submit("record", workspace.operation(record={
        "kind": "challenge", "delivery_id": packet["delivery_id"], "version_digest": version,
        "decision": "challenge", "reason": "Database decision needed",
        "dependent_paths": ["src/db"],
    }))
    entry = read_entry(tmp_path, packet["entry_id"])
    response = workspace.runner.invoke(fixtures.main, [
        "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
        "--entry", entry["entry_id"],
    ])
    observe_return(tmp_path, {"hook_event_name": "PostToolUse", "session_id": "codex-a",
                             "turn_id": "root-turn", "cwd": str(tmp_path), "tool_name": "Bash",
                             "tool_use_id": "fixture-refreshed",
                             "tool_input": {"command": entry_command(entry)},
                             "tool_response": {"output": _completed_output(response.stdout, entry),
                                                       "exit_code": 0}})
    workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                   "--finalize-acquisition")

    def decide(body, expected=0):
        path = tmp_path / "candidate.patch"
        path.write_text(body, encoding="utf-8")
        return workspace.cli("gate", "check", "pre-tool-use", "--agent", "codex",
                             "--change-id", "change-a", "--session-id", "codex-a",
                             "--turn-id", "root-turn", "--patch-file", str(path), code=expected)

    independent = "*** Begin Patch\n*** Add File: docs/independent.md\n+safe\n*** End Patch\n"
    assert decide(independent)["data"]["decision"] == "allow"
    dependent_move = ("*** Begin Patch\n*** Update File: docs/independent.md\n"
                      "*** Move to: src/db/moved.md\n@@\n-safe\n+changed\n*** End Patch\n")
    assert decide(dependent_move, 2)["data"]["decision"] == "block"
    mixed = independent.replace("*** End Patch", "*** Delete File: src/db/old.py\n*** End Patch")
    assert decide(mixed, 2)["data"]["decision"] == "block"
    assert decide(independent.replace("docs/independent.md", "../outside.md"), 2)["data"][
        "decision"] == "block"
    assert decide("malformed patch", 2)["data"]["decision"] == "block"
