"""One byte snapshot of the ledger is expanded at most once per measured path (plan C5).

The count wraps ``effective_event_lines`` itself (every module reference to it),
grouped by the SHA-256 of the input bytes, so a new snapshot after an append is
counted separately.
"""

import collections
import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

from keepsail.core import events as events_module
from keepsail.core.emit_validation import (
    _change_event_types,
    _current_state,
    ledger_snapshot,
)
from keepsail.core.events import effective_event_lines
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state, derive_state_from_lines
from keepsail.core.review_verdict import read_change_events
from keepsail.core.writer import EventWriter
from tests.integration.lifecycle.policy_repo import (
    OWNER_PROCESS,
    PolicyRepo,
    v2_policy,
)

MODULES = ["keepsail.core.reducer", "keepsail.core.emit_validation",
           "keepsail.core.review_verdict", "keepsail.core.knowledge", "keepsail.cli.change",
           "keepsail.core.writer", "keepsail.core.transition_guard", "keepsail.core.events"]
# Module-level mutable containers before C5 (captured from the pre-change tree).
BASELINE_GLOBALS = {"keepsail.core.emit_validation": {"_HARD_PREREQ_EVENTS"},
                    "keepsail.core.review_verdict": {"_DISPOSITIONS", "_SEVERITIES",
                                                     "_SEVERITY_ORDER", "_STATUSES"}}


@pytest.fixture
def expansions(monkeypatch):
    counts = collections.Counter()
    original = events_module.effective_event_lines

    def counted(lines):
        materialized = list(lines)
        digest = hashlib.sha256("".join(materialized).encode("utf-8")).hexdigest()
        counts[digest] += 1
        return original(materialized)

    for name, module in list(sys.modules.items()):
        if name.startswith("keepsail") and module is not None:
            for attribute, value in list(vars(module).items()):
                if value is original:
                    monkeypatch.setattr(module, attribute, counted)
    return counts


@pytest.fixture(scope="module")
def delivered(tmp_path_factory):
    """A ledger with a completion transaction (no-review delivery) and plain events."""
    policy = v2_policy(plan=OWNER_PROCESS, code_review="off")
    repo = PolicyRepo(tmp_path_factory.mktemp("ledger") / "repo", policy)
    repo.approve("delivered", OWNER_PROCESS, policy)
    (repo.root / "feature.txt").write_bytes(b"feature\n")
    repo.commit("feature")
    repo.record("delivered", ["feature.txt"])
    repo.ok("done", "delivered")
    repo.approve("second", OWNER_PROCESS, policy)
    assert b"completion-transaction/v1" in events_path(repo.root).read_bytes()
    return repo


def test_change_resume_expands_each_snapshot_at_most_once(delivered, expansions):
    for args in (("change", "resume", "delivered"), ("--json", "change", "resume", "second")):
        expansions.clear()
        delivered.ok(*args)
        assert expansions and max(expansions.values()) == 1, (args, dict(expansions))


def test_one_strict_write_expands_each_snapshot_at_most_once(delivered, expansions,
                                                             monkeypatch):
    """Count inside each real strict write made by CLI commands (validation included)."""
    per_write = []
    original = EventWriter.emit_many

    def measured(self, events, *args, **kwargs):
        before = collections.Counter(expansions)
        try:
            return original(self, events, *args, **kwargs)
        finally:
            per_write.append((tuple(event.type for event in events),
                              collections.Counter(expansions) - before))

    monkeypatch.setattr(EventWriter, "emit_many", measured)
    (delivered.root / "second.txt").write_bytes(b"second\n")
    delivered.commit("second change")
    delivered.record("second", ["second.txt"])
    delivered.ok("done", "second")
    writes = [(types, counts) for types, counts in per_write if counts]
    assert any("implementation_recorded" in types for types, _ in writes), per_write
    assert any("implementation_complete" in types for types, _ in writes), per_write
    for types, counts in writes:
        assert max(counts.values()) == 1, (types, dict(counts))


