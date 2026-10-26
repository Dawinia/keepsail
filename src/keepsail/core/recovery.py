"""Strict recovery of already merged, immutable historical lifecycle evidence.

Live preparation verifies Git/GitHub; replay uses only the retained envelope.
Knowledge-bearing streams require a future dependency-closure protocol.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from keepsail.core.approval import (
    ApprovalError,
    _recognition_from_mapping,
    evidence_digest,
    evidence_is_recognized,
    has_unresolved_candidate,
    load_recognition,
    make_code_subject,
    missing_coverage,
    validate_approval,
    validate_code_subject,
    validate_evidence,
)
from keepsail.core.events import (
    KNOWN_EVENT_TYPES,
    Actor,
    Event,
    parse_event_line,
)
from keepsail.core.scope_match import file_text_at_commit, resolve_commit

RECOVERY_EVENT = "historical_change_recovered"
PROTOCOL = "historical-merge-recovery/v1"


def _need(condition: object, message: str) -> None:
    if not condition:
        raise ApprovalError(f"historical recovery: {message}")


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        _need(key not in out, f"duplicate JSON key {key}")
        out[key] = value
    return out


def strict_events(text: str, change: str | None = None) -> list[Event]:
    out: list[Event] = []
    seen: set[str] = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        raw = json.loads(line, object_pairs_hook=_unique)
        event = parse_event_line(line)
        _need(isinstance(event.event_id, str) and event.event_id not in seen,
              "duplicate or malformed event ID")
        _need(isinstance(raw, dict) and isinstance(raw.get("payload", {}), dict),
              "malformed event payload")
        seen.add(event.event_id)
        if change is not None:
            _need(set(raw) <= set(asdict(event)), "unsupported source event fields")
            _need(event.change_id == change, "source contains another Change")
            _need(event.type in KNOWN_EVENT_TYPES and event.type != RECOVERY_EVENT,
                  "unknown or nested source event")
            _need(not event.type.startswith("knowledge_") and
                  "knowledge_basis" not in json.dumps(event.payload),
                  "knowledge dependency closure is not supported by recovery v1")
        out.append(event)
    return out


def retained_history(payload: dict[str, Any], change: str) -> list[Event]:
    """Validate a self-contained envelope without network, Git or mutable files."""
    from keepsail.core.reducer import derive_state_from_lines
    from keepsail.core.transitions import INVALID, compute_target_state

    _need(payload.get("version") == PROTOCOL, "unsupported recovery reader")
    source = payload.get("source_text")
    _need(isinstance(source, str), "missing original source bytes")
    assert isinstance(source, str)
    _need(sha256(source.encode()).hexdigest() == payload.get("source_sha256"),
          "retained source digest mismatch")
    events = strict_events(source, change)
    _need(bool(events), "empty source")
    recognition = _recognition_from_mapping(payload.get("historical_recognition"))
    _need(recognition.policy_digest == payload.get("historical_recognition_digest"),
          "retained historical recognition mismatch")
    for event in events:
        if event.type == "review_evidence_imported":
            record = validate_evidence(event.payload.get("evidence"), change_id=change)
            _need(evidence_digest(record) == event.payload.get("evidence_digest") and
                  evidence_is_recognized(record, recognition) and
                  record.get("provenance", {}).get("policy_digest") == recognition.policy_digest,
                  "historical recognition or retained evidence digest mismatch")
    current = None
    seen: set[str] = set()
    for event in events:
        target = compute_target_state(current, event.type)
        _need(target != INVALID, "source lifecycle ordering conflict")
        if event.type == "implementation_complete":
            _need("verification_passed" in seen, "missing verification predecessor")
        current = target
        seen.add(event.type)
    _need(current == "READY_TO_MERGE", "source must retain the reviewed pre-merge history")
    state = derive_state_from_lines(source.splitlines())[change]
    approval = validate_approval(state.effective_approval, change_id=change)
    subject = validate_code_subject(state.current_code_subject, change_id=change)
    _need(not has_unresolved_candidate(state), "unresolved plan candidate")
    approved_position = max(i for i, e in enumerate(events) if e.type == "plan_approved")
    candidate = next((e.payload.get("plan_subject") for e in reversed(events[:approved_position])
                      if e.type in {"plan_ready", "plan_revision_submitted"}), None)
    _need(candidate == approval["subject"], "approval has no matching plan candidate")
    _need(subject["approval_id"] == approval["approval_id"], "code approval mismatch")
    verification = state.current_verification or {}
    _need(verification.get("outcome") == "passed" and
          verification.get("subject_id") == subject["subject_id"] and
          verification.get("code_subject") == subject,
          "verification does not cover final subject")
    _need(bool(state.implementation_assessments) and bool(state.coverage_manifest) and
          not missing_coverage(subject, state.coverage_manifest),
          "incomplete implementation coverage")
    evidence = {e.get("evidence_id"): e for e in state.evidence_references}
    plan = evidence.get(approval["evidence_id"])
    _need(isinstance(plan, dict), "missing retained plan review")
    assert isinstance(plan, dict)
    validate_evidence(plan, change_id=change)
    _need(plan.get("decision") == "approve" and plan.get("kind") == "plan" and
          plan.get("subject_id") == approval["subject_id"] and
          evidence_digest(plan) == approval["evidence_digest"], "plan review mismatch")
    review = next(e for e in reversed(events) if e.type == "code_review_passed")
    completion = next(e for e in reversed(events) if e.type == "implementation_complete")
    _need(completion.payload.get("code_subject") == subject,
          "completion does not cover final reviewed subject")
    code = evidence.get(review.payload.get("evidence_id"))
    _need(isinstance(code, dict), "missing retained code review")
    assert isinstance(code, dict)
    validate_evidence(code, change_id=change)
    _need(code.get("decision") == "approve" and code.get("kind") == "code" and
          code.get("subject_id") == subject["subject_id"] and
          review.payload.get("evidence") == code, "code review mismatch")
    count = payload.get("prefix_count")
    _need(type(count) is int and 0 <= count <= len(events), "invalid source prefix count")
    fact = payload.get("merge_fact", {})
    _need(fact.get("state") == "MERGED" and bool(fact.get("mergedAt")),
          "missing retained merge fact")
    merged = parse_event_line(json.dumps(payload.get("merged_event")))
    _need(merged.type == "merged" and merged.change_id == change and
          merged.payload == {"merge_commit_sha": fact.get("mergeCommit", {}).get("oid")} and
          merged.timestamp == fact["mergedAt"] and
          merged.event_id not in {e.event_id for e in events}, "merge event mismatch")
    return [*events[count:], merged]


def github_merge_fact(root: Path, repository: str, pr: int) -> dict[str, Any]:
    result = subprocess.run(
        ["gh", "pr", "view", str(pr), "--repo", repository, "--json",
         "state,mergedAt,mergeCommit,headRefOid,baseRefName,url,body"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", check=True, timeout=30,
    )
    value: dict[str, Any] = json.loads(result.stdout)
    return value


def _repository(root: Path) -> str:
    remote = subprocess.check_output(
        ["git", "remote", "get-url", "origin"], cwd=root, text=True,
    ).strip()
    match = re.fullmatch(
        r"(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?", remote)
    _need(match is not None, "origin must identify a GitHub repository")
    assert match is not None
    return match[1]


def _source_blob(root: Path, commit: str, path: str) -> str:
    # Read bytes: text-mode Git helpers normalize CRLF and cannot retain a blob's
    # original digest. UTF-8 decoding/encoding preserves the exact source bytes.
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"], cwd=root,
    ).decode("utf-8")


def prepare_recovery(
    root: Path, change: str, source_commit: str, pr: int, *, events_file: Path | None = None
) -> dict[str, Any]:
    """Read-only validation. A source object alone is never proof of merge."""
    from keepsail.core.clock import utc_now_iso
    from keepsail.core.events import effective_event_lines
    from keepsail.core.reducer import derive_state_from_lines
    from keepsail.core.ulid import new_event_id

    source_commit = resolve_commit(root, source_commit)
    repository = _repository(root)
    fact = github_merge_fact(root, repository, pr)
    _need(fact.get("state") == "MERGED" and
          fact.get("mergeCommit", {}).get("oid") == source_commit and
          fact.get("url") == f"https://github.com/{repository}/pull/{pr}",
          "PR repository or actual merge object mismatch")
    body = fact.get("body", "")
    blocks = re.findall(
        r"<!-- (?:keepsail|super-harness):metadata -->(.*?)"
        r"<!-- /(?:keepsail|super-harness):metadata -->",
        body, re.S,
    )
    identities = [m for block in blocks for m in re.findall(r"^change:\s*(\S+)\s*$", block,
                                                          re.I | re.M)]
    _need(identities == [change], "PR must identify the exact Change once")
    path = f".harness/attestations/{change}.jsonl"
    source = _source_blob(root, source_commit, path)
    _need(source == _source_blob(root, fact["headRefOid"], path),
          "merged attestation differs from the PR head evidence")
    events = strict_events(source, change)
    _need(bool(events), "missing source history")
    code_event = next((e for e in reversed(events) if e.type == "code_review_passed"), None)
    _need(code_event is not None, "missing code approval")
    assert code_event is not None
    subject = validate_code_subject(code_event.payload.get("code_subject"), change_id=change)
    # The first protocol deliberately excludes historical knowledge closure.
    from keepsail.core.knowledge import load_policy
    _need(load_policy(root, ref=subject["base"]) is None,
          "historical active knowledge requires unsupported dependency closure")
    recognition = load_recognition(root, ref=subject["base"])
    for head in [subject["head"], fact["headRefOid"], source_commit]:
        expected = make_code_subject(
            root, change_id=change, approval_id=subject["approval_id"],
            base=subject["base"], head=head, knowledge_basis=None,
            verification_config_digest=subject.get("verification_config_digest"),
        )
        _need(expected["subject_id"] == subject["subject_id"],
              "complete merged content differs from reviewed code subject")
    target_path = events_file or root / ".harness/events.jsonl"
    physical = target_path.read_bytes() if target_path.exists() else b""
    _need(not physical or physical.endswith(b"\n"), "unterminated target ledger")
    target = strict_events(physical.decode())
    prior = [e for e in target if e.type == RECOVERY_EVENT and e.change_id == change]
    identity = {"repository": repository, "source_commit": source_commit, "pr": pr,
                "source_sha256": sha256(source.encode()).hexdigest()}
    if prior:
        _need(len(prior) == 1 and all(prior[0].payload.get(k) == v for k, v in identity.items()) and
              prior[0].payload.get("merge_fact") == fact, "conflicting recovery already recorded")
        retained_history(prior[0].payload, change)
        replay = derive_state_from_lines(physical.decode().splitlines()).get(change)
        _need(replay is not None and replay.current_state == "ARCHIVED" and
              replay.merge_commit_sha == source_commit, "recovered state no longer matches")
        return {"idempotent_replay": True, "expected_revision": sha256(physical).hexdigest(),
                "merge_commit_sha": source_commit, "change_id": change}
    effective = strict_events("\n".join(effective_event_lines(physical.decode().splitlines())))
    existing = [e for e in effective if e.change_id == change]
    _need([asdict(e) for e in existing] == [asdict(e) for e in events[:len(existing)]],
          "target history is not an exact ordered source prefix")
    occupied = {e.event_id for e in effective} | {e.event_id for e in target}
    _need(not any(e.event_id in occupied for e in events[len(existing):]), "event ID conflict")
    merged = Event(new_event_id(), "merged", change, fact["mergedAt"],
                   Actor("ci", "historical-merge-recovery"), "plain",
                   payload={"merge_commit_sha": source_commit})
    payload = {"version": PROTOCOL, **identity, "source_path": path, "source_text": source,
               "prefix_count": len(existing), "merge_fact": fact,
               "historical_recognition_digest": recognition.policy_digest,
               "historical_recognition": yaml.safe_load(file_text_at_commit(
                   root, subject["base"], ".harness/review-recognition.yaml")),
               "expected_revision": sha256(physical).hexdigest(), "merged_event": asdict(merged)}
    retained_history(payload, change)
    state = derive_state_from_lines(source.splitlines())[change]
    envelope = Event(new_event_id(), RECOVERY_EVENT, change, utc_now_iso(),
                     Actor("agent", "change-recover"), "plain", payload=payload)
    return {"idempotent_replay": False, "expected_revision": payload["expected_revision"],
            "change_id": change, "merge_commit_sha": source_commit,
            "missing_events": len(events) - len(existing),
            "approval_id": (state.effective_approval or {})["approval_id"],
            "code_subject_id": subject["subject_id"], "event": asdict(envelope)}


def validate_recovery(events_file: Path, event: Event) -> None:
    """Shared strict writer seam; rejects handcrafted/bypassed envelopes."""
    payload = event.payload
    retained_history(payload, event.change_id)
    expected = prepare_recovery(events_file.parent.parent, event.change_id,
                                payload["source_commit"], payload["pr"], events_file=events_file)
    _need(not expected["idempotent_replay"], "recovery was already recorded")
    existing = strict_events(events_file.read_text(encoding="utf-8"))
    ids = {e.event_id for e in existing}
    _need(event.event_id not in ids and
          payload["merged_event"]["event_id"] not in ids, "recovery event ID conflict")
    actual = dict(payload)
    prepared = expected["event"]["payload"]
    # IDs/time of a prepared record are locators; its facts must match exactly.
    prepared["merged_event"] = actual["merged_event"]
    _need(prepared == actual, "recovery facts or target revision changed")


def recovery_event(data: dict[str, Any]) -> Event:
    return parse_event_line(json.dumps(data["event"]))
