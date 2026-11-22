"""A derived v2 lifecycle snapshot, with explicit current-subject references.

Native history is not rewritten. The exported rows use new deterministic IDs
and retain their source event identities/digests; they do not claim original
event bytes. Historical obligations are reduced only by reviewed continuation.
"""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    digest_record,
    evidence_digest,
    has_unresolved_candidate,
    validate_approval,
    validate_code_subject,
    validate_evidence,
    validate_evidence_reuse,
    validate_retained_lineage,
)
from keepsail.core.events import Event, parse_event_line, serialize_event

SCHEMA = "attestation/v2"
REPRESENTATION = "derived-not-original-event-bytes"


def _require(value: object, message: str) -> None:
    if not value:
        raise ApprovalError(message)


def _validate_evidence_chain(rows: list[Any], change: str) -> None:
    prior: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("type") != "review_evidence_imported":
            continue
        payload = row.get("payload")
        _require(isinstance(payload, dict), "invalid retained review evidence")
        assert isinstance(payload, dict)
        evidence = validate_evidence(payload.get("evidence"), change_id=change)
        _require(payload.get("subject_id") == evidence["subject_id"]
                 and payload.get("evidence_digest") == evidence_digest(evidence),
                 "retained review evidence binding does not match")
        outcome = validate_evidence_reuse(evidence, prior, subject_id=evidence["subject_id"])
        if outcome == "new":
            prior.append(evidence)


def _validate_historical_review_failures(
    index: list[dict[str, Any]], change: str, subject_id: str,
) -> None:
    for row in index:
        if row["type"] != "code_review_failed":
            continue
        source = row.get("source_event")
        _require(isinstance(source, dict) and digest_record(source) == row["source_event_digest"],
                 "historical code review failure requires its original event")
        event = parse_event_line(json.dumps(source))
        _require(event.event_id == row["source_event_id"] and event.type == row["type"]
                 and event.change_id == change, "historical review event identity mismatch")
        code = event.payload.get("code_subject")
        _require(isinstance(code, dict) and isinstance(code.get("subject_id"), str),
                 "historical review failure lacks a code subject")
        assert isinstance(code, dict)
        _require(code["subject_id"] != subject_id,
                 "a rejected code subject cannot bypass its code review")


