"""EventWriter — append-only writer for .harness/events.jsonl.

Atomicity guarantees (per lifecycle-event-model §2 + §3.9 #1):
- Single line per event (newline-terminated JSON)
- POSIX O_APPEND ensures kernel-atomic append across processes
- A cross-platform exclusive lock on `.harness/.events.lock` serializes the WHOLE
  validate→append critical section across writers (F4 fix). O_APPEND alone keeps
  each write() atomic, but emit first READS the stream to validate the new event
  against derived state; without a lock spanning read+append, two writers both
  validate the stale stream, both pass, and both append — landing an event that
  is illegal on replay (which the must_pass `lifecycle-ordering` baseline flags
  as tamper on an append-only log with no repair path). The flock closes that
  TOCTOU. Mirrors `post_emit.py`'s `.state.lock` idiom; lock order is
  events-before-state (emit releases `.events.lock` before the caller's
  `refresh_state_after_emit` takes `.state.lock`; never nested).
- threading.Lock is a PER-INSTANCE thread guard (serializes threads sharing ONE
  EventWriter). It is NOT process-wide: two EventWriter instances in one process
  are serialized by the flock, not this lock (kept as cheap defense-in-depth).
- fsync after each write — durable on power loss (cost: ~ms per emit; v0.1
  accepts this; v0.2 may add batch-fsync option)

Supported filesystems (spec §3.9 #1): Linux ext4, macOS APFS. NOT supported:
NFS / SMB / FUSE — these break atomic append AND advisory-lock semantics. flock
is POSIX-only (Linux/macOS), consistent with the module's local-fs stance.
README must call this out before users try to put .harness/ on a network drive.

emit-time validation: this writer accepts a `skip_validation: bool = False`
kwarg. When False (default) emit calls `emit_validation.validate_preconditions`
UNDER the flock, BEFORE writing — illegal transitions raise
`EmitPreconditionError` and nothing hits disk (strict per spec §3.8.1). Pass
`skip_validation=True` to bypass validation (used by replay/import tooling that
already vetted the stream); the append still holds the flock so a skip write
cannot slip into another writer's validate→append window.
"""

import base64
import json
import os
import tempfile
import threading
from hashlib import sha256
from pathlib import Path

from keepsail.core.approval import authorizing_event
from keepsail.core.emit_validation import (
    EmitPreconditionError,
    is_new_contract_event,
    validate_preconditions,
)
from keepsail.core.events import Event, serialize_event
from keepsail.core.file_lock import exclusive_file_lock

__all__ = ["EmitPreconditionError", "EventWriter"]


