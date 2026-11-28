"""Read committed regular blobs without consulting the working tree.

Within one CLI operation (``git_fact_scope``) immutable Git facts are reused:
object-id keyed tree listings and blob bytes, a commit's ``.harness/`` listing,
full-OID ``resolve_commit`` and OID ``is_ancestor``/``merge_base`` results.
Mutable refs (``HEAD``, branch names, ``for-each-ref``) are never cached,
failed Git calls are never cached, and structural checks (regular file, UTF-8)
are redone on every read.  Outside a scope nothing is cached.

Assumption (docs/limitations.md): no ``fetch --unshallow``, replace or graft
rewrites the repository during one operation.  The existing code already
queried Git several times per operation under the same assumption.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import IO, cast

from keepsail.core.approval import ApprovalError
from keepsail.core.git_facts import (
    active_cache,
    git_fact_scope,
    is_object_id,
    memoized,
    root_key,
)

__all__ = ["git_fact_scope", "optional_regular_blob_bytes", "optional_regular_blob_text",
           "regular_blob_bytes", "regular_blob_text", "regular_blob_texts"]
_HARNESS = ".harness/"


class _BatchReader:
    """One persistent ``git cat-file --batch``; each request completes under a lock."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._lock = threading.Lock()
        self._process = subprocess.Popen(
            ["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

    def read(self, oid: str) -> tuple[bytes, bytes]:
        """Return ``(type, content)``; any protocol anomaly fails closed."""
        with self._lock:
            process = self._process
            stdin = cast(IO[bytes], process.stdin)
            stdout = cast(IO[bytes], process.stdout)
            if process.poll() is not None:
                raise ApprovalError("git cat-file --batch exited unexpectedly")
            try:
                stdin.write(oid.encode("ascii") + b"\n")
                stdin.flush()
                header = stdout.readline()
                if not header.endswith(b"\n"):
                    raise ApprovalError("git cat-file --batch ended before answering")
                fields = header.split()
                if len(fields) == 2 and fields[1] == b"missing":
                    raise ApprovalError(f"committed object is missing: {oid}")
                if len(fields) != 3 or fields[0] != oid.encode("ascii"):
                    raise ApprovalError("invalid git cat-file --batch response header")
                size = int(fields[2])
                if size < 0:
                    raise ApprovalError("invalid git cat-file --batch object size")
                data = stdout.read(size + 1)
            except (OSError, ValueError) as exc:
                raise ApprovalError(f"git cat-file --batch failed: {exc}") from exc
            if len(data) != size + 1 or data[-1:] != b"\n":
                raise ApprovalError("git cat-file --batch returned a truncated object")
            return fields[1], data[:size]

    def close(self) -> None:
        process = self._process
        try:
            if process.stdin is not None:
                process.stdin.close()
            process.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            process.wait()
        finally:
            if process.stdout is not None:
                process.stdout.close()


def _ls_tree(root: Path, commit: str, path: str) -> bytes:
    """Raw ``ls-tree -z`` output for one path; a ``.harness/`` child uses the subtree listing."""
    def run(target: str) -> bytes:
        return subprocess.run(["git", "ls-tree", "-z", commit, "--", target], cwd=root,
                              capture_output=True, check=True).stdout

    cacheable = is_object_id(commit) and active_cache() is not None
    if cacheable and path.startswith(_HARNESS) and "/" not in path[len(_HARNESS):]:
        listing = memoized(("harness-tree", root_key(root), commit),
                           lambda: run(_HARNESS), cacheable=True)
        encoded = path.encode("utf-8")
        return b"".join(entry + b"\0" for entry in listing.split(b"\0")
                        if entry and entry.split(b"\t", 1)[-1] == encoded)
    return memoized(("ls-tree", root_key(root), commit, path), lambda: run(path),
                    cacheable=cacheable)


def _blob(root: Path, oid: str) -> bytes:
    def read() -> bytes:
        cache = active_cache()
        reader = (cache.resource(root_key(root), lambda: _BatchReader(root))
                  if cache is not None else None)
        if reader is None:
            return subprocess.check_output(["git", "cat-file", "blob", oid], cwd=root)
        kind, data = reader.read(oid)
        if kind != b"blob":
            raise ApprovalError(f"committed object is not a blob: {oid}")
        return data

    return memoized(("blob", root_key(root), oid), read, cacheable=True)


def optional_regular_blob_bytes(root: Path, commit: str, path: str) -> bytes | None:
    try:
        stdout = _ls_tree(root, commit, path)
        if not stdout:
            return None
        entries = stdout.split(b"\0")
        if len(entries) != 2 or entries[1] != b"":
            raise ApprovalError(f"committed policy input is missing or ambiguous: {path}")
        header, name = entries[0].split(b"\t", 1)
        fields = header.split()
        if (name != path.encode("utf-8") or len(fields) != 3
                or fields[0] not in {b"100644", b"100755"} or fields[1] != b"blob"):
            raise ApprovalError(f"committed policy input is not a regular blob: {path}")
        return _blob(root, fields[2].decode("ascii"))
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


def regular_blob_texts(root: Path, commit: str, paths: list[str]) -> dict[str, str]:
    """Read several committed UTF-8 regular blobs with one tree and one blob query.

    Inside a scope the tree listing and persistent batch reader are reused; the
    structural checks are identical to ``regular_blob_text``.
    """
    if not paths or len(set(paths)) != len(paths):
        raise ApprovalError("committed policy input paths must be non-empty and unique")
    if active_cache() is not None:
        return {path: regular_blob_text(root, commit, path) for path in paths}
    try:
        tree = subprocess.run(["git", "ls-tree", "-z", commit, "--", *paths], cwd=root,
                              capture_output=True, check=True).stdout
        expected = {path.encode("utf-8"): path for path in paths}
        objects: dict[str, bytes] = {}
        for entry in tree.split(b"\0"):
            if not entry:
                continue
            header, name = entry.split(b"\t", 1)
            fields = header.split()
            if (name not in expected or expected[name] in objects or len(fields) != 3
                    or fields[0] not in {b"100644", b"100755"} or fields[1] != b"blob"):
                raise ApprovalError("committed policy inputs are not exact regular blobs")
            objects[expected[name]] = fields[2]
        missing = [path for path in paths if path not in objects]
        if missing:
            raise ApprovalError(f"committed policy input is missing: {missing[0]}")
        result = subprocess.run(["git", "cat-file", "--batch"], cwd=root, capture_output=True,
                                input=b"".join(objects[path] + b"\n" for path in paths),
                                check=True).stdout
        contents: dict[str, str] = {}
        for path in paths:
            header, result = result.split(b"\n", 1)
            fields = header.split()
            if len(fields) != 3 or fields[0] != objects[path] or fields[1] != b"blob":
                raise ApprovalError(f"invalid committed blob response: {path}")
            size = int(fields[2])
            if size < 0 or len(result) < size + 1 or result[size:size + 1] != b"\n":
                raise ApprovalError(f"invalid committed blob response: {path}")
            try:
                contents[path] = result[:size].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ApprovalError(f"committed policy input is not UTF-8: {path}") from exc
            result = result[size + 1:]
        if result:
            raise ApprovalError("unexpected trailing committed blob response")
        return contents
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError) as exc:
        if isinstance(exc, ApprovalError):
            raise
        raise ApprovalError(f"cannot read committed policy inputs: {exc}") from exc
