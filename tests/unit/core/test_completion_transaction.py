import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from click.testing import CliRunner

from keepsail.cli import main
from keepsail.core.completion_transaction import decode_completion, encode_completion
from keepsail.core.events import Actor, Event, EventSchemaError, serialize_event
from keepsail.core.reducer import derive_state
from keepsail.core.writer import EmitPreconditionError, EventWriter


def pair():
    common = dict(change_id="delivery", timestamp="2026-11-11T00:00:00Z",
                  actor=Actor(type="human", identifier="fixture"), framework="plain")
    return [
        Event(event_id="one", type="implementation_complete",
              payload={"code_subject": {"subject_id": "code:subject"}}, **common),
        Event(event_id="two", type="code_review_not_required",
              payload={"subject_id": "code:subject", "trusted_base": "a" * 40,
                       "policy_digest": "b" * 64, "reason": "outside review scope"}, **common),
    ]


def test_transaction_round_trip_is_one_complete_line():
    events = pair()
    data = encode_completion(events)
    assert data.count(b"\n") == 1
    assert decode_completion(data) == events


def test_incomplete_and_modified_transactions_never_expand():
    data = encode_completion(pair())
    for offset in range(len(data)):
        with pytest.raises(EventSchemaError):
            decode_completion(data[:offset])
    raw = json.loads(data)
    raw["events"][1]["payload"]["reason"] = "modified"
    with pytest.raises(EventSchemaError, match="digest or encoding"):
        decode_completion((json.dumps(raw) + "\n").encode())
    with pytest.raises(EventSchemaError, match="duplicate"):
        decode_completion(b'{"schema_version":"completion-transaction/v1","schema_version":"x"}\n')


def test_wrong_order_mixed_change_and_subject_are_rejected():
    events = pair()
    for invalid in (list(reversed(events)), [events[0]],
                    [events[0], replace(events[1], change_id="another")],
                    [events[0], replace(events[1], event_id="one")],
                    [events[0], replace(events[1], payload={**events[1].payload,
                                                           "subject_id": "code:other"})]):
        with pytest.raises(EventSchemaError):
            encode_completion(invalid)


def _prefix() -> bytes:
    common = dict(change_id="delivery", timestamp="2026-11-11T00:00:00Z",
                  actor=Actor(type="human", identifier="fixture"), framework="plain")
    kinds = ("intent_declared", "plan_ready", "plan_approved", "implementation_started",
             "verification_passed")
    events = [Event(event_id=f"prefix-{i}", type=kind, **common)
              for i, kind in enumerate(kinds)]
    return "".join(serialize_event(event) + "\n" for event in events).encode("utf-8")