# @decision:d-events-append-only
class EventWriter:
    """Append-only writer to events.jsonl.

    Thread-safe within a process (per-instance lock) AND across writer instances
    / processes (an OS file lock on a sentinel). NOT safe on network filesystems
    (see module docstring).
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        # Cross-process critical-section lock sentinel. Sibling of events.jsonl,
        # equal to `paths.lock_path(root, "events")` (`.harness/.events.lock`);
        # derived from self.path so EventWriter stays path-only.
        self._lock_path = self.path.parent / ".events.lock"
        # Ensure parent directory exists — common case: `.harness/` is brand
        # new on first emit. mkdir(parents=True, exist_ok=True) is idempotent.
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        event: Event,
        *,
        skip_validation: bool = False,
        historical_replay: bool = False,
    ) -> None:
        """Append one event to events.jsonl.

        Args:
            event: the Event to write (already constructed by caller)
            skip_validation: when True, bypass emit-time precondition checks
                (illegal transitions + hard prereqs). Default False — emit is
                strict per spec §3.8.1 and raises EmitPreconditionError before
                touching disk. Set True only for replay/import paths where the
                event stream has already been vetted.
            historical_replay: explicit escape hatch for reconstructing an
                immutable historical stream. Normal callers cannot combine
                ``skip_validation`` with an authorizing or new-contract event.

        Raises:
            EmitPreconditionError: if `skip_validation=False` and the event
                would create an illegal transition or is missing a hard
                prerequisite (e.g. implementation_complete without prior
                verification_passed on the same change_id). ALSO raised —
                regardless of `skip_validation` — for a non-str `timestamp`:
                the writer is the single choke point to disk and does not
                round-trip `parse_event_line`, so shape is enforced here (a
                widening of EmitPreconditionError's documented transition-only
                meaning; reusing it keeps the 12+ existing "emit rejected, stay
                alive" handlers working). Type-only: `""` stays legal (the
                dispatcher stamps blank timestamps before emit).
        """
        self.emit_many(
            [event],
            skip_validation=skip_validation,
            historical_replay=historical_replay,
        )

    def emit_many(
        self,
        events: list[Event],
        *,
        skip_validation: bool = False,
        historical_replay: bool = False,
    ) -> None:
        """Validate and append a small event transaction under one lock.

        External evidence import needs an evidence record and its lifecycle
        conclusion to become visible together. Validation runs against a
        temporary copy of the append-only stream, so a failed second event
        cannot leave a misleading orphan evidence record in the real log.
        """
        if not events:
            return
        for event in events:
            if not isinstance(event.timestamp, str):
                raise EmitPreconditionError(
                    f"timestamp must be a string, got {type(event.timestamp).__name__}"
                )
        # Pure prep stays outside the lock to keep the critical section minimal.
        data = b"".join((serialize_event(event) + "\n").encode("utf-8") for event in events)
        with self._lock:  # per-instance thread guard (see class docstring)
            # The process lock spans validate+append so no writer validates a
            # stale stream then appends over another writer's transition.
            with exclusive_file_lock(self._lock_path):
                if self.path.with_name(".events.recovery-pending.json").exists():
                    raise EmitPreconditionError(
                        "historical recovery append pending; resume change recover")
                if any(event.type == "historical_change_recovered" for event in events):
                    raise EmitPreconditionError(
                        "historical recovery requires the strict recovery transaction")
                guarded = [
                    event
                    for event in events
                    if authorizing_event(event.type)
                    or is_new_contract_event(self.path, event)
                ]
                if skip_validation and guarded and not historical_replay:
                    event = guarded[0]
                    raise EmitPreconditionError(
                        f"skip_validation cannot write authorizing or new-contract "
                        f"event {event.type!r}; use the strict writer or explicit "
                        "historical_replay"
                    )
                if not skip_validation:
                    temp_path: Path | None = None
                    try:
                        with tempfile.NamedTemporaryFile(
                            mode="wb",
                            dir=self.path.parent,
                            prefix=".events-",
                            suffix=".tmp",
                            delete=False,
                        ) as temp:
                            temp_path = Path(temp.name)
                            if self.path.exists():
                                temp.write(self.path.read_bytes())
                        assert temp_path is not None
                        for event in events:
                            validate_preconditions(temp_path, event)
                            with temp_path.open("ab") as staged:
                                staged.write((serialize_event(event) + "\n").encode("utf-8"))
                    finally:
                        if temp_path is not None:
                            temp_path.unlink(missing_ok=True)
                fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
                try:
                    os.write(fd, data)
                    os.fsync(fd)
                finally:
                    os.close(fd)

    def recover(self, event: Event | None, *, expected_revision: str,
                change: str, source_commit: str, pr: int) -> None:
        """Durable, suffix-resumable append; never overwrite/truncate log bytes.

        Readers see either the old history or one complete recovery envelope.
        An incomplete UTF-8/JSON line cannot expose nested approvals. Ordinary
        writers refuse the pending journal until this exact append is completed.
        """
        from keepsail.core.recovery import validate_recovery, validate_recovery_header

        journal_path = self.path.with_name(".events.recovery-pending.json")
        identity = {"change": change, "source_commit": source_commit, "pr": pr}
        with self._lock, exclusive_file_lock(self._lock_path):
            current = self.path.read_bytes() if self.path.exists() else b""
            if journal_path.exists():
                journal = json.loads(journal_path.read_text(encoding="utf-8"))
                if journal.get("identity") != identity:
                    raise EmitPreconditionError("pending recovery belongs to another request")
                data = base64.b64decode(journal["append_base64"], validate=True)
                size = journal["prefix_length"]
                prefix, suffix = current[:size], current[size:]
                if (len(prefix) != size or sha256(prefix).hexdigest() != journal["prefix_sha256"]
                        or sha256(data).hexdigest() != journal["append_sha256"]
                        or not data.startswith(suffix)):
                    raise EmitPreconditionError("pending recovery prefix or append was modified")
                if expected_revision != journal["prefix_sha256"]:
                    raise EmitPreconditionError("pending recovery revision mismatch")
                from keepsail.core.events import parse_event_line

                if not data.endswith(b"\n") or data.count(b"\n") != 1:
                    raise EmitPreconditionError(
                        "pending recovery must contain one complete newline-terminated event")
                event = parse_event_line(data.decode("utf-8"))
            else:
                if sha256(current).hexdigest() != expected_revision:
                    raise EmitPreconditionError("historical recovery target revision changed")
                if event is None or event.type != "historical_change_recovered":
                    raise EmitPreconditionError("missing prepared recovery envelope")
                prefix = current
                suffix = b""
                data = (serialize_event(event) + "\n").encode("utf-8")
            validate_recovery_header(event)
            if (event.change_id != change or event.payload.get("source_commit") != source_commit
                    or event.payload.get("pr") != pr):
                raise EmitPreconditionError("pending recovery event identity mismatch")
            # Validate the original prefix even after an interrupted append. The
            # temporary file is not a state source and never replaces the log.
            staged_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=".events-",
                                                 suffix=".tmp", delete=False) as staged:
                    staged.write(prefix)
                    staged_path = Path(staged.name)
                validate_recovery(staged_path, event)
            finally:
                if staged_path is not None:
                    staged_path.unlink(missing_ok=True)
            if not journal_path.exists():
                journal = {"identity": identity, "prefix_length": len(prefix),
                           "prefix_sha256": sha256(prefix).hexdigest(),
                           "append_sha256": sha256(data).hexdigest(),
                           "append_base64": base64.b64encode(data).decode("ascii")}
                # Exclusive creation + fsync precedes every log byte. A damaged
                # journal fails closed and is preserved for investigation.
                with journal_path.open("xb") as pending:
                    pending.write(json.dumps(journal).encode())
                    pending.flush()
                    os.fsync(pending.fileno())
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            try:
                remaining = memoryview(data)[len(suffix):]
                while remaining:
                    written = os.write(fd, remaining)
                    if written <= 0:
                        raise OSError("recovery append made no progress")
                    remaining = remaining[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            journal_path.unlink()
