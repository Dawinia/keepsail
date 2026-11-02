"""Real Keepsail processes with explicit host callback fixtures, not Claude A/B."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from keepsail.core.context import entry_command, session_entry
from tests.unit.core import test_knowledge as fixtures


def test_process_recovery_exposes_v2_without_rewriting_v1(tmp_path, monkeypatch):
    policy = fixtures.policy()
    policy["observation_issuers"].append("keepsail-cli-observer")
    policy["policy_digest"] = fixtures.policy_digest(policy)
    monkeypatch.setattr(fixtures, "policy", lambda: policy)
    workspace = fixtures.Workspace(tmp_path)
    v1 = workspace.recognize(fixtures.version())
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src"),
           "KEEPSAIL_CHANGE_ID": "change-a", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
    cli = Path(sys.executable).with_name("keepsail.exe" if os.name == "nt" else "keepsail")
    hook = [sys.executable, "-B", "-c", "from keepsail.daemon.hook_entry import main;main()",
            "--agent", "claude-code", "--context"]

    def callback(event, payload, expected=0):
        result = subprocess.run([*hook, "--event", event, "--cli", str(cli)],
                                cwd=tmp_path, input=json.dumps(payload), env=env,
                                capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == expected, (result.stdout, result.stderr)
        return result

    def start(session):
        result = callback("session-start", {
            "hook_event_name": "SessionStart", "session_id": session, "source": "resume",
            "cwd": str(tmp_path),
        })
        assert len(result.stdout.encode("utf-8")) <= 8 * 1024
        hint = json.loads(json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])
        assert hint["change"] == "change-a"
        return session_entry(tmp_path, session)

    def retrieve(entry):
        page = 1
        while page is not None:
            result = subprocess.run([
                sys.executable, "-B", "-c", "from keepsail.cli import main;main()",
                "--workspace", str(tmp_path), "--json", "change", "context", "change-a",
                "--entry", entry["entry_id"], "--page", str(page),
            ], cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8")
            assert result.returncode == 0, result.stderr
            data = json.loads(result.stdout)["data"]
            callback("post-tool-use", {
                "hook_event_name": "PostToolUse", "session_id": entry["session_id"],
                "cwd": str(tmp_path), "tool_name": "Bash",
                "tool_use_id": f"fixture-{entry['entry_id']}-{data['manifest_id']}-{page}",
                "tool_input": {"command": entry_command(entry, page)},
                "tool_response": {"stdout": result.stdout, "stderr": result.stderr,
                                  "interrupted": False},
            })
            page = data["next_page"]

    def edit(session, expected):
        return callback("pre-tool-use", {
            "hook_event_name": "PreToolUse", "session_id": session, "cwd": str(tmp_path),
            "tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "src/db.py")},
        }, expected)

    first = start("fixture-session-a")
    reminder = callback("user-prompt-submit", {
        "hook_event_name": "UserPromptSubmit", "session_id": "fixture-session-a",
        "cwd": str(tmp_path),
    })
    assert "next_command" in reminder.stdout
    edit("fixture-session-a", 2)
    retrieve(first)
    edit("fixture-session-a", 0)
    quiet = callback("user-prompt-submit", {
        "hook_event_name": "UserPromptSubmit", "session_id": "fixture-session-a",
        "cwd": str(tmp_path),
    })
    assert quiet.stdout == ""
    for extra in ({"agent_id": "fixture-child"}, {"session_id": None}, {"tool_input": None}):
        callback("pre-tool-use", {
            "hook_event_name": "PreToolUse", "session_id": "fixture-session-a",
            "cwd": str(tmp_path), "tool_name": "Edit",
            "tool_input": {"file_path": str(tmp_path / "src/db.py")}, **extra,
        }, 2)
    second = start("fixture-session-b")
    edit("fixture-session-b", 2)
    retrieve(second)
    edit("fixture-session-b", 0)
    v2 = workspace.recognize(fixtures.version(body="PostgreSQL 17+", previous=v1))
    blocked = edit("fixture-session-b", 2)
    assert "refresh" in blocked.stderr
    view = workspace.cli("change", "resume", "change-a")["data"]["knowledge"]
    impact = next(i for i in view["impacts"] if i["status"] != "resolved")
    frozen = {k: v for k, v in impact.items()
              if k not in {"impact_id", "status", "disposition_id", "disposition"}}
    evidence = workspace.evidence("disposition", impact["impact_id"], "continue",
                                  impact=frozen, use_version=v2)
    workspace.submit("import", workspace.operation(evidence=evidence))
    retrieve(second)
    edit("fixture-session-b", 0)
    history = workspace.cli("knowledge", "show")["data"]
    assert {v["version_digest"] for v in history["versions"]} == {v1, v2}
    assert {o["session_id"] for o in history["observations"]} == {
        "fixture-session-a", "fixture-session-b",
    }
    assert any(o["version_digest"] == v1 for o in history["observations"])
