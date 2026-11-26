"""Structured agent hook invocations and the transports that encode them.

A hook is modelled as *what to run* — an executable plus an argument list in which
every item is explicitly a literal or a path — never as a shell string. A
transport turns that invocation into the handler fields one host executes, and
decodes a handler back. Adapters choose a transport from the host's documented
contract and the target OS; they never quote or rewrite paths themselves.

- ``ExecArgv``: no shell (``{"command": exe, "args": [...]}``) for hosts that spawn
  an argument vector directly.
- ``PowerShellWrapped``: keepsail names the interpreter itself
  (``powershell.exe -Command "& '<exe>' ..."``) for Windows hosts whose own shell
  is undocumented; valid whether the host hands the string to ``cmd`` or PowerShell.
- ``PosixSh``: ``shlex`` quoting for hosts documented to use a POSIX shell.

Every ``encode`` is checked against its own ``decode`` before a handler leaves this
module, so a rendering that the host would read differently fails at install time
instead of silently at hook time.

API stability: experimental.
"""

from __future__ import annotations

import json
import ntpath
import re
import shlex
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

__all__ = [
    "Arg",
    "ExecArgv",
    "HookInvocation",
    "HookTransport",
    "PosixSh",
    "PowerShellWrapped",
    "TransportError",
    "context_session_start_installed",
    "is_keepsail_handler",
    "legacy_string_is_keepsail",
    "lit",
    "owner_predicate",
    "path",
]

# Executable basenames that identify a keepsail-managed handler.
KEEPSAIL_EXECUTABLES = frozenset({"keepsail", "keepsail.exe", "keepsail-hook", "keepsail-hook.exe"})
HOOK_EXECUTABLES = frozenset({"keepsail-hook", "keepsail-hook.exe"})


class TransportError(ValueError):
    """An invocation cannot be encoded safely for the selected host transport."""


@dataclass(frozen=True)
class Arg:
    """One argument; ``is_path`` marks values that are filesystem paths."""

    value: str
    is_path: bool = False


def lit(value: str) -> Arg:
    return Arg(value)


def path(value: str) -> Arg:
    return Arg(value, is_path=True)


@dataclass(frozen=True)
class HookInvocation:
    executable: str
    args: tuple[Arg, ...] = ()

    def argv(self) -> list[str]:
        return [self.executable, *(arg.value for arg in self.args)]


class HookTransport(Protocol):
    @property
    def name(self) -> str: ...

    def encode(self, invocation: HookInvocation) -> dict[str, Any]:
        """Return the handler fields (``type``, ``command`` and, if any, ``args``)."""
        ...

    def decode(self, handler: Any) -> HookInvocation | None:
        """Return the invocation a handler runs, or ``None`` if not this transport."""
        ...


def _checked(
    transport: HookTransport,
    invocation: HookInvocation,
    handler: dict[str, Any],
    expected: list[str],
) -> dict[str, Any]:
    decoded = transport.decode(handler)
    if decoded is None or decoded.argv() != expected:
        raise TransportError(
            f"{transport.name} cannot represent {invocation.argv()!r} faithfully "
            f"(decodes as {decoded.argv() if decoded else None!r}); refusing to write it"
        )
    return handler


def _forward(value: str) -> str:
    return value.replace("\\", "/")


@dataclass(frozen=True)
class ExecArgv:
    """Host spawns ``command`` with ``args`` as the argument vector; no shell."""

    name: str = "exec-argv"

    def encode(self, invocation: HookInvocation) -> dict[str, Any]:
        handler = {
            "type": "command",
            "command": invocation.executable,
            "args": [arg.value for arg in invocation.args],
        }
        return _checked(self, invocation, handler, invocation.argv())

    def decode(self, handler: Any) -> HookInvocation | None:
        if not isinstance(handler, dict) or handler.get("type") != "command":
            return None
        command, args = handler.get("command"), handler.get("args")
        if not isinstance(command, str) or not isinstance(args, list):
            return None
        if not all(isinstance(arg, str) for arg in args):
            return None
        return HookInvocation(command, tuple(lit(arg) for arg in args))


