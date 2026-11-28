import json
import subprocess
from copy import deepcopy
from types import SimpleNamespace

import pytest
import yaml

from keepsail.core.approval import (
    ApprovalError,
    canonical_json,
    digest_record,
    evidence_digest,
    recognition_policy_digest,
)
from keepsail.core.attestation_format import _validate_evidence_chain
from keepsail.core.attestation_v3 import make_v3, parse_v3_line, validate_v3
from keepsail.core.risk_boundary import compare_risk_boundary


def v3():
    snapshot = {"schema_version": "attestation/v2", "change_id": "delivery"}
    snapshot["digest"] = digest_record(snapshot)
    return make_v3(change_id="delivery", trusted_base="a" * 40, policy_digest="b" * 64,
                   recognition_basis={"plan": {"mode": "current", "policy_digest": "b" * 64},
                                      "code": {"mode": "current", "policy_digest": "b" * 64}},
                   authorization=None, snapshot=snapshot)


@pytest.mark.parametrize("failed_subject,blocked", [("code:current", True), ("code:other", False)])
def test_no_review_replay_checks_retained_failure_for_same_subject(
    tmp_path, monkeypatch, failed_subject, blocked,
):
    from keepsail.core import attestation_replay, no_review
    from keepsail.core.events import Actor, Event

    base = "a" * 40
    code = {"subject_id": "code:current", "base": base, "head": "b" * 40, "manifest": []}
    approval = {"approval_id": "approval:one", "evidence_id": "missing"}
    state = SimpleNamespace(
        effective_approval=approval, evidence_references=[], current_code_subject=code,
        coverage_manifest=[],
        current_verification={"subject_id": "code:current", "outcome": "passed"},
    )
    actor = Actor(type="agent", identifier="test")
    events = [
        Event(event_id="failed", type="code_review_failed", change_id="delivery", timestamp="",
              actor=actor, framework="plain",
              payload={"code_subject": {"subject_id": failed_subject}}),
        Event(event_id="no-review", type="code_review_not_required", change_id="delivery",
              timestamp="", actor=actor, framework="plain",
              payload={"trusted_base": base, "subject_id": "code:current"}),
    ]
    monkeypatch.setattr(attestation_replay, "validate_approval", lambda value, **kwargs: value)
    monkeypatch.setattr(attestation_replay, "has_unresolved_candidate", lambda value: False)
    monkeypatch.setattr(attestation_replay, "validate_code_subject", lambda value, **kwargs: value)
    monkeypatch.setattr(attestation_replay, "make_code_subject", lambda *args, **kwargs: code)
    monkeypatch.setattr(attestation_replay, "events_from_stateful_attestation",
                        lambda *args, **kwargs: events)
    monkeypatch.setattr(attestation_replay, "missing_coverage", lambda *args: [])
    monkeypatch.setattr(attestation_replay, "_review_reference_blockers", lambda *args: [])
    monkeypatch.setattr(no_review, "verify_no_review_binding", lambda *args: None)
    blockers = attestation_replay._new_contract_blockers(
        tmp_path, state, "delivery", [], recognition=SimpleNamespace(policy_digest=None),
        base=base, head="b" * 40, code_review_required=False,
    )
    assert any("retained evidence contains a code review failure" in message
               for message in blockers) is blocked


@pytest.mark.parametrize("case", ["other-subject", "same-subject", "missing", "tampered"])
def test_v3_no_review_checks_retained_historical_failures(case):
    from keepsail.core.attestation_format import _validate_historical_review_failures

    original = {
        "event_id": "failure", "type": "code_review_failed", "change_id": "delivery",
        "timestamp": "2026-01-01T00:00:00Z", "actor": {"type": "agent", "identifier": "reviewer"},
        "framework": "plain", "payload": {"code_subject": {"subject_id": (
            "code:current" if case == "same-subject" else "code:other")}},
    }
    row = {"source_event_id": "failure", "type": "code_review_failed",
           "source_event_digest": digest_record(original), "source_event": original}
    if case == "missing":
        del row["source_event"]
    elif case == "tampered":
        row["source_event_digest"] = "x" * 64
    if case == "other-subject":
        _validate_historical_review_failures([row], "delivery", "code:current")
    else:
        with pytest.raises(ApprovalError):
            _validate_historical_review_failures([row], "delivery", "code:current")


@pytest.mark.parametrize("case", ["valid", "legacy-signed", "mismatch", "missing",
                                  "undeclared", "recovery-basis"])
