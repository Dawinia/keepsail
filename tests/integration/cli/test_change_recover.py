"""Historical merge recovery uses immutable Git evidence, never current authority."""

import json

import pytest
import yaml
from click.testing import CliRunner

from keepsail.cli import main
from keepsail.core.approval import make_code_subject
from keepsail.core.events import Actor, Event, serialize_event
from keepsail.core.reducer import derive_state
from keepsail.core.review_verdict import read_change_events
from keepsail.core.writer import EventWriter
from tests.integration.lifecycle.test_plan_authority import _evidence as _original_evidence
from tests.integration.lifecycle.test_plan_authority import _git, _recognition


def _evidence(root, **kwargs):
    path = _original_evidence(root, **kwargs)
    record = json.loads(path.read_text())
    record["provenance"]["change_id"] = "historical"
    path.write_text(json.dumps(record))
    return path


@pytest.fixture
def historical(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / ".harness").mkdir(parents=True)
    _recognition(root)
    (root / "plan.md").write_text("# Historical goal\nPublish answer.\n")
    (root / ".gitignore").write_text(".harness/events.jsonl\n.harness/state.yaml\n*.json\n")
    (root / ".harness/verification.yaml").write_text(yaml.safe_dump({
        "layers": {"baseline": {"enabled": False},
                   "framework_adapter": {"enabled": False},
                   "user_checks": {"enabled": False}},
    }))
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "historical policy")
    base = _git(root, "rev-parse", "HEAD")
    _git(root, "switch", "-qc", "delivery")
    runner = CliRunner()

    def cli(*args):
        result = runner.invoke(main, ["--workspace", str(root), "--json", *args])
        assert result.exit_code == 0, (result.output, result.exception)
        return result

    cli("change", "start", "historical")
    cli("plan", "ready", "historical", "--plan", "plan.md", "--commitment", "A=Publish answer")
    subject = derive_state(root / ".harness/events.jsonl")["historical"].pending_revision["subject"]
    cli("review", "import", "historical", "--evidence", str(_evidence(
        root, kind="plan", subject_id=subject["subject_id"], evidence_id="plan")))
    cli("implementation", "start", "historical")
    (root / "answer.txt").write_text("42\n")
    _git(root, "add", "answer.txt")
    _git(root, "commit", "-qm", "answer")
    state = derive_state(root / ".harness/events.jsonl")["historical"]
    approval = state.effective_approval["approval_id"]
    assessment = root / "assessment.json"
    assessment.write_text(json.dumps({"assessment": {
        "approval_id": approval, "affected_commitments": ["A"],
        "conclusion": "within_approval", "reasons": ["Publish approved answer"],
        "references": ["answer.txt"]}, "coverage": [{"path": "answer.txt"}]}))
    cli("implementation", "record", "historical", "--assessment", str(assessment))
    cli("done", "historical")
    state = derive_state(root / ".harness/events.jsonl")["historical"]
    cli("review", "import", "historical", "--evidence", str(_evidence(
        root, kind="code", subject_id=state.current_code_subject["subject_id"],
        evidence_id="code")))
    cli("attest", "write", "historical")
    # Add the attestation explicitly: *.json does not ignore *.jsonl.
    _git(root, "add", ".harness/attestations/historical.jsonl")
    _git(root, "commit", "-qm", "retain evidence")
    head = _git(root, "rev-parse", "HEAD")
    full = (root / ".harness/events.jsonl").read_bytes()
    # A squash merge is a single-parent object; product content must still match.
    _git(root, "switch", "-q", "main")
    _git(root, "merge", "--squash", "delivery")
    _git(root, "commit", "-qm", "squash publication (#1)")
    merged = _git(root, "rev-parse", "HEAD")
    fact = {"state": "MERGED", "mergedAt": "2026-10-22T09:30:11Z",
            "mergeCommit": {"oid": merged}, "headRefOid": head,
            "baseRefName": "main", "url": "https://github.com/owner/repo/pull/1",
            "body": "<!-- keepsail:metadata -->\nchange: historical\n<!-- /keepsail:metadata -->"}
    from keepsail.core import recovery
    monkeypatch.setattr(recovery, "github_merge_fact", lambda *args: fact)
    _git(root, "remote", "add", "origin", "https://github.com/owner/repo.git")
    prefix = b"\n".join(full.splitlines()[:2]) + b"\n"
    (root / ".harness/events.jsonl").write_bytes(prefix)
    return root, merged, base, full, prefix, fact


def recover(root, merged, *extra):
    return CliRunner().invoke(main, ["--workspace", str(root), "--json", "change",
        "recover", "historical", "--source-commit", merged, "--pr", "1", *extra])


