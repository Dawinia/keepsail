"""Read a specific committed regular blob without consulting the working tree."""

from __future__ import annotations

import subprocess
from pathlib import Path

from keepsail.core.approval import ApprovalError


def optional_regular_blob_bytes(root: Path, commit: str, path: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-z", commit, "--", path], cwd=root,
            capture_output=True, check=True,
        )
        if not result.stdout:
            return None
        entries = result.stdout.split(b"\0")
        if len(entries) != 2 or entries[1] != b"":
            raise ApprovalError(f"committed policy input is missing or ambiguous: {path}")
        header, name = entries[0].split(b"\t", 1)
        fields = header.split()
        if (name != path.encode("utf-8") or len(fields) != 3
                or fields[0] not in {b"100644", b"100755"} or fields[1] != b"blob"):
            raise ApprovalError(f"committed policy input is not a regular blob: {path}")
        return subprocess.check_output(["git", "cat-file", "blob", fields[2].decode("ascii")],
                                       cwd=root)
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as exc:
        if isinstance(exc, ApprovalError):
            raise
        raise ApprovalError(f"cannot read committed policy input {path}: {exc}") from exc


def optional_regular_blob_text(root: Path, commit: str, path: str) -> str | None:
    data = optional_regular_blob_bytes(root, commit, path)
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ApprovalError(f"committed policy input is not UTF-8: {path}") from exc


def regular_blob_bytes(root: Path, commit: str, path: str) -> bytes:
    value = optional_regular_blob_bytes(root, commit, path)
    if value is None:
        raise ApprovalError(f"committed policy input is missing: {path}")
    return value


def regular_blob_text(root: Path, commit: str, path: str) -> str:
    value = optional_regular_blob_text(root, commit, path)
    if value is None:
        raise ApprovalError(f"committed policy input is missing: {path}")
    return value