def test_v1_risk_boundary_delivery_needs_the_matching_owner_acceptance(
    tmp_path, monkeypatch, case,
):
    """Exercise real Git objects; lifecycle replay is tested separately."""
    from keepsail.core import attestation_v3_verify as replay
    from keepsail.core import risk_boundary

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    recognition = {"version": "review-recognition/v1", "enabled": True, "process": {
        "id": "old", "version": "v1", "kinds": ["plan", "code"],
        "issuers": ["owner"], "evidence_forms": ["json"]}}
    recognition["process"]["policy_digest"] = recognition_policy_digest(recognition)
    harness = tmp_path / ".harness"
    harness.mkdir()
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(recognition), encoding="utf-8")
    checks = "checks:\n- id: fixture\n  command: [python, -c, pass]\n  must_pass: true\n"
    (harness / "verification.yaml").write_text(checks, encoding="utf-8")
    (tmp_path / "plan.md").write_text("# Replace the review process\n", encoding="utf-8")
    git("init", "-q", "-b", "main")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "fixture")
    git("add", ".")
    git("commit", "-qm", "trusted base")
    base = git("rev-parse", "HEAD")
    git("switch", "-qc", "candidate")
    changed = deepcopy(recognition)
    changed["process"]["id"] = "new"
    changed["process"]["policy_digest"] = recognition_policy_digest(changed)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(changed), encoding="utf-8")
    evidence = harness / "attestations/v3/delivery.jsonl"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "candidate replaces the process")
    head = git("rev-parse", "HEAD")
    policy_digest = recognition["process"]["policy_digest"]
    boundary = compare_risk_boundary(tmp_path, base=base, head=head)
    assert boundary is not None and boundary.changed
    assert {row["path"] for row in boundary.differences} >= {
        "/processes_by_kind/plan/id", "/processes_by_kind/code/id"}
    acceptance = boundary.acceptance(change_id="delivery", plan_subject_id="plan:test")
    authorization = {"acceptance": acceptance, "event_id": "01ACCEPT",
                     "actor": {"type": "human", "identifier": "owner"},
                     "ts": "2026-11-28T00:00:00Z"}
    bases = {"plan": {"mode": "current"}, "code": {"mode": "current"}}
    if case == "legacy-signed":
        authorization = {"version": "policy-authorization/v1", "kind": "transition"}
    elif case == "mismatch":
        authorization["acceptance"] = {**acceptance, "target_checks_digest": "0" * 64}
    elif case == "missing":
        authorization = None
    elif case == "recovery-basis":
        bases["plan"] = {"mode": "recovery"}
    record = {"trusted_base": base, "policy_digest": policy_digest, "change_id": "delivery",
              "snapshot": {}, "authorization": authorization, "recognition_basis": bases}
    commitments = ([] if case == "undeclared"
                   else [{"id": "RISK-BOUNDARY", "text": "Replace the review process"}])
    approval = {"subject_id": "plan:test", "subject": {"commitments": commitments}}
    code = {"subject_id": "code:test", "manifest": [{"path": ".harness/review-recognition.yaml"}]}
    state = SimpleNamespace(current_verification={}, coverage_manifest=code["manifest"])
    monkeypatch.setattr(risk_boundary, "validate_plan_subject", lambda value, **kwargs: value)
    monkeypatch.setattr(replay, "validate_v3", lambda value: value)
    monkeypatch.setattr(replay, "validate_approval", lambda *args, **kwargs: approval)
    monkeypatch.setattr(replay, "validate_code_subject", lambda *args, **kwargs: code)
    monkeypatch.setattr(replay, "parse_v3_line", lambda raw: record)
    monkeypatch.setattr(replay, "expand_attestation", lambda *args, **kwargs: [])
    monkeypatch.setattr(replay, "wrap_derived_completion", lambda lines: lines)
    monkeypatch.setattr(replay, "check_recognized_attestation", lambda *args, **kwargs: [])
    monkeypatch.setattr(replay, "derive_state", lambda path: {"delivery": state})
    monkeypatch.setattr(replay, "_new_contract_blockers", lambda *args, **kwargs: [])
    monkeypatch.setattr(replay, "_knowledge_attestation", lambda *args, **kwargs: None)
    monkeypatch.setattr(replay, "events_from_stateful_attestation", lambda *args, **kwargs: [])
    monkeypatch.setattr(replay, "gate_bypass_disclosure", lambda events: {"undisclosed": False})
    monkeypatch.setattr(replay, "derive_independence", lambda events: {
        kind: {"skipped": False, "override": False} for kind in ("plan_review", "code_review")})
    monkeypatch.setattr(replay, "verify_check_evidence", lambda *args, **kwargs: {})

    if case == "valid":
        # Identity keywords from older workflows are accepted and ignored.
        result = replay.verify_v3_transition(tmp_path, record, base=base, head=head,
            repository_id="owner/project", target_ref="refs/heads/main")
        assert result["target_policy_digest"] == changed["process"]["policy_digest"]
        assert result["code_review_required"] is True
        assert result["risk_boundary"]["actor"] == {"type": "human", "identifier": "owner"}
        assert result["risk_boundary"]["obligation_changes"] == boundary.differences
    else:
        expected = {"legacy-signed": "no longer accepted",
                    "mismatch": "does not match the recomputed change",
                    "missing": "needs the owner's recorded policy acceptance",
                    "undeclared": "RISK-BOUNDARY",
                    "recovery-basis": "historical attestations"}
        with pytest.raises(ApprovalError, match=expected[case]):
            replay.verify_v3_transition(tmp_path, record, base=base, head=head)


