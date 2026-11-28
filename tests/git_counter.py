"""Count git child processes by wrapping ``subprocess.Popen`` (timing-independent)."""

from __future__ import annotations

import subprocess
import threading
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PRODUCT = str(Path(__file__).resolve().parents[1] / "src" / "keepsail")


@dataclass
class GitCalls:
    calls: list[tuple[str, ...]] = field(default_factory=list)
    product: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def total(self) -> int:
        return len(self.calls)

    def named(self, subcommand: str) -> int:
        return sum(1 for argv in self.calls if len(argv) > 1 and argv[1] == subcommand)


@contextmanager
def count_git(monkeypatch: Any) -> Iterator[GitCalls]:
    """Count every git process; ``product`` counts those started from src/keepsail."""
    counter = GitCalls()
    original = subprocess.Popen

    class CountingPopen(original):  # type: ignore[misc, valid-type]
        def __init__(self, args: Any, *rest: Any, **kwargs: Any) -> None:
            argv = tuple(str(item) for item in args) if isinstance(args, (list, tuple)) else ()
            if argv and Path(argv[0]).name.lower() in {"git", "git.exe"}:
                frames = traceback.extract_stack(limit=40)[:-1]
                from_product = any(frame.filename.startswith(_PRODUCT) for frame in frames)
                with counter._lock:
                    counter.calls.append(argv)
                    counter.product += from_product
            super().__init__(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", CountingPopen)
    try:
        yield counter
    finally:
        monkeypatch.setattr(subprocess, "Popen", original)