def make_attestation(change: str, inputs: Any, checkpoint: dict[str, Any],
                     lineage: list[dict[str, Any]], *, for_v3: bool = False) -> dict[str, Any]:
    state = inputs.states[change]
    approval = validate_approval(state.effective_approval, change_id=change)
    _require(not has_unresolved_candidate(state), "cannot compact an unresolved plan revision")
    code = state.current_code_subject
    evidence = {e["evidence_id"]: e for e in state.evidence_references}
    originals = [parse_event_line(line) for line in inputs.effective_lines]
    originals = [event for event in originals if event.change_id == change]
    rows: list[dict[str, Any]] = []

    def last(kind: str, predicate: Any = None) -> Event:
        matches = [e for e in originals if e.type == kind and (predicate is None or predicate(e))]
        _require(matches, f"snapshot lacks native {kind}")
        return matches[-1]

    def add(kind: str, payload: dict[str, Any], source: Event) -> None:
        rows.append({
            "type": kind, "payload": payload,
            "timestamp": max(source.timestamp, rows[-1]["timestamp"]) if rows else source.timestamp,
            "source_timestamp": source.timestamp,
            "actor": {"type": source.actor.type, "identifier": source.actor.identifier},
            "framework": source.framework, "source_event_id": source.event_id,
            "source_event_digest": digest_record(json.loads(serialize_event(source))),
        })

    def add_evidence_history(target: dict[str, Any], source: Event) -> None:
        candidates = [source]
        if for_v3:
            candidates = [event for event in originals[:originals.index(source) + 1]
                          if event.type == "review_evidence_imported"
                          and isinstance(event.payload.get("evidence"), dict)
                          and event.payload["evidence"].get("subject_id") == target["subject_id"]]
        for event in candidates:
            retained = event.payload["evidence"]
            if for_v3:
                _require(event.payload.get("evidence_digest") == evidence_digest(retained),
                         "retained review evidence digest does not match")
            add("review_evidence_imported", {"evidence": retained,
                                            "evidence_digest": evidence_digest(retained),
                                            "subject_id": retained["subject_id"]}, event)

    approved = last("plan_approved", lambda e: e.payload.get("approval", {}).get("approval_id")
                    == approval["approval_id"])
    add("intent_declared", {"description": state.description}, last("intent_declared"))
    add("plan_ready", {"scope": state.scope, "tier_hint": state.tier,
                       "plan_artifacts": state.plan_artifacts,
                       "plan_subject_ref": "current"}, approved)
    plan_evidence = evidence[approval["evidence_id"]]
    source = last("review_evidence_imported", lambda e: e.payload.get("evidence", {}).get(
        "evidence_id") == plan_evidence["evidence_id"])
    add_evidence_history(plan_evidence, source)
    add("plan_approved", {"approval_ref": "current",
                          "review_reference_version": "review-reference/v2",
                          "evidence_id": approval["evidence_id"],
                          "evidence_digest": approval["evidence_digest"]}, approved)
    if state.current_state not in {"PLAN_APPROVED", "AWAITING_PLAN_REVIEW", "PLAN_REJECTED"}:
        started = last("implementation_started")
        add("implementation_started", {}, started)
        assessments = [e for e in originals if e.type == "implementation_recorded"
                       and e.payload.get("assessment", {}).get("approval_id")
                       == approval["approval_id"]]
        for i, event in enumerate(assessments):
            add("implementation_recorded", {
                "assessment": event.payload["assessment"],
                "coverage": state.coverage_manifest if i == len(assessments) - 1 else [],
            }, event)
    verification = state.current_verification
    if verification is not None:
        _require(code is not None, "verification without a current code subject")
        kind = ("verification_passed" if verification["outcome"] == "passed"
                else "verification_failed")
        value = deepcopy(verification)
        value.pop("code_subject", None)
        value["code_subject_ref"] = "current"
        add(kind, {"verification": value}, last(kind, lambda e: e.payload.get("verification", {})
                                               .get("subject_id") == code["subject_id"]))
    if code is not None and state.current_state in {
        "AWAITING_CODE_REVIEW", "CODE_REVIEW_REJECTED", "READY_TO_MERGE", "ARCHIVED",
    }:
        add("implementation_complete", {"code_subject_ref": "current"}, last(
            "implementation_complete", lambda e: e.payload.get("code_subject", {}).get("subject_id")
            == code["subject_id"]))
        review = next((e for e in reversed(originals) if (
            (e.type in {"code_review_passed", "code_review_failed"}
             and e.payload.get("code_subject", {}).get("subject_id") == code["subject_id"])
            or (e.type == "code_review_not_required"
                and e.payload.get("subject_id") == code["subject_id"])
        )), None)
        if review is not None and review.type == "code_review_not_required":
            _require(for_v3, "no-review completion requires a v3 attestation")
            add(review.type, review.payload, review)
        elif review is not None:
            conclusion = evidence[review.payload["evidence_id"]]
            source = last("review_evidence_imported", lambda e: e.payload.get("evidence", {}).get(
                "evidence_id") == conclusion["evidence_id"])
            add_evidence_history(conclusion, source)
            add(review.type, {"code_subject_ref": "current",
                              "review_reference_version": "review-reference/v2",
                              "evidence_id": conclusion["evidence_id"],
                              "evidence_digest": digest_record(conclusion)}, review)
    for event in originals:
        if event.type in {"gate_bypassed", "gate_bypass_disclosed", "review_budget_exceeded"}:
            add(event.type, event.payload, event)
    if state.current_state == "ARCHIVED":
        add("merged", last("merged").payload, last("merged"))
    record = {
        "schema_version": SCHEMA, "representation": REPRESENTATION, "change_id": change,
        "approval": approval, "code_subject": code, "authorization_lineage": lineage,
        "lifecycle": rows, "knowledge_checkpoint": checkpoint,
        "expected_state": state.current_state,
        "historical_lifecycle_index": [
            {"source_event_id": e.event_id, "type": e.type,
             "source_event_digest": digest_record(json.loads(serialize_event(e))),
             **({"source_event": json.loads(serialize_event(e))}
                if for_v3 and e.type == "code_review_failed" else {})}
            for e in originals if e.type not in {"knowledge_checkpointed"}
            and not e.type.startswith("knowledge_")
        ],
    }
    result = {**record, "digest": digest_record(record)}
    # Round-trip validation includes the unchanged transition table and subject
    # predicates, before a writer can publish the derived artifact.
    expanded = expand_attestation(result, for_v3=for_v3)
    from keepsail.core.reducer import derive_state_from_lines
    restored = derive_state_from_lines(expanded, _effective=True)[change]
    _require(restored.current_state == state.current_state
             and restored.effective_approval == approval
             and restored.current_code_subject == code
             and restored.coverage_manifest == state.coverage_manifest,
             "compact lifecycle does not restore current authority and coverage")
    return result


def inactive_knowledge_checkpoint() -> dict[str, str]:
    body = {"schema_version": "knowledge-inactive/v1"}
    return {**body, "digest": digest_record(body)}


def expand_attestation(raw: object, *, for_v3: bool = False) -> list[str]:
    """Reject malformed external records through the domain validation boundary."""
    if not isinstance(raw, dict):
        raise ApprovalError("compact attestation must be an object")
    try:
        return _expand_attestation(raw, for_v3=for_v3)
    except ApprovalError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
        raise ApprovalError("invalid compact attestation structure") from exc