def test_restore_prefix_and_historical_merge_idempotently(historical):
    from keepsail.core.emit_validation import find_ordering_violations

    root, merged, base, full, prefix, _ = historical
    unrelated = Event("other-id", "intent_declared", "other", "2026-10-26T00:00:00Z",
                      Actor("agent", "test"), "plain", payload={"description": "保留"})
    with (root / ".harness/events.jsonl").open("ab") as stream:
        stream.write((serialize_event(unrelated) + "\n").encode())
    before = (root / ".harness/events.jsonl").read_bytes()
    dry = recover(root, merged)
    assert dry.exit_code == 0, dry.output
    assert (root / ".harness/events.jsonl").read_bytes() == before
    revision = json.loads(dry.stdout)["data"]["expected_revision"]
    applied = recover(root, merged, "--apply", "--expected-revision", revision)
    assert applied.exit_code == 0, (applied.output, applied.exception)
    state = derive_state(root / ".harness/events.jsonl")["historical"]
    assert state.current_state == "ARCHIVED" and state.merge_commit_sha == merged
    assert state.current_code_subject["subject_id"] == make_code_subject(
        root, change_id="historical", approval_id=state.effective_approval["approval_id"],
        base=base, head=merged, knowledge_basis=None)["subject_id"]
    assert not find_ordering_violations(root / ".harness/events.jsonl", "historical")
    assert [e.type for e in read_change_events(root / ".harness/events.jsonl", "historical")][-1] \
        == "merged"
    after = (root / ".harness/events.jsonl").read_bytes()
    assert after.startswith(before)
    assert recover(root, merged, "--apply", "--expected-revision", revision).exit_code == 0
    assert (root / ".harness/events.jsonl").read_bytes() == after
    assert derive_state(root / ".harness/events.jsonl")["other"].description == "保留"
    assert prefix == before[:len(prefix)] and full


@pytest.mark.parametrize("bad", ["cas", "divergent", "unknown", "merge", "unmerged"])
def test_reject_without_appending(historical, bad):
    root, merged, _, _, _, fact = historical
    log = root / ".harness/events.jsonl"
    revision = json.loads(recover(root, merged).stdout)["data"]["expected_revision"]
    if bad in {"divergent", "unknown"}:
        rows = log.read_text().splitlines()
        item = json.loads(rows[-1])
        if bad == "divergent":
            item["payload"]["scope"] = {"files": ["tampered"]}
        else:
            item["type"] = "unknown-target-event"
        log.write_text(rows[0] + "\n" + json.dumps(item) + "\n")
    elif bad == "merge":
        fact["mergeCommit"]["oid"] = "0" * 40
    elif bad == "unmerged":
        fact["state"] = "OPEN"
    else:
        revision = "0" * 64
    before = log.read_bytes()
    result = recover(root, merged, "--apply", "--expected-revision", revision)
    assert result.exit_code != 0
    assert log.read_bytes() == before


def test_shared_writer_cannot_skip_recovery_validation(historical):
    from keepsail.core.writer import EmitPreconditionError

    root, _, _, _, _, _ = historical
    forged = Event("forged", "historical_change_recovered", "historical", "2026-10-27T00:00:00Z",
                   Actor("agent", "test"), "plain", payload={})
    before = (root / ".harness/events.jsonl").read_bytes()
    for skip in [False, True]:
        with pytest.raises(EmitPreconditionError):
            EventWriter(root / ".harness/events.jsonl").emit(forged, skip_validation=skip)
    assert (root / ".harness/events.jsonl").read_bytes() == before


def test_old_checkout_after_policy_activation_recovers_without_disabling_gate(historical):
    from tests.unit.core.test_knowledge import policy

    root, merged, _, full, _, _ = historical
    (root / ".harness/knowledge-recognition.yaml").write_text(yaml.safe_dump(policy()))
    _git(root, "add", ".harness/knowledge-recognition.yaml")
    _git(root, "commit", "-qm", "later knowledge activation")
    _git(root, "switch", "--detach", "delivery")
    log = root / ".harness/events.jsonl"
    log.write_bytes(full)
    current = CliRunner().invoke(main, ["--workspace", str(root), "on-merge",
                                       "--change", "historical", "--commit", merged])
    assert current.exit_code == 1
    assert "activated knowledge policy is missing" in current.output
    assert "change recover" in current.output
    assert "must be READY_TO_MERGE" not in current.output
    assert log.read_bytes() == full
    dry = recover(root, merged)
    assert dry.exit_code == 0, (dry.output, dry.exception)
    revision = json.loads(dry.stdout)["data"]["expected_revision"]
    assert recover(root, merged, "--apply", "--expected-revision", revision).exit_code == 0
    assert derive_state(log)["historical"].current_state == "ARCHIVED"
    # Recovery grants no current authoring right and never creates policy files.
    assert not (root / ".harness/knowledge-recognition.yaml").exists()
    result = CliRunner().invoke(main, ["--workspace", str(root), "implementation", "reopen",
                                      "historical", "--reason", "try to continue old work"])
    assert result.exit_code != 0


