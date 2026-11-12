"""Shared replay checks for committed lifecycle evidence."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    Recognition,
    evidence_digest,
    evidence_is_recognized,
    has_unresolved_candidate,
    is_attestation_path,
    make_code_subject,
    missing_coverage,
    resolve_review_reference,
    validate_approval,
    validate_code_subject,
    validate_evidence,
)
from keepsail.core.emit_validation import find_ordering_violations
from keepsail.core.events import Event, EventSchemaError, effective_event_lines, parse_event_line
from keepsail.core.reducer import derive_state
from keepsail.core.scope_match import GitScopeError, resolve_commit, tracked_files_at_commit

ATTESTATIONS_DIRNAME = ".harness/attestations"
PLACEHOLDER_IDENTITY = "cli"


def check_recognized_attestation(
    attestation_path: Path, slug: str, *, builtin_version: str = "keepsail-baseline/v1",
    repository_root: Path | None = None, code_review_required: bool = True,
) -> list[str]:
    """Check ordering, identity, state and old mandatory milestones for a replay."""
    try:
        states = derive_state(attestation_path)
    except (ApprovalError, EventSchemaError) as exc:
        return [f"attestation {slug}: invalid lifecycle evidence: {exc}"]
    if set(states) != {slug}:
        return [f"attestation {slug}: filename and contained Change differ"]
    blockers = []
    violations = find_ordering_violations(attestation_path, slug, builtin_version=builtin_version,
                                          repository_root=repository_root)
    if violations:
        blockers.append(f"attestation {slug}: lifecycle ordering invalid "
                        f"({len(violations)} violation(s); first: {violations[0].reason})")
    state = states[slug]
    if state.current_state != "READY_TO_MERGE":
        blockers.append(f"attestation {slug}: state is {state.current_state}, not READY_TO_MERGE")
    review_event = "code_review_passed" if code_review_required else "code_review_not_required"
    missing = sorted({"plan_approved", "implementation_complete", review_event}
                     - set(state.event_counts))
    if missing:
        blockers.append(f"attestation {slug}: missing milestone event(s) {missing}")
    return blockers


def _review_reference_blockers(events: list[Event], slug: str) -> list[str]:
    """A reference can use only the exact conclusion imported before its milestone."""
    available: list[dict[str, Any]] = []
    blockers = []
    for event in events:
        payload = event.payload
        if event.type == "review_evidence_imported":
            if isinstance(payload.get("evidence"), dict) and not payload.get("historical_only"):
                available.append(payload["evidence"])
        if payload.get("review_reference_version") is None:
            continue
        try:
            if event.type not in {
                "plan_approved", "plan_rejected", "code_review_passed", "code_review_failed",
            }:
                raise ApprovalError("review reference on an unsupported lifecycle event")
            kind = "plan" if event.type.startswith("plan_") else "code"
            decision = ("approve" if event.type in {"plan_approved", "code_review_passed"}
                        else "reject")
            subject = payload.get("approval" if kind == "plan" else "code_subject", {})
            subject_id = (payload.get("candidate_id") if event.type == "plan_rejected"
                          else subject.get("subject_id") if isinstance(subject, dict) else None)
            resolve_review_reference(payload, available, change_id=slug, kind=kind,
                                     decision=decision, subject_id=str(subject_id or ""))
        except (ApprovalError, TypeError, KeyError) as exc:
            blockers.append(f"attestation {slug}: invalid review reference: {exc}")
    return blockers


def _new_contract_blockers(
    root: Path,
    state: Any,
    slug: str,
    diff_entries: Sequence[Any],
    *,
    recognition: Recognition,
    base: str | None,
    head: str | None,
    attestation_path: Path | None = None,
    evidence_validator: Callable[[dict[str, Any], str], None] | None = None,
    code_review_required: bool = True,
) -> list[str]:
    """Check authority and subjects for a new-contract attestation."""
    blockers: list[str] = []
    try:
        approval = validate_approval(state.effective_approval, change_id=slug)
    except ApprovalError as exc:
        return [f"attestation {slug}: invalid effective plan approval: {exc}"]

    evidence_by_id = {
        item.get("evidence_id"): item
        for item in state.evidence_references
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    }
    plan_evidence = evidence_by_id.get(approval.get("evidence_id"))
    if not isinstance(plan_evidence, dict):
        blockers.append(f"attestation {slug}: effective approval evidence is not retained")
    else:
        try:
            validate_evidence(plan_evidence, change_id=slug)
        except ApprovalError:
            plan_valid = False
        else:
            plan_valid = True
        if not (
            plan_valid
            and plan_evidence.get("kind") == "plan"
            and plan_evidence.get("decision") == "approve"
            and plan_evidence.get("subject_id") == approval.get("subject_id")
            and evidence_digest(plan_evidence) == approval.get("evidence_digest")
            and (evidence_validator is not None
                 or evidence_is_recognized(plan_evidence, recognition))
        ):
            blockers.append(
                f"attestation {slug}: effective approval is not backed by recognized plan evidence"
            )
        provenance = plan_evidence.get("provenance")
        if evidence_validator is not None:
            try:
                evidence_validator(plan_evidence, "plan")
            except ApprovalError as exc:
                blockers.append(f"attestation {slug}: plan recognition invalid: {exc}")
        if evidence_validator is None and recognition.policy_digest and (
            not isinstance(provenance, dict)
            or provenance.get("policy_digest") != recognition.policy_digest
        ):
            blockers.append(
                f"attestation {slug}: plan evidence is bound to another recognition policy"
            )

    if has_unresolved_candidate(state):
        blockers.append(f"attestation {slug}: unresolved plan revision candidate")
    code_subject = state.current_code_subject
    if not isinstance(code_subject, dict):
        blockers.append(f"attestation {slug}: missing current code subject")
        return blockers
    try:
        validated_code = validate_code_subject(code_subject, change_id=slug)
        expected = make_code_subject(
            root,
            change_id=slug,
            approval_id=str(approval["approval_id"]),
            base=base or str(validated_code["base"]),
            head=head or str(validated_code["head"]),
            knowledge_basis=validated_code.get("knowledge_basis"),
        )
    except (ApprovalError, GitScopeError, KeyError) as exc:
        blockers.append(f"attestation {slug}: cannot recompute code subject: {exc}")
    else:
        if expected["subject_id"] != validated_code.get("subject_id"):
            blockers.append(
                f"attestation {slug}: code subject does not match the complete Git change set"
            )
        actual_paths = {
            path for entry in diff_entries for path in entry.paths if not is_attestation_path(path)
        }
        subject_paths = set()
        for item in validated_code.get("manifest", []):
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("path"), str):
                subject_paths.add(item["path"])
            if isinstance(item.get("old_path"), str):
                subject_paths.add(item["old_path"])
        if actual_paths != subject_paths:
            blockers.append(
                f"attestation {slug}: code subject manifest does not cover the exact PR paths"
            )
    verification = state.current_verification
    if not isinstance(verification, dict):
        blockers.append(f"attestation {slug}: missing verification subject")
    elif verification.get("subject_id") != code_subject.get("subject_id"):
        blockers.append(f"attestation {slug}: verification is for a different code subject")
    elif verification.get("outcome") != "passed":
        blockers.append(f"attestation {slug}: current verification did not pass")

    attestation_events = events_from_stateful_attestation(root, slug, path=attestation_path)
    code_review = next(
        (event for event in reversed(attestation_events) if event.type == "code_review_passed"),
        None,
    )
    if not code_review_required:
        from keepsail.core.no_review import verify_no_review_binding

        no_review = next((event for event in reversed(attestation_events)
                          if event.type == "code_review_not_required"), None)
        try:
            if no_review is None or no_review.payload.get("trusted_base") != base:
                raise ApprovalError("missing current no-review decision")
            verify_no_review_binding(root, no_review, code_subject)
        except (ApprovalError, GitScopeError, ValueError, TypeError, KeyError) as exc:
            blockers.append(f"attestation {slug}: no-review decision invalid: {exc}")
    elif code_review is None:
        blockers.append(f"attestation {slug}: missing code review pass event")
    else:
        evidence_id = code_review.payload.get("evidence_id")
        code_evidence = evidence_by_id.get(evidence_id)
        if not isinstance(code_evidence, dict):
            blockers.append(f"attestation {slug}: code review evidence is not retained")
        else:
            try:
                validate_evidence(code_evidence, change_id=slug)
            except ApprovalError:
                code_valid = False
            else:
                code_valid = True
            if not (
                code_valid
                and code_evidence.get("kind") == "code"
                and code_evidence.get("decision") == "approve"
                and code_evidence.get("subject_id") == code_subject.get("subject_id")
                and (evidence_validator is not None
                     or evidence_is_recognized(code_evidence, recognition))
            ):
                blockers.append(
                    f"attestation {slug}: code review is not backed by recognized code evidence"
                )
            if evidence_validator is not None:
                try:
                    evidence_validator(code_evidence, "code")
                except ApprovalError as exc:
                    blockers.append(f"attestation {slug}: code recognition invalid: {exc}")
        if (isinstance(code_evidence, dict) and evidence_validator is None
                and recognition.policy_digest):
            provenance = code_evidence.get("provenance")
            if (
                not isinstance(provenance, dict)
                or provenance.get("policy_digest") != recognition.policy_digest
            ):
                blockers.append(
                    f"attestation {slug}: code evidence is bound to another recognition policy"
                )
    coverage = state.coverage_manifest
    try:
        missing = missing_coverage(code_subject, coverage)
    except ApprovalError:
        missing = ["<invalid code subject>"]
    if missing:
        blockers.append(f"attestation {slug}: implementation coverage omits a changed file")
    blockers.extend(_review_reference_blockers(attestation_events, slug))
    return blockers


def _knowledge_attestation(
    root: Path, att_path: Path, state: Any, *, base: str | None, head: str | None = None
) -> None:
    from keepsail.core.knowledge import policy_configuration, validate_checkpoint
    policy, _ = policy_configuration(
        root, ref=base, candidate_ref=head or ("HEAD" if base else None)
    )
    checkpoints = []
    lines = att_path.read_bytes().decode("utf-8").splitlines(keepends=True)
    for line in effective_event_lines(lines):
        if not line.strip():
            continue
        try:
            event = parse_event_line(line)
        except EventSchemaError:
            # Legacy tolerant parsing is retained; enabled knowledge records and
            # malformed knowledge material must never disappear into that path.
            if policy is not None or "knowledge_" in line:
                raise
            continue
        if event.type == "knowledge_checkpointed":
            checkpoints.append(event.payload)
        elif policy is None and event.type.startswith("knowledge_"):
            raise ApprovalError("knowledge evidence has no trusted activation")
    if policy is None:
        if checkpoints or (state.current_code_subject or {}).get("knowledge_basis"):
            raise ApprovalError("knowledge protocol is not activated in the trusted base")
        return
    if not checkpoints:
        raise ApprovalError("activated knowledge protocol requires a retained checkpoint")
    if checkpoints[-1].get("schema_version") == "knowledge-checkpoint/v2":
        from keepsail.core.approval import resolve_contract_base
        from keepsail.core.knowledge_checkpoint import resolve_facts
        trusted = resolve_commit(root, base) if base else resolve_contract_base(root)
        if checkpoints[-1].get("baseline", {}).get("commit") != trusted:
            raise ApprovalError("checkpoint baseline is not the trusted Git base")
        facts = resolve_facts(root, checkpoints[-1], policy)
        validate_checkpoint(checkpoints[-1], policy, state, retained_facts=facts)
        return
    required: list[dict[str, Any]] = []
    if base:
        from keepsail.core.scope_match import file_text_at_commit
        for path in tracked_files_at_commit(root, base):
            if path.startswith(ATTESTATIONS_DIRNAME + "/") and path.endswith(".jsonl"):
                for line in file_text_at_commit(root, base, path).splitlines():
                    raw = json.loads(line)
                    if raw.get("schema_version") == "attestation/v2":
                        raise ApprovalError("legacy checkpoint cannot omit a trusted v2 baseline")
                    if raw.get("type") == "knowledge_checkpointed":
                        if raw["payload"].get("schema_version") != "knowledge-checkpoint/v1":
                            raise ApprovalError("legacy checkpoint requires the v2 baseline reader")
                        required.extend(raw["payload"]["events"])
    validate_checkpoint(checkpoints[-1], policy, state, required_events=required)


def events_from_stateful_attestation(root: Path, slug: str, *,
                                    path: Path | None = None) -> list[Event]:
    """Read one attestation's valid event lines for new-contract checks."""
    path = path or root / ATTESTATIONS_DIRNAME / f"{slug}.jsonl"
    events: list[Event] = []
    try:
        lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
    except OSError:
        return events
    for raw in effective_event_lines(lines):
        try:
            event = parse_event_line(raw)
        except EventSchemaError:
            continue
        if event.change_id == slug:
            events.append(event)
    return events


