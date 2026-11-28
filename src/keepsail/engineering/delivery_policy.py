"""Committed delivery-policy snapshots and current delivery visibility."""

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    make_code_subject,
    resolve_contract_base,
    validate_code_subject,
)
from keepsail.core.effective_policy import load_effective_v2
from keepsail.core.git_objects import optional_regular_blob_text
from keepsail.core.policy_snapshot import PolicySnapshot as PolicySnapshot
from keepsail.core.policy_snapshot import read_policy_snapshot as read_policy_snapshot
from keepsail.core.scope_match import GitScopeError
from keepsail.core.strict_yaml import parse_unique_yaml


def delivery_details(root: Path, state: Any) -> dict[str, Any] | None:
    """Resolve current obligations without claiming historical deliveries used them."""
    if (state.current_code_subject is None or state.current_state not in {
        "IMPLEMENTATION_IN_PROGRESS", "AWAITING_CODE_REVIEW", "CODE_REVIEW_REJECTED",
        "READY_TO_MERGE",
    }):
        return None
    try:
        base = resolve_contract_base(root)
        text = optional_regular_blob_text(root, base, ".harness/review-recognition.yaml")
        policy = parse_unique_yaml(text) if text is not None else None
        if not isinstance(policy, dict) or policy.get("version") != "review-recognition/v2":
            return None
        snapshot = load_effective_v2(root, base)
        subject = validate_code_subject(state.current_code_subject, change_id=state.change_id)
        current = make_code_subject(
            root, change_id=state.change_id, approval_id=subject["approval_id"], base=base,
            verification_config_digest=subject.get("verification_config_digest"),
            knowledge_basis=subject.get("knowledge_basis"),
            legacy_paths=subject.get("path_representation") != "git-literal/v1",
        )
        required, reason = snapshot.policy.review_requirement(current["manifest"])
        return {"status": "resolved", "trusted_base": base,
                "policy_digest": snapshot.policy.policy_digest,
                "required_checks_digest": snapshot.checks["digest"],
                "required_checks": [{"source": item["source"], "id": item["id"]}
                                    for item in snapshot.checks["checks"]],
                "required_project_checks": sum(
                    item["source"] == "user" for item in snapshot.checks["checks"]
                ),
                "builtin_checks_version": snapshot.policy.builtin_checks_version,
                "code_review_required": required, "code_review_reason": reason,
                "current_subject_id": current["subject_id"],
                "recorded_subject_id": subject["subject_id"],
                "subject_matches": current["subject_id"] == subject["subject_id"],
                "basis": "committed-git-diff"}
    except (ApprovalError, GitScopeError, OSError, ValueError, KeyError, TypeError) as exc:
        return {"status": "unavailable", "reason": str(exc)}


_ACTIVE_DELIVERY_STATES = frozenset({
    "IMPLEMENTATION_IN_PROGRESS", "AWAITING_CODE_REVIEW", "CODE_REVIEW_REJECTED",
    "READY_TO_MERGE",
})


def risk_boundary_details(root: Path, state: Any) -> dict[str, Any] | None:
    """Show a committed risk-boundary change, its differences and the owner's record."""
    from keepsail.core.approval import validate_approval
    from keepsail.core.review_verdict import read_change_events
    from keepsail.core.risk_boundary import (
        ACCEPTANCE_EVENT,
        RISK_BOUNDARY_COMMITMENT,
        compare_risk_boundary,
    )
    from keepsail.core.scope_match import resolve_commit

    if (not isinstance(state.effective_approval, dict)
            or state.current_state not in _ACTIVE_DELIVERY_STATES):
        return None
    try:
        approval = validate_approval(state.effective_approval, change_id=state.change_id)
        declared = any(item.get("id") == RISK_BOUNDARY_COMMITMENT
                       and isinstance(item.get("text"), str) and item["text"].strip()
                       for item in approval["subject"].get("commitments", []))
        boundary = compare_risk_boundary(root, base=resolve_contract_base(root),
                                         head=resolve_commit(root))
        if boundary is None or not boundary.changed:
            return ({"status": "declared-unchanged",
                     "reason": f"the plan declares {RISK_BOUNDARY_COMMITMENT} but the committed "
                               "HEAD changes neither the policy nor the required checks"}
                    if declared else None)
        expected = boundary.acceptance(change_id=state.change_id,
                                       plan_subject_id=approval["subject_id"])
        accepted = [event for event in read_change_events(root / ".harness/events.jsonl",
                                                          state.change_id)
                    if event.type == ACCEPTANCE_EVENT]
        acceptance = None
        if accepted:
            latest = accepted[-1]
            acceptance = {"event_id": latest.event_id,
                          "actor": {"type": latest.actor.type,
                                    "identifier": latest.actor.identifier},
                          "ts": latest.timestamp, "matches": latest.payload == expected}
        return {"status": "changed", "declared": declared, "labels": boundary.labels,
                "obligation_changes": boundary.differences,
                "predecessor_policy_digest": boundary.base.digest,
                "target_policy_digest": boundary.target.digest,
                "target_policy_state": boundary.target.state,
                "acceptance": acceptance}
    except (ApprovalError, GitScopeError, OSError, ValueError, KeyError, TypeError) as exc:
        return {"status": "unavailable", "reason": str(exc)}


def approval_recognition(root: Path, state: Any) -> dict[str, Any] | None:
    """Whether the effective plan approval is still recognized by the effective policy."""
    from keepsail.core.review_basis import validate_effective_plan_basis

    if not isinstance(state.effective_approval, dict):
        return None
    try:
        basis = validate_effective_plan_basis(root, root / ".harness/events.jsonl", state)
    except (ApprovalError, GitScopeError, OSError, ValueError, KeyError, TypeError) as exc:
        return {"recognized": False, "reason": str(exc)}
    return {"recognized": True, "policy_digest": basis["policy_digest"]}