@pytest.mark.parametrize("mode", [
    "partial", "unicode", "complete", "prefix-corrupt", "journal-corrupt"])
def test_interrupted_append_resumes_exact_suffix(historical, monkeypatch, mode):
    import keepsail.core.writer as writer_module

    root, merged, _, _, _, _ = historical
    log = root / ".harness/events.jsonl"
    before = log.read_bytes()
    dry = recover(root, merged)
    assert dry.exit_code == 0, dry.output
    revision = json.loads(dry.stdout)["data"]["expected_revision"]
    write = writer_module.os.write
    calls = 0
    cutoff = 0
    if mode == "unicode":
        from dataclasses import asdict, replace

        from keepsail.core import recovery

        original = recovery.recovery_event
        monkeypatch.setattr(recovery, "recovery_event",
            lambda data: replace(original(data), actor=Actor("agent", "保留")))
        monkeypatch.setattr(writer_module, "serialize_event",
                            lambda event: json.dumps(asdict(event), ensure_ascii=False))

    def interrupted(fd, data):
        nonlocal calls, cutoff
        calls += 1
        if calls == 1:
            raw = bytes(data)
            cutoff = (raw.index("保".encode()) + 1 if mode == "unicode"
                      else raw.index(b"\\n") + 1)
            return write(fd, data[:cutoff])
        raise OSError("injected process interruption")

    monkeypatch.setattr(writer_module.os, "write", interrupted)
    failed = recover(root, merged, "--apply", "--expected-revision", revision)
    assert failed.exit_code != 0
    journal = root / ".harness/.events.recovery-pending.json"
    assert journal.exists() and log.read_bytes().startswith(before)
    if mode == "unicode":
        with pytest.raises(UnicodeDecodeError):
            derive_state(log)
    else:
        assert derive_state(log)["historical"].effective_approval is None
    blocked = Event("blocked", "intent_declared", "new-change", "2026-10-27T00:00:00Z",
                    Actor("agent", "test"), "plain")
    with pytest.raises(ValueError, match="pending"):
        EventWriter(log).emit(blocked)
    monkeypatch.setattr(writer_module.os, "write", write)
    if mode == "prefix-corrupt":
        raw = bytearray(log.read_bytes())
        raw[5] ^= 1
        log.write_bytes(raw)
    elif mode == "journal-corrupt":
        record = json.loads(journal.read_text())
        record["append_sha256"] = "0" * 64
        journal.write_text(json.dumps(record))
    elif mode == "complete":
        import base64
        record = json.loads(journal.read_text())
        full_append = base64.b64decode(record["append_base64"])
        with log.open("ab") as stream:
            stream.write(full_append[cutoff:])
    resume_before = log.read_bytes()
    resumed = recover(root, merged, "--apply", "--expected-revision", revision)
    if mode.endswith("corrupt"):
        assert resumed.exit_code != 0
        assert log.read_bytes() == resume_before and journal.exists()
    else:
        assert resumed.exit_code == 0, (resumed.output, resumed.exception)
        assert log.read_bytes().startswith(resume_before)
        assert derive_state(log)["historical"].current_state == "ARCHIVED"
        assert not journal.exists()


def test_offline_replay_and_attestation_share_historical_authority(historical, monkeypatch):
    from keepsail.core import recovery
    from keepsail.engineering.attestation import (
        check_attestation,
        derive_independence,
        events_from_stateful_attestation,
        extract_change_events,
    )

    root, merged, _, _, _, _ = historical
    data = json.loads(recover(root, merged).stdout)["data"]
    assert recover(root, merged, "--apply", "--expected-revision",
                   data["expected_revision"]).exit_code == 0
    log = root / ".harness/events.jsonl"
    att = root / ".harness/attestations/historical.jsonl"
    att.write_text("\n".join(extract_change_events(log, "historical")) + "\n")
    monkeypatch.setattr(recovery, "github_merge_fact",
                        lambda *args: pytest.fail("replay must be offline"))
    _git(root, "remote", "remove", "origin")
    assert derive_state(att)["historical"].current_state == "ARCHIVED"
    # This is a historical trace, not a new pre-merge attestation. The existing
    # merge gate deliberately still requires READY_TO_MERGE.
    assert check_attestation(att, "historical") == [
        "attestation historical: state is ARCHIVED, not READY_TO_MERGE"]
    events = events_from_stateful_attestation(root, "historical")
    assert events[-1].type == "merged"
    assert derive_independence(events)