def _classify_review(events: list[Event], milestone: str, author: str | None) -> dict[str, Any]:
    """One role's disclosure row, from the last occurrence of its PASS milestone.

    Truth table, first match wins:
      1. no milestone event                         → ``unattributed``
         referenced retained external approval      → ``external-evidence``
         (unless skipped; no identity claim is made)
      2. reviewer ``actor.type == "ci"``            → ``ci`` (forward-compat;
         not producible via the current CLI, see design §4.1 row 2)
      3. ``payload["skipped"] is True``             → ``skipped``
      4. reviewer or author is the ``"cli"`` placeholder → ``unattributed``
      5. reviewer identifier == author identifier   → ``self-signed``
      6. otherwise                                  → ``independent``
    """
    position = next((i for i in range(len(events) - 1, -1, -1)
                     if events[i].type == milestone), None)
    if position is None:
        return {
            "classification": "unattributed",
            "reviewer": None,
            "skipped": False,
            "override": False,
            "reason": None,
        }
    r = events[position]  # last wins (reject → re-review cycles)
    reviewer = r.actor.identifier
    skipped = r.payload.get("skipped") is True
    override = r.payload.get("override") is True
    if not skipped and r.payload.get("evidence_id"):
        # Attribute the referenced conclusion, not the actor who imported it.
        # This is disclosure of a retained claim, never verified independence.
        for imported in reversed(events[:position]):
            evidence = imported.payload.get("evidence")
            if (imported.type != "review_evidence_imported"
                    or imported.change_id != r.change_id
                    or not isinstance(evidence, dict)
                    or evidence.get("evidence_id") != r.payload["evidence_id"]):
                continue
            try:
                evidence = validate_evidence(evidence, change_id=r.change_id)
            except ApprovalError:
                break
            kind = "plan" if milestone == "plan_approved" else "code"
            subject = r.payload.get("approval" if kind == "plan" else "code_subject")
            if (evidence["kind"] != kind or evidence["decision"] != "approve"
                    or imported.payload.get("historical_only") is True
                    or imported.payload.get("evidence_digest") != evidence_digest(evidence)
                    or (r.payload.get("review_reference_version") is not None
                        and r.payload.get("evidence_digest") != evidence_digest(evidence))
                    or not isinstance(subject, dict)
                    or subject.get("subject_id") != evidence["subject_id"]):
                break
            return {
                "classification": "external-evidence",
                "reviewer": None,
                "importer": reviewer,
                "evidence_id": evidence["evidence_id"],
                "process": evidence["process"],
                "issuer": evidence["issuer"],
                "subject_id": evidence["subject_id"],
                "skipped": False,
                "override": False,
                "reason": None,
            }
    if r.actor.type == "ci":
        cls = "ci"
    elif skipped:
        cls = "skipped"
    elif reviewer == PLACEHOLDER_IDENTITY or author == PLACEHOLDER_IDENTITY:
        cls = "unattributed"
    elif reviewer == author:
        cls = "self-signed"
    else:
        cls = "independent"
    return {
        "classification": cls,
        "reviewer": reviewer,
        "skipped": skipped,
        "override": override,
        "reason": r.payload.get("reason"),
    }


