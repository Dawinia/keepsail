"""Strict, single-line representation of the no-review completion pair."""

from __future__ import annotations

import json
import re
from typing import Any

from keepsail.core.approval import ApprovalError, canonical_json, digest_record
from keepsail.core.events import Event, EventSchemaError, parse_event_line, serialize_event

_BASE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EventSchemaError("duplicate completion transaction key")
        value[key] = item
    return value


def _validate_pair(events: list[Event]) -> None:
    if (len(events) != 2 or [event.type for event in events]
            != ["implementation_complete", "code_review_not_required"]):
        raise EventSchemaError("completion transaction requires exactly the prescribed event pair")
    completed, no_review = events
    for event in events:
        if (not isinstance(event.event_id, str) or not event.event_id
                or not isinstance(event.change_id, str) or not isinstance(event.payload, dict)):
            raise EventSchemaError("completion transaction event identity or payload is invalid")
        try:
            parse_event_line(serialize_event(event))
        except (TypeError, ValueError) as exc:
            raise EventSchemaError("completion transaction event is invalid") from exc
    if (completed.change_id != no_review.change_id or not completed.change_id
            or completed.event_id == no_review.event_id):
        raise EventSchemaError("completion transaction event identities do not match")
    if set(no_review.payload) != {"subject_id", "trusted_base", "policy_digest", "reason"}:
        raise EventSchemaError("completion transaction policy bindings are invalid")
    subject = completed.payload.get("code_subject")
    if (not isinstance(subject, dict) or not isinstance(subject.get("subject_id"), str)
            or not subject["subject_id"]
            or no_review.payload.get("subject_id") != subject["subject_id"]):
        raise EventSchemaError("completion transaction code subjects do not match")
    base = no_review.payload.get("trusted_base")
    policy = no_review.payload.get("policy_digest")
    reason = no_review.payload.get("reason")
    if (not isinstance(base, str) or _BASE.fullmatch(base) is None
            or not isinstance(policy, str) or _DIGEST.fullmatch(policy) is None
            or not isinstance(reason, str) or not reason.strip()):
        raise EventSchemaError("completion transaction lacks trusted policy bindings")


def encode_completion(events: list[Event]) -> bytes:
    """Return one complete checksummed physical line after validating both events."""
    _validate_pair(events)
    body = {"schema_version": "completion-transaction/v1",
            "change_id": events[0].change_id,
            "events": [json.loads(serialize_event(event)) for event in events]}
    return (canonical_json({**body, "digest": digest_record(body)}) + "\n").encode("utf-8")


def decode_completion(data: bytes) -> list[Event]:
    """Reject partial, noncanonical, ambiguous or modified transactions."""
    if not data.endswith(b"\n") or data.count(b"\n") != 1:
        raise EventSchemaError("completion transaction is not a complete single line")
    try:
        text = data.decode("utf-8")
        raw = json.loads(text, object_pairs_hook=_unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EventSchemaError("completion transaction is invalid JSON") from exc
    if (not isinstance(raw, dict) or set(raw) != {"schema_version", "change_id", "events", "digest"}
            or raw["schema_version"] != "completion-transaction/v1"):
        raise EventSchemaError("unsupported completion transaction")
    body = {key: value for key, value in raw.items() if key != "digest"}
    try:
        matches = raw["digest"] == digest_record(body) and text == canonical_json(raw) + "\n"
    except ApprovalError as exc:
        raise EventSchemaError("completion transaction is not canonical JSON") from exc
    if not matches:
        raise EventSchemaError("completion transaction digest or encoding does not match")
    if not isinstance(raw["events"], list):
        raise EventSchemaError("completion transaction events must be a list")
    try:
        events = [parse_event_line(canonical_json(item)) for item in raw["events"]]
    except (TypeError, ValueError) as exc:
        raise EventSchemaError("completion transaction event is invalid") from exc
    if any(json.loads(serialize_event(event)) != item
           for event, item in zip(events, raw["events"], strict=True)):
        raise EventSchemaError("completion transaction event contains unknown fields")
    _validate_pair(events)
    if raw["change_id"] != events[0].change_id:
        raise EventSchemaError("completion transaction Change does not match")
    return events
