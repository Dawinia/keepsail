"""Installed brand aliases and upgrade from real legacy hook ownership."""

import json
import os
import subprocess
import sysconfig
from importlib.metadata import distribution
from pathlib import Path

from super_harness.adapters.agent._settings_merge import (
    apply_settings_merge_plan,
    plan_settings_merge,
)


def test_installed_console_aliases_share_implementation(tmp_path: Path) -> None:
    dist = distribution("keepsail")
    entries = {e.name: e.value for e in dist.entry_points if e.group == "console_scripts"}
    for suffix in ("", "-hook", "-daemon"):
        assert entries[f"keepsail{suffix}"] == entries[f"super-harness{suffix}"]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    for name in ("keepsail", "super-harness"):
        binary = Path(sysconfig.get_path("scripts")) / (name + (".exe" if os.name == "nt" else ""))
        result = subprocess.run([str(binary), "--help"], cwd=tmp_path,
                                env=env, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "Keepsail" in result.stdout
        result = subprocess.run([str(binary), "--version"], cwd=tmp_path,
                                env=env, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        assert "0.1.0" in result.stdout


def test_legacy_hook_refresh_is_idempotent_and_preserves_user_hooks(tmp_path: Path) -> None:
    path = tmp_path / ".claude" / "settings.local.json"
    path.parent.mkdir()
    user = {"hooks": [{"type": "command", "command": "user-check"}]}
    old = {"hooks": {event: [user, {"hooks": [{"type": "command", "command": command}]}]
                     for event, command in {
                         "PreToolUse": "/old/super-harness-hook --agent claude-code",
                         "SessionStart": "/old/super-harness change resume",
                         "Stop": "/old/super-harness-hook --agent claude-code --event stop",
                     }.items()}}
    original = json.dumps(old).encode()
    path.write_bytes(original)
    kwargs = {
        "pre_tool_use_command": "/new/keepsail-hook --agent claude-code",
        "session_start_command": "/new/keepsail change resume",
        "stop_command": "/new/keepsail-hook --agent claude-code --event stop",
    }
    apply_settings_merge_plan(plan_settings_merge(path, **kwargs))
    updated = path.read_bytes()
    assert b"super-harness" not in updated
    for entries in json.loads(updated)["hooks"].values():
        assert len(entries) == 2
        assert user in entries
    backups = list(path.parent.glob("*.super-harness-backup.*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original
    plan = plan_settings_merge(path, **kwargs)
    assert not plan.changed
    apply_settings_merge_plan(plan)
    assert path.read_bytes() == updated
    assert list(path.parent.glob("*.super-harness-backup.*")) == backups