@dataclass(frozen=True)
class PosixSh:
    """Host runs the ``command`` string through a POSIX shell.

    ``windows_target`` rewrites ``\\`` to ``/`` in the executable and path items (a
    POSIX shell would treat a backslash as an escape); on a POSIX target a
    backslash is a legal path character and is preserved.
    """

    windows_target: bool = False
    name: str = "posix-sh"

    def _normalize(self, invocation: HookInvocation) -> list[str]:
        fix = _forward if self.windows_target else (lambda value: value)
        return [fix(invocation.executable)] + [
            fix(arg.value) if arg.is_path else arg.value for arg in invocation.args
        ]

    def encode(self, invocation: HookInvocation) -> dict[str, Any]:
        argv = self._normalize(invocation)
        handler = {"type": "command", "command": " ".join(shlex.quote(token) for token in argv)}
        return _checked(self, invocation, handler, argv)

    def decode(self, handler: Any) -> HookInvocation | None:
        if not isinstance(handler, dict) or handler.get("type", "command") != "command":
            return None
        command = handler.get("command")
        if not isinstance(command, str) or "args" in handler:
            return None
        try:
            tokens = shlex.split(command)
        except ValueError:
            return None
        if not tokens:
            return None
        return HookInvocation(tokens[0], tuple(lit(token) for token in tokens[1:]))


_PS_PREFIX = 'powershell.exe -NoProfile -NonInteractive -Command "'
# `cmd` expands % and ! inside double quotes; an outer PowerShell expands $ and `
# inside double quotes. & and ^ stay literal in both contexts, so they are allowed.
_PS_REFUSED = frozenset('"%!$`\r\n')
_PS_BARE = re.compile(r"[A-Za-z0-9_.:=/+,-]+")


@dataclass(frozen=True)
class PowerShellWrapped:
    """keepsail names the interpreter: ``powershell.exe -Command "& '<exe>' ..."``.

    Paths are forward-slashed and single-quoted (``'`` doubled); literals must be
    plain tokens. Characters that ``cmd`` or an outer PowerShell would expand inside
    the double-quoted ``-Command`` argument are refused.
    """

    name: str = "powershell-wrapped"

    def encode(self, invocation: HookInvocation) -> dict[str, Any]:
        executable = _forward(invocation.executable)
        argv = [executable]
        parts = ["& " + self._quote(executable)]
        for arg in invocation.args:
            if arg.is_path:
                value = _forward(arg.value)
                parts.append(self._quote(value))
            else:
                value = arg.value
                if not _PS_BARE.fullmatch(value):
                    raise TransportError(f"unsupported literal {value!r} for {self.name}")
                parts.append(value)
            argv.append(value)
        handler = {"type": "command", "command": _PS_PREFIX + " ".join(parts) + '"'}
        return _checked(self, invocation, handler, argv)

    @staticmethod
    def _quote(value: str) -> str:
        refused = sorted(set(value) & _PS_REFUSED)
        if refused:
            raise TransportError(
                f"path {value!r} contains {''.join(refused)!r}, which a Windows host shell "
                "could expand inside the PowerShell wrapper; use a path without these characters"
            )
        return "'" + value.replace("'", "''") + "'"

    def decode(self, handler: Any) -> HookInvocation | None:
        if not isinstance(handler, dict) or handler.get("type", "command") != "command":
            return None
        command = handler.get("command")
        if (not isinstance(command, str) or "args" in handler
                or not command.startswith(_PS_PREFIX) or not command.endswith('"')):
            return None
        inner = command[len(_PS_PREFIX):-1]
        if not inner.startswith("& "):
            return None
        tokens = _ps_tokens(inner[2:])
        if not tokens or not tokens[0][1]:
            return None
        return HookInvocation(
            tokens[0][0], tuple(Arg(value, quoted) for value, quoted in tokens[1:])
        )