def test_envelope_round_trips_canonical_single_line():
    record = v3()
    data = (canonical_json(record) + "\n").encode()
    assert parse_v3_line(data) == record
    for partial in (data[:-1], data[:100], data + b"\n"):
        with pytest.raises(ApprovalError):
            parse_v3_line(partial)
    with pytest.raises(ApprovalError, match="duplicate"):
        parse_v3_line(b'{"schema_version":"attestation/v3","schema_version":"x"}\n')


def test_bases_and_snapshot_are_bound_to_the_envelope():
    record = v3()
    for mutate in (lambda x: x["snapshot"].update(change_id="other"),
                   lambda x: x["snapshot"].update(digest="0" * 64),
                   lambda x: x["recognition_basis"]["plan"].update(policy_digest="c" * 64),
                   lambda x: x["recognition_basis"]["code"].update(mode="continued_plan")):
        changed = deepcopy(record)
        mutate(changed)
        changed["digest"] = digest_record({k: v for k, v in changed.items() if k != "digest"})
        with pytest.raises(ApprovalError):
            validate_v3(changed)


def test_historical_recovery_basis_remains_structurally_parseable():
    record = v3()
    authorization = {"version": "policy-authorization/v1", "signature": "fixture"}
    auth_digest = digest_record(authorization)
    recovery_digest = digest_record({"version": "recovery-recognition/v1",
                                     "base_policy_digest": record["policy_digest"],
                                     "authorization_digest": auth_digest})
    record["authorization"] = authorization
    record["recognition_basis"]["plan"] = {"mode": "recovery", "policy_digest": recovery_digest,
                                             "authorization_digest": auth_digest}
    record["digest"] = digest_record({k: v for k, v in record.items() if k != "digest"})
    assert validate_v3(record) == record
    missing = deepcopy(record)
    missing["authorization"] = None
    missing["digest"] = digest_record({k: v for k, v in missing.items() if k != "digest"})
    with pytest.raises(ApprovalError, match="requires its signed authorization"):
        validate_v3(missing)
    record["authorization"]["signature"] = "different"
    record["digest"] = digest_record({k: v for k, v in record.items() if k != "digest"})
    with pytest.raises(ApprovalError, match="recovery basis"):
        validate_v3(record)
    with pytest.raises(ApprovalError, match="not canonical"):
        parse_v3_line((json.dumps(v3()) + "\n").encode())


def test_new_deliveries_accept_only_current_recognition_bases():
    from keepsail.core.attestation_v3_verify import _require_current_bases

    _require_current_bases({"recognition_basis": {"plan": {"mode": "current"}, "code": None}})
    for kind, mode in (("plan", "recovery"), ("plan", "continued_plan"), ("code", "recovery")):
        record = {"recognition_basis": {"plan": {"mode": "current"},
                                        "code": {"mode": "current"}}}
        record["recognition_basis"][kind] = {"mode": mode}
        with pytest.raises(ApprovalError, match="historical attestations"):
            _require_current_bases(record)


def test_v3_replays_retained_evidence_supersession_and_id_consistency():
    first = {"version": "review-evidence/v1", "evidence_id": "first", "kind": "plan",
             "subject_id": "plan:one", "decision": "reject", "issuer": "owner",
             "process": {"id": "review", "version": "v1"}, "form": "json",
             "original_evidence": {"decision": "reject"}, "provenance": {}}
    second = {**first, "evidence_id": "second", "decision": "approve", "supersedes": "first"}

    def row(evidence):
        return {"type": "review_evidence_imported", "payload": {
            "evidence": evidence, "evidence_digest": evidence_digest(evidence),
            "subject_id": evidence["subject_id"]}}

    _validate_evidence_chain([row(first), row(second)], "delivery")
    with pytest.raises(ApprovalError, match="supersedes"):
        _validate_evidence_chain([row(second)], "delivery")
    with pytest.raises(ApprovalError, match="reused"):
        _validate_evidence_chain([row(first), row({**first, "decision": "approve"})], "delivery")
