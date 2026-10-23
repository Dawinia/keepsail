"""Canonical-only installed package and current hook refresh contracts."""

import json
import os
import subprocess
import sys
import sysconfig
from importlib.metadata import distribution
from pathlib import Path

from keepsail.adapters.agent._settings_merge import (
    apply_settings_merge_plan,
    plan_settings_merge,
)


def test_installed_namespace_and_console_entries_are_canonical_only(tmp_path: Path) -> None:
    dist = distribution("keepsail")
    entries = {e.name: e.value for e in dist.entry_points if e.group == "console_scripts"}
    assert entries == {
        "keepsail": "keepsail.cli:main",
        "keepsail-hook": "keepsail.daemon.hook_entry:main",
        "keepsail-daemon": "keepsail.daemon.server:main",
    }
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    probe = subprocess.run(
        [sys.executable, "-c", "import importlib.util, keepsail; "
         "assert importlib.util.find_spec('super_harness') is None; print(keepsail.__file__)"],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )
    assert probe.returncode == 0, probe.stderr
    scripts = Path(sysconfig.get_path("scripts"))
    suffix = ".exe" if os.name == "nt" else ""
    for old in ("super-harness", "super-harness-hook", "super-harness-daemon"):
        assert not (scripts / (old + suffix)).exists()
    for flag in ("--help", "--version"):
        result = subprocess.run(
            [str(scripts / ("keepsail" + suffix)), flag], cwd=tmp_path,
            env=env, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert ("Keepsail" if flag == "--help" else "0.1.0") in result.stdout


def test_current_hook_refresh_is_idempotent_and_preserves_user_hooks(tmp_path: Path) -> None:
    path = tmp_path / ".claude" / "settings.local.json"
    path.parent.mkdir()
    user = {"hooks": [{"type": "command", "command": "user-check"}]}
    prior = {"hooks": {event: [user, {"hooks": [{"type": "command", "command": command}]}]
                       for event, command in {
                           "PreToolUse": "/prior/keepsail-hook --agent claude-code",
                           "SessionStart": "/prior/keepsail change resume",
                           "Stop": "/prior/keepsail-hook --agent claude-code --event stop",
                       }.items()}}
    original = json.dumps(prior).encode()
    path.write_bytes(original)
    kwargs = {
        "pre_tool_use_command": "/new/keepsail-hook --agent claude-code",
        "session_start_command": "/new/keepsail change resume",
        "stop_command": "/new/keepsail-hook --agent claude-code --event stop",
    }
    apply_settings_merge_plan(plan_settings_merge(path, **kwargs))
    updated = path.read_bytes()
    assert b"/prior/" not in updated
    for entries in json.loads(updated)["hooks"].values():
        assert len(entries) == 2
        assert user in entries
    backups = list(path.parent.glob("*.keepsail-backup.*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original
    plan = plan_settings_merge(path, **kwargs)
    assert not plan.changed
    apply_settings_merge_plan(plan)
    assert path.read_bytes() == updated
    assert list(path.parent.glob("*.keepsail-backup.*")) == backups
