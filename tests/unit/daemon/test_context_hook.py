"""Isolated callback fixtures; these are not real Claude session acceptance."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from tests.unit.core.test_knowledge import Workspace


def test_selected_hook_blocks_missing_context_but_legacy_hook_keeps_contract(tmp_path):
    Workspace(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src"),
           "KEEPSAIL_CHANGE_ID": "change-a", "PYTHONDONTWRITEBYTECODE": "1"}
    payload = {"hook_event_name": "PreToolUse", "session_id": "realistic-session-fixture",
               "cwd": str(tmp_path), "tool_name": "Edit",
               "tool_input": {"file_path": str(tmp_path / "src/db.py")}}
    command = [sys.executable, "-B", "-c", "from keepsail.daemon.hook_entry import main;main()",
               "--agent", "claude-code"]
    legacy = subprocess.run(command, cwd=tmp_path, input=json.dumps(payload),
                            capture_output=True, text=True, env=env)
    selected = subprocess.run([*command, "--context"], cwd=tmp_path, input=json.dumps(payload),
                              capture_output=True, text=True, env=env)
    assert legacy.returncode == 0, legacy.stderr
    assert selected.returncode == 2, (selected.stdout, selected.stderr)
    assert "context" in selected.stderr.lower()
    missing_session = subprocess.run(
        [*command, "--context"], cwd=tmp_path,
        input=json.dumps({**payload, "session_id": None}), capture_output=True, text=True, env=env,
    )
    assert missing_session.returncode == 2, missing_session.stderr


def test_invalid_tool_returns_do_not_fill_empty_context_observations(tmp_path, monkeypatch):
    from keepsail.core.context import entry_command, entry_readiness
    from keepsail.daemon.context_hook import observe_return, start_session
    from tests.unit.core import test_knowledge as fixtures

    policy = fixtures.policy()
    policy["observation_issuers"].append("keepsail-cli-observer")
    policy["policy_digest"] = fixtures.policy_digest(policy)
    monkeypatch.setattr(fixtures, "policy", lambda: policy)
    workspace = Workspace(tmp_path)
    entry = start_session(tmp_path, {"hook_event_name": "SessionStart", "session_id": "executor-a",
                                    "source": "startup", "cwd": str(tmp_path)},
                          cli_executable="/tools/keepsail", change="change-a")
    result = workspace.runner.invoke(fixtures.main, [
        "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
        "--entry", entry["entry_id"],
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"]["total_pages"] == 1
    callback = {"hook_event_name": "PostToolUse", "session_id": "executor-a",
                "cwd": str(tmp_path), "tool_name": "Bash", "tool_use_id": "fixture-tool-1",
                "tool_input": {"command": entry_command(entry)},
                "tool_response": {"stdout": result.stdout, "stderr": "", "interrupted": False}}
    cases = []
    for field, value in [("interrupted", True), ("persistedOutputPath", "/tmp/unobserved"),
                         ("backgroundTaskId", "background-1"), ("stdout", result.stdout[:-30])]:
        altered = deepcopy(callback)
        altered["tool_response"][field] = value
        cases.append(altered)
    altered = deepcopy(callback)
    altered["tool_response"]["stdout"] = result.stdout.replace('{', '{"exit_code":0,', 1)
    cases.append(altered)
    altered = deepcopy(callback)
    altered["agent_id"] = "another-executor"
    cases.append(altered)
    altered = deepcopy(callback)
    altered["cwd"] = str(tmp_path.parent)
    cases.append(altered)
    for altered in cases:
        with pytest.raises(ValueError):
            observe_return(tmp_path, altered)
        assert not entry_readiness(tmp_path, "change-a", "executor-a")["ready"]
    assert observe_return(tmp_path, callback)["empty_set_observed"]
    assert observe_return(tmp_path, callback)["complete"]
    assert entry_readiness(tmp_path, "change-a", "executor-a")["ready"]
    assert workspace.cli("knowledge", "show")["data"]["observations"] == []