def _ps_tokens(text: str) -> list[tuple[str, bool]] | None:
    """Split ``'quoted'`` (``''`` escape) and bare tokens separated by single spaces."""
    tokens: list[tuple[str, bool]] = []
    index = 0
    while index < len(text):
        if text[index] == "'":
            index += 1
            value = []
            while True:
                if index >= len(text):
                    return None
                if text[index] == "'":
                    if text[index + 1:index + 2] == "'":
                        value.append("'")
                        index += 2
                        continue
                    index += 1
                    break
                value.append(text[index])
                index += 1
            tokens.append(("".join(value), True))
        else:
            end = text.find(" ", index)
            end = len(text) if end < 0 else end
            tokens.append((text[index:end], False))
            index = end
        if index < len(text):
            if text[index] != " ":
                return None
            index += 1
    return tokens


def _basename(executable: str) -> str:
    """Windows-aware basename: accepts both separators and spaces."""
    return ntpath.basename(executable.strip()).lower()


def legacy_string_is_keepsail(command: Any, markers: Iterable[str]) -> bool:
    """Recognize a pre-structured keepsail command string by marker + executable.

    Takes the text before the marker, trims whitespace and one pair of surrounding
    quotes, and requires a keepsail basename. Deliberately no ``shlex`` parsing: the
    broken raw Windows form (``E:\\...\\keepsail.EXE change resume``) and paths with
    spaces must still be recognized, and ``othertool change resume`` must not be.
    """
    if not isinstance(command, str):
        return False
    for marker in markers:
        index = command.find(marker)
        if index <= 0:
            continue
        prefix = command[:index].strip()
        if len(prefix) >= 2 and prefix[0] == prefix[-1] and prefix[0] in "'\"":
            prefix = prefix[1:-1]
        if _basename(prefix) in KEEPSAIL_EXECUTABLES:
            return True
    return False


def is_keepsail_handler(
    handler: Any,
    *,
    transports: Sequence[HookTransport],
    agent: str,
    legacy_markers: Iterable[str],
) -> bool:
    """Whether ``handler`` is a keepsail-managed hook for ``agent``.

    Structured first: any transport that decodes it to a keepsail executable whose
    arguments are this agent's (``--agent <agent> ...``) or the CLI's
    ``change resume``. Otherwise the legacy string fallback.
    """
    if not isinstance(handler, dict):
        return False
    for transport in transports:
        invocation = transport.decode(handler)
        if invocation is None:
            continue
        name = _basename(invocation.executable)
        argv = [arg.value for arg in invocation.args]
        if name in HOOK_EXECUTABLES and argv[:2] == ["--agent", agent]:
            return True
        if name in KEEPSAIL_EXECUTABLES and argv[:2] == ["change", "resume"]:
            return True
    return legacy_string_is_keepsail(handler.get("command"), legacy_markers)


def context_session_start_installed(
    raw: bytes | None,
    *,
    transports: Sequence[HookTransport],
    agent: str,
) -> bool:
    """Whether a settings file holds keepsail's context-mode SessionStart hook.

    One detector for every adapter: a SessionStart handler that decodes to
    ``keepsail-hook --agent <agent> --event session-start --context --cli <path>``.
    Permission prose and user hooks never match.
    """
    try:
        settings = json.loads(raw or b"{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    entries = hooks.get("SessionStart") if isinstance(hooks, dict) else None
    if not isinstance(entries, list):
        return False
    expected = ["--agent", agent, "--event", "session-start", "--context", "--cli"]
    for entry in entries:
        inner = entry.get("hooks") if isinstance(entry, dict) else None
        for handler in inner if isinstance(inner, list) else []:
            for transport in transports:
                invocation = transport.decode(handler)
                if invocation is None:
                    continue
                argv = [arg.value for arg in invocation.args]
                if (_basename(invocation.executable) in HOOK_EXECUTABLES
                        and len(argv) == 7 and argv[:6] == expected):
                    return True
    return False


def owner_predicate(
    *,
    transports: Sequence[HookTransport],
    agent: str,
    legacy_markers: Iterable[str],
) -> Callable[[Any], bool]:
    markers = tuple(legacy_markers)
    return lambda handler: is_keepsail_handler(
        handler, transports=transports, agent=agent, legacy_markers=markers
    )
