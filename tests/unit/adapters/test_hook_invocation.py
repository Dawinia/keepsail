"""Hook invocations, host transports, ownership and mode detection.

Pure encode/decode cases run everywhere. The real-execution cases run each
transport the way its host does — direct spawn, ``bash -c``, ``powershell.exe`` /
``cmd /c`` — against a stub in a directory whose name contains a space: the class
of input that broke the shell-string installs on Windows.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from keepsail.adapters.agent._hook_invocation import (
    ExecArgv,
    HookInvocation,
    PosixSh,
    PowerShellWrapped,
    TransportError,
    context_session_start_installed,
    is_keepsail_handler,
    legacy_string_is_keepsail,
    lit,
    path,
)
from keepsail.adapters.agent.claude_code import ClaudeCodeAdapter
from keepsail.adapters.agent.codex import CodexAdapter, CodexContextUnsupportedError

_PATHS = [
    "/usr/local/bin/keepsail-hook",
    "/opt/with space/keepsail-hook",
    r"C:\Program Files\keepsail\keepsail-hook.exe",
    r"\\server\share\keepsail-hook.exe",
    "/opt/it's/keepsail-hook",
    "/opt/a&b^c/keepsail-hook",
]


def _invocation(executable: str, cli: str = "/opt/keepsail") -> HookInvocation:
    return HookInvocation(
        executable,
        (lit("--agent"), lit("codex"), lit("--event"), lit("session-start"),
         lit("--context"), lit("--cli"), path(cli)),
    )


# --------------------------------------------------------------------------- round trips


@pytest.mark.parametrize("executable", [*_PATHS, "/opt/$HOME/keepsail-hook"])
def test_exec_argv_round_trips_exactly(executable: str) -> None:
    invocation = _invocation(executable, cli=executable)
    handler = ExecArgv().encode(invocation)
    assert handler == {"type": "command", "command": executable,
                       "args": [arg.value for arg in invocation.args]}
    assert ExecArgv().decode(handler).argv() == invocation.argv()  # type: ignore[union-attr]


@pytest.mark.parametrize("executable", [*_PATHS, "/opt/$HOME/keepsail-hook"])
def test_posix_sh_round_trips_and_keeps_backslashes_on_posix(executable: str) -> None:
    invocation = _invocation(executable, cli=executable)
    decoded = PosixSh().decode(PosixSh().encode(invocation))
    assert decoded is not None and decoded.argv() == invocation.argv()


def test_posix_sh_forward_slashes_only_paths_for_a_windows_target() -> None:
    invocation = HookInvocation(
        r"E:\Work\keepsail\.venv\Scripts\keepsail-hook.EXE",
        (lit(r"a\b"), path(r"C:\Program Files\keepsail\keepsail.exe")),
    )
    handler = PosixSh(windows_target=True).encode(invocation)
    assert handler["command"] == (
        "E:/Work/keepsail/.venv/Scripts/keepsail-hook.EXE 'a\\b' "
        "'C:/Program Files/keepsail/keepsail.exe'"
    )


@pytest.mark.parametrize("executable", [
    "/usr/local/bin/keepsail-hook",
    r"C:\Program Files\keepsail\keepsail-hook.exe",
    r"\\server\share\keepsail-hook.exe",
    "/opt/it's/keepsail-hook",
    "/opt/a&b^c/keepsail-hook",
])
def test_powershell_wrapped_round_trips(executable: str) -> None:
    invocation = _invocation(executable, cli=executable)
    decoded = PowerShellWrapped().decode(PowerShellWrapped().encode(invocation))
    assert decoded is not None
    assert decoded.argv() == [arg.replace("\\", "/") if index in (0, 7) else arg
                               for index, arg in enumerate(invocation.argv())]


@pytest.mark.parametrize("bad", ['"', "%", "!", "$", "`", "\r", "\n"])
def test_powershell_wrapped_refuses_characters_a_host_shell_could_expand(bad: str) -> None:
    with pytest.raises(TransportError, match="contains"):
        PowerShellWrapped().encode(_invocation(f"/opt/x{bad}y/keepsail-hook"))
    with pytest.raises(TransportError, match="contains"):
        PowerShellWrapped().encode(_invocation("/opt/keepsail-hook", cli=f"/opt/x{bad}y/k"))


def test_powershell_wrapped_refuses_non_plain_literals() -> None:
    with pytest.raises(TransportError, match="literal"):
        PowerShellWrapped().encode(HookInvocation("/opt/keepsail-hook", (lit("a b"),)))


# The owner's `.codex/hooks.json` on 2026-11-25 (gitignored, so embedded here): Codex
# knowledge-context entries on Windows must stay identical field for field, so the
# hooks Codex has already trusted are not changed by this refactor.
_HOOK = "E:/Work/keepsail/.venv/Scripts/keepsail-hook.EXE"
_CLI = "E:/Work/keepsail/.venv/Scripts/keepsail.EXE"
_PS = "powershell.exe -NoProfile -NonInteractive -Command \"& '" + _HOOK + "' --agent codex "
_OWNER_CODEX_HOOKS = {
    "PreToolUse": [{"matcher": "^(apply_patch|Edit|Write)$", "hooks": [
        {"type": "command", "command": _PS + "--context\"", "timeout": 10}]}],
    "SessionStart": [{"hooks": [
        {"type": "command", "command": _PS + "--event session-start --context --cli '"
         + _CLI + "'\"", "timeout": 10}]}],
    "Stop": [{"hooks": [{"type": "command", "command": _PS + "--event stop\"", "timeout": 10}]}],
    "UserPromptSubmit": [{"hooks": [
        {"type": "command", "command": _PS + "--event user-prompt-submit --context\"",
         "timeout": 10}]}],
    "PostToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": _PS + "--event post-tool-use --context\"",
         "timeout": 10}]}],
}


def test_codex_windows_context_entries_are_identical_to_the_owner_install(
    tmp_path: Path,
) -> None:
    path_ = tmp_path / ".codex" / "hooks.json"
    path_.parent.mkdir()
    path_.write_text(json.dumps({"hooks": _OWNER_CODEX_HOOKS}, indent=2) + "\n")
    for knowledge_context in (True, None):
        plan = CodexAdapter(knowledge_context=knowledge_context, target_os="nt").plan_hook_install(
            tmp_path,
            hook_executable=r"E:\Work\keepsail\.venv\Scripts\keepsail-hook.EXE",
            cli_executable=r"E:\Work\keepsail\.venv\Scripts\keepsail.EXE",
        )
        assert not plan.changed
        assert json.loads(plan.desired_bytes)["hooks"] == _OWNER_CODEX_HOOKS


# --------------------------------------------------------------------------- adapters


def _hooks(plan: object) -> dict[str, list[dict[str, object]]]:
    return json.loads(plan.desired_bytes)["hooks"]  # type: ignore[attr-defined]


@pytest.mark.parametrize("knowledge_context", [False, True])
@pytest.mark.parametrize("target_os", ["nt", "posix"])
def test_claude_code_writes_exec_form_for_every_hook(
    tmp_path: Path, knowledge_context: bool, target_os: str,
) -> None:
    hook = r"C:\Program Files\keepsail\keepsail-hook.exe"
    cli = r"C:\Program Files\keepsail\keepsail.exe"
    adapter = ClaudeCodeAdapter()
    adapter.knowledge_context = knowledge_context
    adapter.target_os = target_os
    hooks = _hooks(adapter.plan_hook_install(tmp_path, hook_executable=hook, cli_executable=cli))
    expected_events = {"PreToolUse", "SessionStart", "Stop"} | (
        {"UserPromptSubmit", "PostToolUse"} if knowledge_context else set())
    assert set(hooks) == expected_events
    for entries in hooks.values():
        handler = entries[0]["hooks"][0]  # type: ignore[index]
        assert set(handler) == {"type", "command", "args", "timeout"}
        assert handler["command"] in (hook, cli)
    session = hooks["SessionStart"][0]["hooks"][0]  # type: ignore[index]
    if knowledge_context:
        assert session["args"] == ["--agent", "claude-code", "--event", "session-start",
                                   "--context", "--cli", cli]
    else:
        assert session == {"type": "command", "command": cli, "args": ["change", "resume"],
                           "timeout": 10}


def test_claude_code_windows_refuses_a_non_exe_executable_after_settings(
    tmp_path: Path,
) -> None:
    adapter = ClaudeCodeAdapter()
    adapter.target_os = "nt"
    with pytest.raises(RuntimeError, match=r"not a \.exe"):
        adapter.plan_hook_install(tmp_path, hook_executable=r"C:\k\keepsail-hook.cmd",
                                  cli_executable=r"C:\k\keepsail.exe")
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    settings.write_text("{broken")
    with pytest.raises(ValueError, match="not valid JSON"):
        adapter.plan_hook_install(tmp_path, hook_executable=r"C:\k\keepsail-hook.cmd",
                                  cli_executable=r"C:\k\keepsail.exe")
    assert settings.read_text() == "{broken"


def test_codex_transport_follows_the_target_os(tmp_path: Path) -> None:
    windows = _hooks(CodexAdapter(target_os="nt").plan_hook_install(
        tmp_path, hook_executable=r"C:\k\keepsail-hook.exe", cli_executable=r"C:\k\keepsail.exe"))
    posix = _hooks(CodexAdapter(target_os="posix").plan_hook_install(
        tmp_path, hook_executable="/opt/with space/keepsail-hook",
        cli_executable="/opt/keepsail"))
    assert windows["PreToolUse"][0]["hooks"][0]["command"] == (  # type: ignore[index]
        "powershell.exe -NoProfile -NonInteractive -Command "
        "\"& 'C:/k/keepsail-hook.exe' --agent codex\"")
    assert posix["PreToolUse"][0]["hooks"][0]["command"] == (  # type: ignore[index]
        "'/opt/with space/keepsail-hook' --agent codex")
    assert posix["SessionStart"][0]["hooks"][0]["command"] == (  # type: ignore[index]
        "/opt/keepsail change resume")


def test_codex_context_is_refused_off_windows_explicit_or_carried_over(tmp_path: Path) -> None:
    with pytest.raises(CodexContextUnsupportedError, match="--no-knowledge-context"):
        CodexAdapter(knowledge_context=True, target_os="posix").plan_hook_install(
            tmp_path, hook_executable="/opt/keepsail-hook", cli_executable="/opt/keepsail")
    settings = tmp_path / ".codex" / "hooks.json"
    settings.parent.mkdir()
    original = json.dumps({"hooks": _OWNER_CODEX_HOOKS})
    settings.write_text(original)
    with pytest.raises(CodexContextUnsupportedError, match="powershell-exit/v1"):
        CodexAdapter(target_os="posix").plan_hook_install(
            tmp_path, hook_executable="/opt/keepsail-hook", cli_executable="/opt/keepsail")
    plan = CodexAdapter(knowledge_context=False, target_os="posix").plan_hook_install(
        tmp_path, hook_executable="/opt/keepsail-hook", cli_executable="/opt/keepsail")
    assert set(_hooks(plan)) == {"PreToolUse", "SessionStart", "Stop"}
    assert settings.read_text() == original


# --------------------------------------------------------------------------- ownership

# The exact file observed on 2026-11-25: raw Windows paths that Git Bash mangles.
_BROKEN_CLAUDE_SETTINGS = {
    "hooks": {
        "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [
            {"type": "command",
             "command": "E:\\Work\\keepsail\\.venv\\Scripts\\keepsail-hook.EXE --agent claude-code",
             "timeout": 10}]}],
        "SessionStart": [{"hooks": [
            {"type": "command",
             "command": "E:\\Work\\keepsail\\.venv\\Scripts\\keepsail.EXE change resume",
             "timeout": 10}]}],
        "Stop": [{"hooks": [
            {"type": "command",
             "command": "E:\\Work\\keepsail\\.venv\\Scripts\\keepsail-hook.EXE "
                        "--agent claude-code --event stop",
             "timeout": 10}]}],
    },
    "permissions": {"allow": ["PowerShell(Get-ChildItem *)"]},
}


def test_reinstall_repairs_the_broken_2026_11_25_install(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps(_BROKEN_CLAUDE_SETTINGS, indent=2))
    adapter = ClaudeCodeAdapter()
    adapter.target_os = "nt"
    plan = adapter.plan_hook_install(
        tmp_path,
        hook_executable=r"E:\Work\keepsail\.venv\Scripts\keepsail-hook.EXE",
        cli_executable=r"E:\Work\keepsail\.venv\Scripts\keepsail.EXE",
    )
    desired = json.loads(plan.desired_bytes)
    assert desired["permissions"] == _BROKEN_CLAUDE_SETTINGS["permissions"]
    for event in ("PreToolUse", "SessionStart", "Stop"):
        handlers = [h for e in desired["hooks"][event] for h in e["hooks"]]
        assert len(handlers) == 1, event
        assert "args" in handlers[0], event


@pytest.mark.parametrize(("command", "owned"), [
    ("E:\\Work\\keepsail\\.venv\\Scripts\\keepsail.EXE change resume", True),
    ("C:\\Program Files\\keepsail\\keepsail-hook.EXE --agent claude-code", True),
    ('"C:\\Program Files\\keepsail\\keepsail-hook.exe" --agent claude-code --event stop', True),
    ("'/opt/with space/keepsail-hook' --agent claude-code --event session-start", True),
    ("/usr/local/bin/keepsail change resume", True),
    ("othertool change resume", False),
    ("old-keepsail change resume", False),
    ("/usr/local/bin/my-linter --agent claude-code", False),
    ("keepsail status", False),
    ("--agent claude-code", False),
])
def test_legacy_string_ownership(command: str, owned: bool) -> None:
    markers = ("--agent claude-code", "change resume")
    assert legacy_string_is_keepsail(command, markers) is owned
    handler = {"type": "command", "command": command}
    assert is_keepsail_handler(handler, transports=(ExecArgv(), PosixSh()), agent="claude-code",
                               legacy_markers=markers) is owned


def test_exec_form_ownership_and_uninstall(tmp_path: Path) -> None:
    owned = {"type": "command", "command": r"C:\k\keepsail-hook.exe",
             "args": ["--agent", "claude-code", "--event", "stop"]}
    foreign = {"type": "command", "command": r"C:\k\keepsail-hook.exe",
               "args": ["--agent", "codex"]}
    transports = (ExecArgv(), PosixSh())
    assert is_keepsail_handler(owned, transports=transports, agent="claude-code",
                               legacy_markers=())
    assert not is_keepsail_handler(foreign, transports=transports, agent="claude-code",
                                   legacy_markers=())
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    user = {"type": "command", "command": "user-stop"}
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [user, owned]}]}}))
    ClaudeCodeAdapter().on_uninstall(tmp_path)
    assert json.loads(settings.read_text()) == {"hooks": {"Stop": [{"hooks": [user]}]}}


def test_context_detection_ignores_prose_and_user_hooks() -> None:
    transports = (ExecArgv(), PosixSh())
    allow = "Bash(keepsail-hook --agent claude-code --event session-start *)"
    user_hook = {"type": "command", "command": 'echo "unbalanced'}
    prose = json.dumps({
        "permissions": {"allow": [allow]},
        "hooks": {"SessionStart": [{"hooks": [user_hook]}]},
    }).encode()
    assert not context_session_start_installed(prose, transports=transports, agent="claude-code")
    exec_form = json.dumps({"hooks": {"SessionStart": [{"hooks": [{
        "type": "command", "command": r"C:\k\keepsail-hook.exe",
        "args": ["--agent", "claude-code", "--event", "session-start", "--context", "--cli",
                 r"C:\k\keepsail.exe"]}]}]}}).encode()
    assert context_session_start_installed(exec_form, transports=transports, agent="claude-code")
    assert not context_session_start_installed(b"{broken", transports=transports,
                                               agent="claude-code")


# --------------------------------------------------------------------------- real execution

_STUB = "import json, sys\nprint(json.dumps(sys.argv[1:]))\n"


@pytest.fixture
def spaced_stub(tmp_path: Path) -> Path:
    directory = tmp_path / "dir with space"
    directory.mkdir()
    stub = directory / "stub.py"
    stub.write_text(_STUB)
    return stub


def _stub_invocation(stub: Path) -> HookInvocation:
    return HookInvocation(sys.executable, (path(str(stub)), lit("--agent"), lit("claude-code"),
                                           lit("--cli"), path(str(stub))))


def _received(stdout: str) -> list[str]:
    return [value.replace("\\", "/") for value in json.loads(stdout.strip().splitlines()[-1])]


def _expected(stub: Path) -> list[str]:
    value = str(stub).replace("\\", "/")
    return [value, "--agent", "claude-code", "--cli", value][1:]


def test_exec_argv_handler_spawns_exact_argv(spaced_stub: Path) -> None:
    handler = ExecArgv().encode(_stub_invocation(spaced_stub))
    result = subprocess.run([handler["command"], *handler["args"]], capture_output=True,
                            text=True, check=True)
    assert _received(result.stdout) == _expected(spaced_stub)


def _working_bash() -> str | None:
    """A bash that actually runs (Git Bash first on Windows; WSL's stub may not)."""
    candidates = []
    git = shutil.which("git")
    if os.name == "nt" and git:
        root = Path(git).resolve().parents[1]
        candidates += [str(root / "bin" / "bash.exe"), str(root / "usr" / "bin" / "bash.exe")]
    candidates.append(shutil.which("bash") or "")
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            probe = subprocess.run([candidate, "-c", "exit 0"], capture_output=True, check=False)
            if probe.returncode == 0:
                return candidate
    return None


def test_posix_sh_handler_runs_under_bash(spaced_stub: Path) -> None:
    bash = _working_bash()
    if bash is None:
        pytest.skip("no working bash")
    handler = PosixSh(windows_target=os.name == "nt").encode(_stub_invocation(spaced_stub))
    result = subprocess.run([bash, "-c", handler["command"]], capture_output=True, text=True,
                            check=True)
    assert _received(result.stdout) == _expected(spaced_stub)


@pytest.mark.skipif(os.name != "nt", reason="Windows host shells")
@pytest.mark.parametrize("host_shell", [["cmd", "/d", "/c"], ["powershell.exe", "-NoProfile",
                                                               "-NonInteractive", "-Command"]])
def test_powershell_wrapped_handler_runs_under_either_windows_host_shell(
    spaced_stub: Path, host_shell: list[str],
) -> None:
    handler = PowerShellWrapped().encode(_stub_invocation(spaced_stub))
    if host_shell[0] == "cmd":
        result = subprocess.run(f'cmd /d /c "{handler["command"]}"', capture_output=True,
                                text=True, check=True)
    else:
        result = subprocess.run([*host_shell, handler["command"]], capture_output=True,
                                text=True, check=True)
    assert _received(result.stdout) == _expected(spaced_stub)