def _expand_attestation(raw: dict[str, Any], *, for_v3: bool = False) -> list[str]:
    _require(set(raw) == {"schema_version", "representation", "change_id", "approval",
                          "code_subject",
                          "authorization_lineage", "lifecycle", "knowledge_checkpoint",
                          "expected_state", "historical_lifecycle_index", "digest"}
             and raw["schema_version"] == SCHEMA and raw["representation"] == REPRESENTATION,
             "invalid compact attestation format")
    _require(raw["digest"] == digest_record({k: v for k, v in raw.items() if k != "digest"}),
             "compact attestation digest mismatch")
    _require(isinstance(raw["change_id"], str) and raw["change_id"]
             and isinstance(raw["expected_state"], str), "invalid compact attestation identity")
    _require(isinstance(raw["lifecycle"], list) and raw["lifecycle"],
             "compact attestation needs a non-empty lifecycle")
    _require(isinstance(raw["knowledge_checkpoint"], dict)
             and isinstance(raw["knowledge_checkpoint"].get("digest"), str),
             "invalid compact knowledge checkpoint")
    inactive_knowledge = raw["knowledge_checkpoint"] == inactive_knowledge_checkpoint()
    _require(for_v3 or not inactive_knowledge,
             "inactive knowledge sentinel is only permitted inside v3")
    index_keys = {"source_event_id", "type", "source_event_digest"}
    _require(isinstance(raw["historical_lifecycle_index"], list)
             and all(isinstance(row, dict)
                 and (set(row) == index_keys or (for_v3 and row.get("type") == "code_review_failed"
                                                and set(row) == index_keys | {"source_event"}))
                 and all(isinstance(row[key], str) and row[key] for key in index_keys)
                 for row in raw["historical_lifecycle_index"]),
             "invalid historical lifecycle index")
    approval = validate_approval(raw["approval"], change_id=raw["change_id"])
    validate_retained_lineage(approval, raw["authorization_lineage"])
    code = validate_code_subject(raw["code_subject"], change_id=raw["change_id"]) if (
        raw["code_subject"] is not None) else None
    if for_v3:
        _validate_evidence_chain(raw["lifecycle"], raw["change_id"])
        if code is not None and any(isinstance(row, dict)
                and row.get("type") == "code_review_not_required" for row in raw["lifecycle"]):
            _validate_historical_review_failures(
                raw["historical_lifecycle_index"], raw["change_id"], code["subject_id"]
            )
    result = []
    for index, row in enumerate(raw["lifecycle"]):
        _require(isinstance(row, dict) and set(row) == {
                              "type", "payload", "timestamp", "source_timestamp", "actor",
                              "framework",
                              "source_event_id",
                              "source_event_digest"}, "invalid derived lifecycle row")
        _require(isinstance(row["payload"], dict), "invalid derived lifecycle payload")
        _require(for_v3 or row["type"] != "code_review_not_required",
                 "no-review completion requires a v3 attestation")
        payload = deepcopy(row["payload"])
        targets = [(payload, "plan_subject", approval["subject"]),
                   (payload, "approval", approval), (payload, "code_subject", code)]
        if isinstance(payload.get("verification"), dict):
            targets.append((payload["verification"], "code_subject", code))
        for target, key, value in targets:
            ref = key + "_ref"
            if ref in target:
                _require(target.pop(ref) == "current" and key not in target and value is not None,
                         "invalid current subject reference")
                target[key] = value
        record = {
            "event_id": "derived-" + digest_record([raw["change_id"], index, row]),
            "type": row["type"], "change_id": raw["change_id"], "timestamp": row["timestamp"],
            "actor": row["actor"], "framework": row["framework"],
            "framework_state": {"representation": REPRESENTATION,
                                "source_event_id": row["source_event_id"],
                                "source_event_digest": row["source_event_digest"],
                                "source_timestamp": row["source_timestamp"]},
            "payload": payload,
        }
        result.append(serialize_event(parse_event_line(json.dumps(record))))
    if not inactive_knowledge:
        from keepsail.core.events import Actor
        result.append(serialize_event(Event(
            event_id="derived-checkpoint-" + raw["knowledge_checkpoint"]["digest"],
            type="knowledge_checkpointed", change_id=raw["change_id"],
            timestamp=raw["lifecycle"][-1]["timestamp"],
            actor=Actor("agent", "attestation-export/v2"),
            framework="plain", payload=raw["knowledge_checkpoint"],
        )))
    from keepsail.core.reducer import derive_state_from_lines
    restored = derive_state_from_lines(result, _effective=True).get(raw["change_id"])
    _require(restored is not None and restored.current_state == raw["expected_state"]
             and restored.effective_approval == approval and restored.current_code_subject == code,
             "compact attestation expected state or current subject mismatch")
    return result
