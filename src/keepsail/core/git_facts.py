"""Operation-scoped reuse of immutable Git facts (no keepsail imports: low layer).

A ``git_fact_scope`` covers one CLI operation.  Facts are cached only under a
scope, only when keyed by full object ids, and only after a successful Git
call; the scope's end discards them and closes scoped resources (the
persistent ``git cat-file --batch`` reader).
"""

from __future__ import annotations

import re
import threading
from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast

_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_MISSING = object()
_T = TypeVar("_T")
MAX_ENTRIES = 4096
MAX_BYTES = 32 * 1024 * 1024


class _Closable(Protocol):
    def close(self) -> None: ...


def is_object_id(value: object) -> bool:
    return isinstance(value, str) and _OID.fullmatch(value) is not None


def root_key(root: Path) -> str:
    return str(root.resolve())


class GitFactCache:
    """A locked LRU of immutable Git facts with entry and byte limits."""

    def __init__(self, *, max_entries: int = MAX_ENTRIES, max_bytes: int = MAX_BYTES) -> None:
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self._entries: OrderedDict[tuple[Any, ...], tuple[object, int]] = OrderedDict()
        self._bytes = 0
        self._resource: tuple[str, _Closable] | None = None

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def size_bytes(self) -> int:
        return self._bytes

    def get(self, key: tuple[Any, ...]) -> object:
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                return _MISSING
            self._entries.move_to_end(key)
            return item[0]

    def put(self, key: tuple[Any, ...], value: object) -> None:
        size = len(value) if isinstance(value, (bytes, str)) else 64
        if size > self.max_bytes:
            return
        with self._lock:
            old = self._entries.pop(key, None)
            if old is not None:
                self._bytes -= old[1]
            self._entries[key] = (value, size)
            self._bytes += size
            while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
                _, (_, evicted) = self._entries.popitem(last=False)
                self._bytes -= evicted

    def resource(self, key: str, factory: Callable[[], _T]) -> _T | None:
        """At most one scoped resource (the batch reader), for the first key requested."""
        with self._lock:
            if self._resource is None:
                self._resource = (key, cast(_Closable, factory()))
            owner, value = self._resource
            return cast(_T, value) if owner == key else None

    def close(self) -> None:
        with self._lock:
            resource, self._resource = self._resource, None
        if resource is not None:
            resource[1].close()


_scope: ContextVar[GitFactCache | None] = ContextVar("keepsail_git_facts", default=None)


@contextmanager
def git_fact_scope() -> Iterator[GitFactCache]:
    """Reuse immutable Git facts for one operation; discard them when it ends."""
    current = _scope.get()
    if current is not None:
        yield current
        return
    cache = GitFactCache()
    token = _scope.set(cache)
    try:
        yield cache
    finally:
        _scope.reset(token)
        cache.close()


def active_cache() -> GitFactCache | None:
    return _scope.get()


def memoized(key: tuple[Any, ...], compute: Callable[[], _T], *, cacheable: bool) -> _T:
    """Return a cached fact, or compute it and cache it only if the call succeeds."""
    cache = _scope.get()
    if cache is None or not cacheable:
        return compute()
    hit = cache.get(key)
    if hit is not _MISSING:
        return cast(_T, hit)
    value = compute()
    cache.put(key, value)
    return value