def test_concurrent_apply_has_one_append_and_safe_retry(historical):
    from concurrent.futures import ThreadPoolExecutor

    from keepsail.core.recovery import prepare_recovery, recovery_event

    root, merged, _, _, _, _ = historical
    log = root / ".harness/events.jsonl"
    before = log.read_bytes()
    first = prepare_recovery(root, "historical", merged, 1)
    second = prepare_recovery(root, "historical", merged, 1)

    def apply(data):
        try:
            EventWriter(log).recover(recovery_event(data),
                expected_revision=data["expected_revision"], change="historical",
                source_commit=merged, pr=1)
            return "applied"
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(apply, [first, second]))
    assert results.count("applied") == 1
    assert any("revision changed" in result for result in results)
    assert log.read_bytes().startswith(before)
    assert prepare_recovery(root, "historical", merged, 1)["idempotent_replay"] is True


@pytest.mark.parametrize("tamper", ["issuer", "subject", "duplicate", "order", "knowledge"])
def test_tampered_immutable_attestation_cannot_authorize_recovery(historical, tamper):
    from keepsail.core.approval import evidence_digest

    root, _, _, _, _, fact = historical
    path = root / ".harness/attestations/historical.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if tamper == "issuer":
        imported = next(r for r in reversed(rows) if r["type"] == "review_evidence_imported")
        imported["payload"]["evidence"]["issuer"] = "unrecognized"
        imported["payload"]["evidence_digest"] = evidence_digest(imported["payload"]["evidence"])
        passed = next(r for r in reversed(rows) if r["type"] == "code_review_passed")
        passed["payload"]["evidence"] = imported["payload"]["evidence"]
    elif tamper == "subject":
        next(r for r in reversed(rows) if r["type"] == "code_review_passed")["payload"][
            "code_subject"]["subject_id"] = "code:" + "0" * 64
    elif tamper == "duplicate":
        rows[-1]["event_id"] = rows[0]["event_id"]
    elif tamper == "order":
        rows[0], rows[1] = rows[1], rows[0]
    else:
        rows[-1]["type"] = "knowledge_checkpointed"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _git(root, "add", str(path))
    _git(root, "commit", "-qm", "corrupt immutable fixture")
    changed = _git(root, "rev-parse", "HEAD")
    fact["mergeCommit"]["oid"] = changed
    fact["headRefOid"] = changed
    log = root / ".harness/events.jsonl"
    before = log.read_bytes()
    result = recover(root, changed)
    assert result.exit_code != 0, result.output
    assert log.read_bytes() == before


@pytest.mark.parametrize("kind", ["plan", "code", "assessment"])
def test_reject_retroactive_authority(historical, kind):
    root, _, _, _, _, fact = historical
    path = root / ".harness/attestations/historical.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if kind == "assessment":
        imported = next(r for r in rows if r["type"] == "implementation_recorded")
        milestone = "implementation_complete"
    else:
        imported = next(r for r in rows if r["type"] == "review_evidence_imported" and
                        r["payload"]["evidence"]["kind"] == kind)
        milestone = "plan_approved" if kind == "plan" else "code_review_passed"
    rows.remove(imported)
    index = next(i for i, r in enumerate(rows) if r["type"] == milestone)
    rows.insert(index + 1, imported)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _git(root, "add", str(path))
    _git(root, "commit", "-qm", "retroactive authority fixture")
    changed = _git(root, "rev-parse", "HEAD")
    fact["mergeCommit"]["oid"] = changed
    fact["headRefOid"] = changed
    log = root / ".harness/events.jsonl"
    before = log.read_bytes()
    result = recover(root, changed)
    assert result.exit_code != 0, result.output
    assert log.read_bytes() == before