def test_torn_envelope_never_exposes_one_completion_event(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    prefix = _prefix()
    data = encode_completion(pair())
    for offset in range(len(data)):
        path.write_bytes(prefix + data[:offset])
        try:
            state = derive_state(path)["delivery"]
        except EventSchemaError:
            continue  # A complete JSON object without its newline fails closed.
        assert state.current_state == "IMPLEMENTATION_IN_PROGRESS"
        assert state.event_counts.get("implementation_complete", 0) == 0
        assert state.event_counts.get("code_review_not_required", 0) == 0
    path.write_bytes(prefix + data)
    state = derive_state(path)["delivery"]
    assert state.current_state == "READY_TO_MERGE"
    assert state.event_counts["implementation_complete"] == 1
    assert state.event_counts["code_review_not_required"] == 1
    path.write_bytes(prefix + data[:-1] + b"\r\n")
    with pytest.raises(EventSchemaError, match="encoding"):
        derive_state(path)


def test_failed_validation_does_not_create_a_completion_journal(tmp_path: Path, monkeypatch):
    path = tmp_path / ".harness/events.jsonl"
    path.parent.mkdir()
    prefix = _prefix()
    path.write_bytes(prefix)

    def validate(_path, event):
        if event.type == "code_review_not_required":
            raise EmitPreconditionError("second precondition failed")

    monkeypatch.setattr("keepsail.core.writer.validate_preconditions", validate)
    writer = EventWriter(path)
    with pytest.raises(EmitPreconditionError, match="second precondition"):
        writer.emit_many(pair())
    assert path.read_bytes() == prefix
    assert not writer._completion_journal.exists()
    with pytest.raises(EmitPreconditionError):
        writer.emit(pair()[1])


@pytest.mark.parametrize("boundary", ["before", "first", "middle", "without_newline", "complete"])
def test_process_exit_recovers_only_the_missing_suffix(tmp_path: Path, monkeypatch, boundary: str):
    path = tmp_path / ".harness/events.jsonl"
    path.parent.mkdir()
    prefix = _prefix()
    path.write_bytes(prefix)
    data = encode_completion(pair())
    cut = {"before": 0, "first": 1, "middle": len(data) // 2,
           "without_newline": len(data) - 1, "complete": len(data)}[boundary]
    encoded = json.dumps([json.loads(serialize_event(event)) for event in pair()])
    script = """\
import json, os, sys
from pathlib import Path
import keepsail.core.writer as writer
from keepsail.core.events import parse_event_line
writer.validate_preconditions = lambda path, event: None
events = [parse_event_line(json.dumps(item)) for item in json.loads(sys.argv[3])]
original = os.write
cut = int(sys.argv[2])
def abort(fd, data):
    if cut:
        original(fd, data[:cut])
    os._exit(47)
os.write = abort
writer.EventWriter(Path(sys.argv[1])).emit_many(events)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path), str(cut), encoded],
                            check=False, capture_output=True, env=os.environ.copy())
    assert result.returncode == 47, result.stderr.decode(errors="replace")
    writer = EventWriter(path)
    assert writer._completion_journal.exists()
    with pytest.raises(EmitPreconditionError, match="completion transaction pending"):
        writer.emit(Event(event_id="blocked", type="gate_bypassed", change_id="delivery",
                          timestamp="2026-11-11T00:00:00Z", actor=Actor("human", "fixture"),
                          framework="plain"), skip_validation=True)
    if cut < len(data) - 1:
        state = derive_state(path)["delivery"]
        assert state.current_state == "IMPLEMENTATION_IN_PROGRESS"
    elif cut == len(data) - 1:
        with pytest.raises(EventSchemaError):
            derive_state(path)
    else:
        assert derive_state(path)["delivery"].current_state == "READY_TO_MERGE"
    monkeypatch.setattr("keepsail.core.writer.validate_preconditions", lambda _path, _event: None)
    assert writer.recover_completion(change="delivery") is True
    assert path.read_bytes() == prefix + data
    assert derive_state(path)["delivery"].current_state == "READY_TO_MERGE"
    assert writer.recover_completion(change="delivery") is False
    assert path.read_bytes() == prefix + data


def test_short_writes_and_interrupted_recovery_are_resumable(tmp_path: Path, monkeypatch):
    path = tmp_path / ".harness/events.jsonl"
    path.parent.mkdir()
    prefix, data = _prefix(), encode_completion(pair())
    path.write_bytes(prefix)
    monkeypatch.setattr("keepsail.core.writer.validate_preconditions", lambda _path, _event: None)
    writer = EventWriter(path)
    actual_write = os.write

    def fail_after_short_write():
        calls = 0

        def write(fd, remaining):
            nonlocal calls
            calls += 1
            if calls == 1:
                return actual_write(fd, remaining[:17])
            raise OSError("injected interruption")

        return write

    with monkeypatch.context() as context:
        context.setattr("keepsail.core.writer.os.write", fail_after_short_write())
        with pytest.raises(OSError, match="injected interruption"):
            writer.emit_many(pair())
    assert path.read_bytes() == prefix + data[:17]
    with pytest.raises(EmitPreconditionError, match="another Change"):
        writer.recover_completion(change="wrong")
    with monkeypatch.context() as context:
        context.setattr("keepsail.core.writer.os.write", fail_after_short_write())
        with pytest.raises(OSError, match="injected interruption"):
            writer.recover_completion(change="delivery")
    assert path.read_bytes() == prefix + data[:34]
    assert derive_state(path)["delivery"].current_state == "IMPLEMENTATION_IN_PROGRESS"
    assert writer.recover_completion(change="delivery") is True
    assert path.read_bytes() == prefix + data


def test_process_exit_after_log_fsync_does_not_duplicate_pair(tmp_path: Path, monkeypatch):
    path = tmp_path / ".harness/events.jsonl"
    path.parent.mkdir()
    prefix, data = _prefix(), encode_completion(pair())
    path.write_bytes(prefix)
    encoded = json.dumps([json.loads(serialize_event(event)) for event in pair()])
    script = """\
import json, os, sys
from pathlib import Path
import keepsail.core.writer as writer
from keepsail.core.events import parse_event_line
writer.validate_preconditions = lambda path, event: None
events = [parse_event_line(json.dumps(item)) for item in json.loads(sys.argv[2])]
original = os.fsync
target = Path(sys.argv[1])
def abort_after_log_sync(fd):
    original(fd)
    if os.path.samestat(os.fstat(fd), os.stat(target)):
        os._exit(48)
os.fsync = abort_after_log_sync
writer.EventWriter(target).emit_many(events)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path), encoded],
                            check=False, capture_output=True)
    assert result.returncode == 48, result.stderr.decode(errors="replace")
    assert path.read_bytes() == prefix + data
    writer = EventWriter(path)
    assert writer._completion_journal.exists()
    monkeypatch.setattr("keepsail.core.writer.validate_preconditions", lambda _path, _event: None)
    assert writer.recover_completion(change="delivery") is True
    assert path.read_bytes() == prefix + data


