"""String callbacks require a completed, entry-bound native CLI transport."""
import pytest


def test_string_return_needs_exit_witness_and_exact_full_page(tmp_path, context_workspace):
    from keepsail.core.context import entry_command, entry_readiness, read_entry
    from keepsail.daemon.codex_context_hook import observe_return, record_prompt, start_session
    from tests.unit.core import test_knowledge as fixtures

    w = context_workspace
    w.recognize(fixtures.version(body="知识约束\u2028保留 Unicode 分隔符"))
    identity = {"session_id": "fixture-string-return", "cwd": str(tmp_path), "turn_id": "root"}
    start = start_session(tmp_path, {**identity, "hook_event_name": "SessionStart",
                                     "source": "startup"}, cli_executable="/tools/keepsail")
    record_prompt(tmp_path, {**identity, "hook_event_name": "UserPromptSubmit"})
    packet = w.cli("change", "context", "change-a", "--bind-startup", start["startup_id"])["data"]
    entry = read_entry(tmp_path, packet["entry_id"])
    result = w.runner.invoke(fixtures.main, ["--workspace", str(tmp_path), "--json", "change",
        "context", "change-a", "--entry", entry["entry_id"]])
    assert result.exit_code == 0 and packet["total_pages"] == 1
    marker = "__KEEPSAIL_CONTEXT_EXIT_V1__:" + entry["entry_id"] + ":1:"
    good = result.stdout + marker + "0\n"
    payload = {**identity, "hook_event_name": "PostToolUse", "tool_name": "Bash",
               "tool_use_id": "fixture-completed", "tool_input": {"command": entry_command(entry)},
               "tool_response": good}
    # This is a supplied callback fixture, never an actual user session receipt.
    assert observe_return(tmp_path, payload)["complete"]
    assert w.cli("knowledge", "show")["data"]["observations"] == []
    for bad in [result.stdout, result.stdout + marker + "1\n",
                result.stdout + marker.replace(entry["entry_id"], "another-entry") + "0\n",
                result.stdout + marker.replace(":1:", ":2:") + "0\n",
                result.stdout[:100] + "\n" + marker + "0\n",
                "unknown diagnostic\n" + good, good + "extra\n",
                " " * (24 * 1024) + good, result.stdout + good,
                result.stdout + marker + "False\n"]:
        with pytest.raises(ValueError):
            observe_return(tmp_path, {**payload, "tool_response": bad})
    assert not entry_readiness(tmp_path, "change-a", identity["session_id"])["ready"]
    diagnostic = "line 31: unknown event type 'l1_update_completed'; skipping\r\n"
    assert observe_return(tmp_path, {**payload, "tool_use_id": "fixture-with-diagnostic",
                                    "tool_response": diagnostic + good})["complete"]
    assert w.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                 "--finalize-acquisition")["data"]["native_acquisition"] == "recorded"
    assert entry_readiness(tmp_path, "change-a", identity["session_id"])["ready"]


def test_legacy_returns_keep_original_interpretation():
    from keepsail.core.context import entry_command, returned_stdout

    entry = {"harness": "codex", "entry_id": "fixture-old", "change_id": "change-a",
             "cli": "/tools/keepsail", "root": "/workspace"}
    assert "__KEEPSAIL_CONTEXT_EXIT_V1__" not in entry_command(entry)
    assert returned_stdout(entry, {"tool_response": {"output": "old JSON", "exit_code": 0}}) == (
        "old JSON")
    with pytest.raises(ValueError, match="incomplete"):
        returned_stdout(entry, {"tool_response": "old JSON"})