@pytest.mark.parametrize("collision", ["source", "merged"])
def test_reject_envelope_id_collision_live_and_offline(historical, collision):
    from dataclasses import replace

    from keepsail.core.events import effective_event_lines
    from keepsail.core.recovery import prepare_recovery, recovery_event

    root, merged, _, _, _, _ = historical
    log = root / ".harness/events.jsonl"
    data = prepare_recovery(root, "historical", merged, 1)
    event = recovery_event(data)
    source = [json.loads(line) for line in event.payload["source_text"].splitlines()]
    event = replace(event, event_id=(source[-1]["event_id"] if collision == "source"
                    else event.payload["merged_event"]["event_id"]))
    before = log.read_bytes()
    with pytest.raises(ValueError, match="ID"):
        EventWriter(log).recover(event, expected_revision=data["expected_revision"],
                                 change="historical", source_commit=merged, pr=1)
    assert log.read_bytes() == before
    with pytest.raises(ValueError, match="ID"):
        list(effective_event_lines([*before.decode().splitlines(), serialize_event(event)]))


def test_native_integrity_and_disclosure_readers_share_recovery(historical):
    from keepsail.adapters.framework.superpowers import _seen_from_events
    from keepsail.engineering.value_report import _read_all_events

    root, merged, _, _, _, _ = historical
    data = json.loads(recover(root, merged).stdout)["data"]
    assert recover(root, merged, "--apply", "--expected-revision",
                   data["expected_revision"]).exit_code == 0
    result = CliRunner().invoke(main, ["--workspace", str(root), "state", "verify"])
    assert result.exit_code == 0, result.output
    assert _read_all_events(root / ".harness/events.jsonl")[-1].type == "merged"
    assert ("historical", "code_review_passed") in _seen_from_events(root)


@pytest.mark.parametrize("corruption", [
    "type", "newline", "extra-line", "timestamp", "unicode-separator", "unicode-tail",
    "duplicate-key", "journal-duplicate"])
def test_self_consistent_invalid_journal_is_rejected(historical, monkeypatch, corruption):
    import base64
    from hashlib import sha256

    import keepsail.core.writer as writer_module

    root, merged, _, _, _, _ = historical
    log = root / ".harness/events.jsonl"
    before = log.read_bytes()
    revision = json.loads(recover(root, merged).stdout)["data"]["expected_revision"]
    write = writer_module.os.write

    def interrupt_before_append(fd, data):
        raise OSError("injected before first append byte")

    monkeypatch.setattr(writer_module.os, "write", interrupt_before_append)
    assert recover(root, merged, "--apply", "--expected-revision", revision).exit_code != 0
    monkeypatch.setattr(writer_module.os, "write", write)
    journal = root / ".harness/.events.recovery-pending.json"
    if corruption == "journal-duplicate":
        journal.write_bytes(b'{"prefix_length":0,' + journal.read_bytes()[1:])
        retained_bytes = journal.read_bytes()
        result = recover(root, merged, "--apply", "--expected-revision", revision)
        assert result.exit_code != 0, result.output
        assert log.read_bytes() == before
        assert journal.read_bytes() == retained_bytes
        return
    retained = json.loads(journal.read_text())
    data = base64.b64decode(retained["append_base64"])
    if corruption in {"type", "timestamp"}:
        event = json.loads(data)
        if corruption == "type":
            event["type"] = "verification_passed"
        else:
            event["timestamp"] = 0
        data = (json.dumps(event) + "\n").encode()
    elif corruption == "unicode-separator":
        event = json.loads(data)
        event["actor"]["identifier"] = "split\u2028record"
        data = (json.dumps(event, ensure_ascii=False) + "\n").encode()
    elif corruption == "duplicate-key":
        data = b'{"event_id":"duplicate",' + data[1:]
    elif corruption == "unicode-tail":
        data = data[:-1] + "\u2028\n".encode()
    elif corruption == "newline":
        data = data[:-1]
    else:
        data += b"\n"
    retained["append_sha256"] = sha256(data).hexdigest()
    retained["append_base64"] = base64.b64encode(data).decode()
    journal.write_text(json.dumps(retained))
    retained_bytes = journal.read_bytes()
    result = recover(root, merged, "--apply", "--expected-revision", revision)
    assert result.exit_code != 0, result.output
    assert log.read_bytes() == before
    assert journal.read_bytes() == retained_bytes


@pytest.mark.parametrize("field", ["root-extra", "actor-extra", "nonfinite"])
def test_transport_schema_rejects_unrecognized_data(field):
    from dataclasses import asdict

    from keepsail.core.recovery import validate_recovery_record

    event = Event("transport", "historical_change_recovered", "historical",
                  "2026-10-27T00:00:00Z", Actor("agent", "test"), "plain")
    data = asdict(event)
    if field == "root-extra":
        data["unrecognized_authority"] = "owner"
    elif field == "actor-extra":
        data["actor"]["unrecognized_authority"] = "owner"
    else:
        data["framework_state"] = {"nonfinite": float("nan")}
    with pytest.raises(ValueError):
        validate_recovery_record((json.dumps(data) + "\n").encode())
