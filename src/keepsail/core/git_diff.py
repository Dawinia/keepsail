"""Strict parsing of Git name-status records."""

from __future__ import annotations

import posixpath
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiffEntry:
    """One ``git diff --name-status`` row.

    ``paths`` is a 1-tuple for A/M/D and a 2-tuple ``(old, new)`` for
    renames/copies (status ``R<score>`` / ``C<score>``).
    """

    status: str
    paths: tuple[str, ...]


def parse_name_status_z(raw: str) -> list[DiffEntry]:
    """Parse Git's NUL protocol without trimming or unquoting path bytes."""
    if not raw:
        return []
    if not raw.endswith("\0"):
        raise ValueError("incomplete NUL-delimited Git diff")
    fields = raw[:-1].split("\0")
    entries: list[DiffEntry] = []
    index = 0
    while index < len(fields):
        status = fields[index]
        count = 2 if status.startswith(("R", "C")) else 1
        valid = (status in {"A", "M", "D", "T", "U", "X", "B"}
                 or (status[:1] in {"R", "C"} and status[1:].isdigit()))
        paths = tuple(fields[index + 1:index + count + 1])
        if not valid or len(paths) != count or not all(paths):
            raise ValueError("malformed NUL-delimited Git diff")
        entries.append(DiffEntry(status=status, paths=paths))
        index += count + 1
    return entries


def require_literal_paths(entries: list[DiffEntry]) -> None:
    """Reject Git names the delivery-policy path language cannot represent safely."""
    for entry in entries:
        for path in entry.paths:
            if (path != path.strip() or posixpath.normpath(path) != path or path.startswith("/")
                    or any(char in path for char in "\\*?[]\x00")):
                raise ValueError(f"unsupported literal Git path for delivery policy: {path!r}")


def require_literal_git_diff(root: Path, *, base: str, head: str) -> None:
    """Check exact Git names without changing the legacy manifest representation."""
    try:
        raw = subprocess.check_output(
            ["git", "diff", "--name-status", "-z", "--find-renames", f"{base}...{head}"],
            cwd=root,
        ).decode("utf-8")
        require_literal_paths(parse_name_status_z(raw))
    except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
        raise ValueError("cannot read literal Git paths for delivery policy") from exc
