"""Codex callback fixtures at the hook/CLI seam, not real desktop acceptance."""

import pytest


def _completed_output(stdout, entry, page=1):
    return stdout + "__KEEPSAIL_CONTEXT_EXIT_V1__:" + entry["entry_id"] + ":" + str(page) + ":0\n"


def test_unbound_startup_ignores_tool_returns_without_claiming_acquisition(tmp_path):
    from keepsail.core.context import context_path
    from keepsail.daemon.codex_context_hook import observe_return, start_session

    (tmp_path / ".harness").mkdir()
    identity = {"session_id": "unbound-root", "cwd": str(tmp_path)}
    startup = start_session(tmp_path, {**identity, "hook_event_name": "SessionStart",
                                     "source": "startup"}, cli_executable="/tools/keepsail")
    assert observe_return(tmp_path, {
        **identity, "hook_event_name": "PostToolUse", "tool_name": "Bash",
        "tool_input": {"command": "git status --short"},
    }) == {"ignored": True}
    assert not context_path(tmp_path, startup["startup_id"], "receipts").exists()


def test_finalize_rechecks_new_approval_and_requires_fresh_returns(tmp_path, context_workspace):
    from keepsail.core.context import entry_command, read_entry
    from keepsail.core.reducer import derive_state
    from keepsail.daemon.codex_context_hook import observe_return, record_prompt, start_session
    from tests.unit.core import test_knowledge as fixtures

    w = context_workspace
    w.recognize(fixtures.version())
    identity = {"session_id": "fixture-approval-recovery", "cwd": str(tmp_path), "turn_id": "root"}
    start = start_session(tmp_path, {**identity, "hook_event_name": "SessionStart",
                                    "source": "startup"}, cli_executable="/tools/keepsail")
    record_prompt(tmp_path, {**identity, "hook_event_name": "UserPromptSubmit"})
    packet = w.cli("change", "context", "change-a", "--bind-startup", start["startup_id"])["data"]
    entry = read_entry(tmp_path, packet["entry_id"])

    def consume(tool):
        result = w.runner.invoke(fixtures.main, ["--workspace", str(tmp_path), "--json",
            "change", "context", "change-a", "--entry", entry["entry_id"]])
        assert result.exit_code == 0, result.output
        return observe_return(tmp_path, {**identity, "hook_event_name": "PostToolUse",
            "tool_name": "Bash", "tool_use_id": tool,
            "tool_input": {"command": entry_command(entry)},
            "tool_response": _completed_output(result.stdout, entry)})

    assert consume("old-approval")["complete"]
    w.cli("plan", "redeclare", "change-a", "--plan", "plan.md", "--commitment",
          "db=Use PostgreSQL under a new approval epoch")
    pending = derive_state(tmp_path / ".harness/events.jsonl")["change-a"].pending_revision
    subject = pending["subject"]
    evidence = {"version": "review-evidence/v1", "evidence_id": "fixture-new-approval",
        "kind": "plan", "subject_id": subject["subject_id"], "decision": "approve",
        "issuer": "owner", "process": {"id": "owner-review", "version": "1"},
        "original_evidence": {"decision": "approve", "source": "test fixture"},
        "provenance": {"policy_digest": w.review["process"]["policy_digest"]}}
    w.cli("review", "import", "change-a", "--evidence", str(w.write(evidence)))
    w.cli("change", "context", "change-a", "--entry", entry["entry_id"],
          "--finalize-acquisition", code=2)
    assert w.cli("knowledge", "show")["data"]["observations"] == []
    fresh = w.cli("change", "context", "change-a", "--entry", entry["entry_id"])["data"]
    assert fresh["manifest_id"] != packet["manifest_id"]
    w.cli("change", "context", "change-a", "--entry", entry["entry_id"],
          "--finalize-acquisition", code=2)
    assert consume("new-approval")["complete"]
    assert w.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                 "--finalize-acquisition")["data"]["native_acquisition"] == "recorded"


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
    # A partial native append keeps the actual returns for retry and cannot make ready.
    from keepsail.core.context import context_path, entry_readiness, receipt_parts
    from keepsail.daemon import context_hook

    submit = context_hook._submit

    def fail_relation(root, event_type, request):
        if request.get("record", {}).get("kind") == "acquisition":
            raise OSError("fixture native association append failure")
        return submit(root, event_type, request)

    with monkeypatch.context() as patch:
        patch.setattr(context_hook, "_submit", fail_relation)
        workspace.cli("change", "context", "change-a", "--entry", packet["entry_id"],
                      "--finalize-acquisition", code=1)
    from keepsail.core.context import read_manifest

    raw_directory = context_path(tmp_path, *receipt_parts(entry, read_manifest(tmp_path, entry)))
    assert raw_directory.exists()
    partial = workspace.cli("knowledge", "show")["data"]
    assert len(partial["context_observations"]) == 1
    assert partial["observations"] == []
    assert not entry_readiness(tmp_path, "change-a", "codex-a", "src/db/file.py")["ready"]
    result = workspace.cli("change", "context", "change-a", "--entry", packet["entry_id"],
                            "--finalize-acquisition")["data"]
    assert result["native_acquisition"] == "recorded"
    assert len(workspace.cli("knowledge", "show")["data"]["observations"]) == 1
    assert not raw_directory.exists()
    before = (tmp_path / ".harness/events.jsonl").read_bytes()
    workspace.cli("change", "context", "change-a", "--entry", packet["entry_id"],
                   "--finalize-acquisition")
    assert len(workspace.cli("knowledge", "show")["data"]["observations"]) == 1
    assert (tmp_path / ".harness/events.jsonl").read_bytes() == before


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
    # Public finalization must reject the replaced epoch, not revive its supply.
    workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                  "--finalize-acquisition", code=2)
    assert workspace.cli("knowledge", "show")["data"]["observations"] == []


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
    assert not entry_readiness(tmp_path, "change-a", "codex-a")["ready"]
    workspace.cli("change", "context", "change-a", "--entry", entry["entry_id"],
                  "--finalize-acquisition")
    assert entry_readiness(tmp_path, "change-a", "codex-a")["ready"]