def test_exit_while_preparing_journal_never_starts_append(tmp_path: Path):
    path = tmp_path / ".harness/events.jsonl"
    path.parent.mkdir()
    prefix = _prefix()
    path.write_bytes(prefix)
    encoded = json.dumps([json.loads(serialize_event(event)) for event in pair()])
    script = """\
import json, os, stat, sys
from pathlib import Path
import keepsail.core.writer as writer
from keepsail.core.events import parse_event_line
writer.validate_preconditions = lambda path, event: None
events = [parse_event_line(json.dumps(item)) for item in json.loads(sys.argv[2])]
target = Path(sys.argv[1])
original = os.fsync
def abort_preparing(fd):
    current = os.fstat(fd)
    if stat.S_ISREG(current.st_mode) and not os.path.samestat(current, os.stat(target)):
        os._exit(49)
    original(fd)
os.fsync = abort_preparing
writer.EventWriter(target).emit_many(events)
"""
    result = subprocess.run([sys.executable, "-c", script, str(path), encoded],
                            check=False, capture_output=True)
    assert result.returncode == 49, result.stderr.decode(errors="replace")
    writer = EventWriter(path)
    assert path.read_bytes() == prefix
    assert not writer._completion_journal.exists()
    writer.emit(Event(event_id="later", type="gate_bypassed", change_id="delivery",
                      timestamp="2026-11-11T00:00:00Z", actor=Actor("human", "fixture"),
                      framework="plain"), skip_validation=True)
    assert path.read_bytes().startswith(prefix)


def test_recovery_command_resumes_the_named_change(tmp_path: Path, monkeypatch):
    path = tmp_path / ".harness/events.jsonl"
    path.parent.mkdir()
    prefix, data = _prefix(), encode_completion(pair())
    path.write_bytes(prefix)
    monkeypatch.setattr("keepsail.core.writer.validate_preconditions", lambda _path, _event: None)
    writer = EventWriter(path)
    actual_write = os.write
    calls = 0

    def interrupt(fd, remaining):
        nonlocal calls
        calls += 1
        if calls == 1:
            return actual_write(fd, remaining[:10])
        raise OSError("interrupted")

    with monkeypatch.context() as context:
        context.setattr("keepsail.core.writer.os.write", interrupt)
        with pytest.raises(OSError):
            writer.emit_many(pair())
    result = CliRunner().invoke(main, ["--workspace", str(tmp_path), "--json", "change",
                                       "recover-completion", "delivery"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["recovered"] is True
    assert path.read_bytes() == prefix + data
