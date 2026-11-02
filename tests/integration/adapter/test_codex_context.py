"""Actual local processes and supplied callback fixtures, not real Codex A/B."""
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from keepsail.adapters.agent.codex import CodexAdapter
from keepsail.core.context import entry_command, read_entry
from tests.unit.core import test_knowledge as fixtures


@pytest.mark.skipif(os.name != "nt", reason="selected Windows Codex desktop transport")
@pytest.mark.parametrize("shell", ["powershell.exe", "pwsh.exe"])
def test_native_powershell_hook_and_cli_roundtrip_from_space_paths(tmp_path, monkeypatch, shell):
    if not shutil.which(shell):
        pytest.skip("optional PowerShell executable unavailable: " + shell)
    policy = fixtures.policy()
    policy["observation_issuers"].append("keepsail-cli-observer")
    policy["policy_digest"] = fixtures.policy_digest(policy)
    monkeypatch.setattr(fixtures, "policy", lambda: policy)
    workspace = fixtures.Workspace(tmp_path)
    runtime = tmp_path / "runtime with space"
    runtime.mkdir()
    cli, hook = [runtime / n for n in ("keepsail.exe", "keepsail-hook.exe")]
    for target in (cli, hook):
        shutil.copyfile(Path(sys.executable).with_name(target.name), target)
    settings = json.loads(CodexAdapter(knowledge_context=True).plan_hook_install(
        tmp_path, hook_executable=str(hook), cli_executable=str(cli),
    ).desired_bytes)
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "CI": "1"}

    def callback(event, payload):
        command = settings["hooks"][event][0]["hooks"][0]["command"]
        result = subprocess.run(shlex.split(command), cwd=tmp_path, env=env,
                                input=json.dumps(payload), capture_output=True, text=True,
                                encoding="utf-8", timeout=10)
        assert result.returncode == 0, (result.stdout, result.stderr)
        return json.loads(result.stdout) if result.stdout else None

    identity = {"session_id": "fixture-desktop-a", "cwd": str(tmp_path)}
    hint = callback("SessionStart", {**identity, "hook_event_name": "SessionStart",
                                     "source": "startup"})
    hint = json.loads(hint["hookSpecificOutput"]["additionalContext"])
    callback("UserPromptSubmit", {**identity, "hook_event_name": "UserPromptSubmit",
                                   "turn_id": "fixture-root-turn"})
    denied = callback("PreToolUse", {**identity, "hook_event_name": "PreToolUse",
                                     "turn_id": "fixture-root-turn", "tool_name": "apply_patch",
                                     "tool_input": {"command": "*** Begin Patch\n"
                                         "*** Add File: src/db/new.py\n+pass\n*** End Patch\n"}})
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    packet = workspace.cli("change", "context", "change-a", "--bind-startup",
                           hint["startup_id"])["data"]
    entry = read_entry(tmp_path, packet["entry_id"])
    page = 1
    while page:
        command = entry_command(entry, page)
        result = subprocess.run([shell, "-NoProfile", "-NonInteractive",
                                 "-Command", command], cwd=tmp_path, env=env,
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
        assert result.returncode == 0, result.stderr
        lines = result.stdout.rstrip("\n").split("\n")
        assert lines[-1] == (
            "__KEEPSAIL_CONTEXT_EXIT_V1__:" + entry["entry_id"] + ":" + str(page) + ":0")
        data = json.loads(lines[-2])["data"]
        callback("PostToolUse", {**identity, "hook_event_name": "PostToolUse",
                                  "turn_id": "fixture-root-turn", "tool_name": "Bash",
                                  "tool_use_id": f"fixture-tool-{page}",
                                  "tool_input": {"command": command},
                                  "tool_response": result.stdout})
        page = data["next_page"]
    from keepsail.core.context import entry_readiness
    pending = entry_readiness(tmp_path, "change-a", identity["session_id"])
    assert not pending["ready"]
    assert "current entry context acquisition missing" in pending["blocking_reasons"]
    finalization = subprocess.run([shell, "-NoProfile", "-NonInteractive",
                                   "-Command", data["next_command"]], cwd=tmp_path, env=env,
                                  capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert finalization.returncode == 0, finalization.stderr
    assert json.loads(finalization.stdout)["data"]["native_acquisition"] == "not_applicable"
    from keepsail.core.knowledge import load_ledger, load_policy

    ledger, _ = load_ledger(tmp_path / ".harness/events.jsonl", load_policy(tmp_path))
    assert ledger["observations"] == []
    assert len(ledger["context_observations"]) == 1
    assert next(iter(ledger["context_observations"].values()))["versions"] == []
    allowed = callback("PreToolUse", {**identity, "hook_event_name": "PreToolUse",
                                      "turn_id": "fixture-root-turn", "tool_name": "apply_patch",
                                      "tool_input": {"command": "*** Begin Patch\n"
                                          "*** Add File: src/db/new.py\n+pass\n*** End Patch\n"}})
    assert allowed is None
    callback("PostToolUse", {**identity, "hook_event_name": "PostToolUse",
                              "turn_id": "fixture-root-turn", "tool_name": "Bash",
                              "tool_use_id": "fixture-repeat-last-page",
                              "tool_input": {"command": command},
                              "tool_response": result.stdout})
    assert callback("UserPromptSubmit", {**identity, "hook_event_name": "UserPromptSubmit",
                                         "turn_id": "fixture-next-root-turn"}) is None
    callback("SessionStart", {**identity, "hook_event_name": "SessionStart", "source": "compact"})
    with pytest.raises(ValueError, match="replaced"):
        read_entry(tmp_path, entry["entry_id"])