def test_codex_complete_cli_returns_require_observed_root_turn(tmp_path, context_workspace):
    from keepsail.core.context import entry_command, entry_readiness, read_entry
    from keepsail.daemon.codex_context_hook import observe_return, record_prompt, start_session
    from tests.unit.core import test_knowledge as fixtures

    workspace = context_workspace
    version = workspace.recognize(fixtures.version(body="完整知识 " * 2500))
    second_version = fixtures.version(body="second supplied knowledge")
    second_version["knowledge_id"] = "fixture-second"
    second = workspace.recognize(second_version)
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
    view = workspace.cli("knowledge", "show")["data"]
    observations = view["observations"]
    assert {o["version_digest"] for o in observations} == {version, second}
    assert len(view["context_observations"]) == 1
    receipt = view["context_observations"][0]
    assert receipt["schema_version"] == "context-acquisition/v2"
    assert receipt["status"] == "complete"
    assert len(receipt["pages"]) == packet["total_pages"]
    assert all(o["schema_version"] == "acquisition-observation/v2"
               and o["observation_id"] == receipt["observation_id"] for o in observations)
    assert all("original_receipt" not in o and "callbacks" not in o for o in observations)
    import json

    assert "tool_response" not in json.dumps(receipt)
    assert "callbacks" not in json.dumps(receipt)
    from keepsail.core.context import context_path, read_manifest, receipt_parts

    raw_path = context_path(tmp_path, *receipt_parts(entry, read_manifest(tmp_path, entry)))
    assert not raw_path.exists()
    original = {k: v for k, v in observations[0].items() if k != "change_id"}
    for mutation in ({"observation_id": "missing"}, {"session_id": "wrong"},
                     {"schema_version": "unknown"}, {"original_receipt": {"hash": "not-raw"}}):
        before = (tmp_path / ".harness/events.jsonl").read_bytes()
        workspace.submit("record", workspace.operation(record={**original, **mutation}), code=2)
        assert (tmp_path / ".harness/events.jsonl").read_bytes() == before
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