def derive_independence(events: list[Event]) -> dict[str, Any]:
    """Classify a change's review independence, per role, from its events (pure).

    Both roles, from the same truth table (see ``_classify_review``) applied to their
    PASS milestones — ``code_review_passed`` and ``plan_approved``. Plan review joined
    code review here because ``review skip --reviewer plan-reviewer`` otherwise emitted
    ``plan_approved`` and merged with nothing said anywhere, which is why a series of
    mis-drawn skip-evidence boundaries all failed silently rather than loudly.

    This is disclosure, not enforcement: the identity is self-asserted and a solo
    owner can set both sides freely. The one blocker built on it lives in
    ``verify_attestations``.
    """
    author = next((e.actor.identifier for e in events if e.type == "intent_declared"), None)
    return {
        "author": author,
        "code_review": _classify_review(events, "code_review_passed", author),
        "plan_review": _classify_review(events, "plan_approved", author),
        # Informational, like the rest of this function — NOT a merge blocker.
        # Hitting the round budget is a legitimate, human-authorized act; it has to be
        # visible at the moment of merge, not forbidden. Deduped on (reviewer,
        # attempted_round) so a retrying agent cannot inflate a figure presented as
        # rounds; an event without that field counts once via its own id.
        "review_budget_rounds_held": len(
            {
                (
                    (e.payload or {}).get("reviewer"),
                    (e.payload or {}).get("attempted_round", f"event:{e.event_id}"),
                )
                for e in events
                if e.type == "review_budget_exceeded"
            }
        ),
    }


def gate_bypass_disclosure(events: list[Event]) -> dict[str, Any]:
    """Count gate bypasses vs disclosures by APPEND ORDER (pure; no timestamps).

    Append position is causal truth. A ``gate_bypassed`` is undisclosed iff it
    appears after the last ``gate_bypass_disclosed`` in the event list.
    """
    last_disclosed = max(
        (i for i, e in enumerate(events) if e.type == "gate_bypass_disclosed"),
        default=-1,
    )
    undisclosed = sum(
        1 for i, e in enumerate(events) if e.type == "gate_bypassed" and i > last_disclosed
    )
    bypassed = sum(1 for e in events if e.type == "gate_bypassed")
    disclosed = sum(1 for e in events if e.type == "gate_bypass_disclosed")
    reasons = [e.payload.get("reason") for e in events if e.type == "gate_bypass_disclosed"]
    return {
        "bypassed": bypassed,
        "disclosed": disclosed,
        "undisclosed": undisclosed,
        "reasons": reasons,
    }