def _ledgers(delivered, tmp_path):
    good = events_path(delivered.root).read_bytes()
    malformed = good + b'{"not": "an event"}\n' + b"not json at all\n"
    unknown = good + json.dumps({
        "event_id": "ev_unknown", "type": "l1_update_completed", "change_id": "second",
        "timestamp": "2099-01-01T00:00:00Z", "actor": {"type": "agent", "identifier": "x"},
        "framework": "plain", "framework_state": None, "payload": {}}).encode() + b"\n"
    for name, data in (("good", good), ("malformed", malformed), ("unknown", unknown)):
        path = tmp_path / name / ".harness/events.jsonl"
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
        yield path


def test_passing_lines_or_not_gives_identical_states_and_events(delivered, tmp_path):
    from keepsail.cli.change import _tail_events_for_change

    for path in _ledgers(delivered, tmp_path):
        _, lines = ledger_snapshot(path)
        assert derive_state(path) == derive_state_from_lines(list(lines), _effective=True)
        for change in ("delivered", "second", "absent"):
            assert read_change_events(path, change) == read_change_events(path, change,
                                                                          lines=lines)
            assert _current_state(path, change) == _current_state(path, change, lines=lines)
            assert _change_event_types(path, change) == _change_event_types(
                path, change, lines=lines)
            assert _tail_events_for_change(path, change, 5) == _tail_events_for_change(
                path, change, 5, lines=lines)
    missing = tmp_path / "missing/.harness/events.jsonl"
    assert ledger_snapshot(missing) == (b"", ())
    assert _current_state(missing, "x") is None and _change_event_types(missing, "x") == set()


def test_expansion_errors_are_unchanged(delivered, tmp_path):
    data = events_path(delivered.root).read_bytes()
    broken = tmp_path / ".harness/events.jsonl"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(data + b'{"schema_version": "completion-transaction/v1", "x": 1}\n')
    errors = []
    for call in (lambda: derive_state(broken), lambda: ledger_snapshot(broken),
                 lambda: read_change_events(broken, "second"),
                 lambda: list(effective_event_lines(
                     broken.read_bytes().decode().splitlines(keepends=True)))):
        with pytest.raises(Exception) as caught:
            call()
        errors.append((type(caught.value), str(caught.value)))
    assert len(set(errors)) == 1, errors


def test_ledger_prefix_hash_revision_and_snapshot_isolation(delivered, tmp_path):
    from keepsail.core.knowledge import load_ledger, policy_configuration, read_inputs

    root = delivered.root
    path = events_path(root)
    policy, _ = policy_configuration(root)
    content, lines = ledger_snapshot(path)
    direct = read_inputs(root)
    held = read_inputs(root, snapshot=(content, lines))
    assert load_ledger(path, policy) == (direct.ledger, direct.revision)
    assert (held.ledger, held.revision) == (direct.ledger, direct.revision)
    assert held.states == direct.states and held.effective_lines == direct.effective_lines
    # Appending after the read does not leak into the held snapshot.
    original = path.read_bytes()
    try:
        path.write_bytes(original + original.splitlines(keepends=True)[-1])
        again = read_inputs(root, snapshot=(content, lines))
        assert again.revision == held.revision and again.states == held.states
    finally:
        path.write_bytes(original)


def test_no_new_module_level_mutable_state():
    for name in MODULES:
        module = importlib.import_module(name)
        mutable = {attribute for attribute, value in vars(module).items()
                   if isinstance(value, (dict, list, set, bytearray))
                   and not attribute.startswith("__")}
        assert mutable == BASELINE_GLOBALS.get(name, set()), (name, mutable)


def test_resume_reads_one_snapshot(delivered, monkeypatch):
    reads = []
    original = Path.read_bytes

    def counting(self):
        if self.name == "events.jsonl":
            reads.append(self)
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    delivered.ok("change", "resume", "delivered")
    assert len(reads) == 1, reads
