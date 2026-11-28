"""Guard committed deliveries: obligations come from the trusted base, unchanged.

A delivery that changes the enabled recognition policy or the required checks
is a risk-boundary change.  It still delivers under the baseline obligations,
and additionally needs its plan declaration and the owner's matching recorded
``policy accept`` (see ``keepsail.core.risk_boundary``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    make_code_subject,
    resolve_contract_base,
    validate_approval,
    validate_code_subject,
)
from keepsail.core.review_verdict import read_change_events
from keepsail.core.risk_boundary import (
    ACCEPTANCE_EVENT,
    POLICY_PATH,
    VERIFICATION_PATH,
    RiskBoundary,
    compare_risk_boundary,
    require_matching_acceptance,
    require_risk_boundary_declaration,
)
from keepsail.core.scope_match import GitScopeError, resolve_commit


def validate_legacy_risk_boundary(root: Path) -> None:
    """A Change without plan approval cannot alter an enabled policy or its checks."""
    try:
        head = resolve_commit(root)
    except GitScopeError:
        return
    try:
        base = resolve_contract_base(root)
    except ApprovalError:
        # No trusted baseline: the first enabled policy is adoption, not a Change.
        return
    boundary = compare_risk_boundary(root, base=base, head=head)
    if boundary is not None and boundary.changed:
        raise ApprovalError(
            "changing an enabled recognition policy or the required checks needs an "
            "approved plan declaring RISK-BOUNDARY and the owner's `keepsail policy accept`")


def risk_boundary_change_required(
    root: Path, *, base: str, head: str, changed_paths: set[str],
) -> bool:
    """Whether a committed base..head delivery is a risk-boundary change."""
    if not changed_paths.intersection({POLICY_PATH, VERIFICATION_PATH}):
        return False
    boundary = compare_risk_boundary(root, base=base, head=head)
    return boundary is not None and boundary.changed


def delivery_boundary(root: Path, *, base: str, head: str) -> RiskBoundary:
    boundary = compare_risk_boundary(root, base=base, head=head)
    if boundary is None:
        raise ApprovalError("delivery requires an enabled trusted review recognition policy")
    return boundary


def validate_delivery_obligations(
    root: Path, events_file: Path, state: Any, subject: object,
) -> dict[str, Any]:
    """Recompute trusted and candidate obligations before accepting completion."""
    if state is None or not isinstance(state.effective_approval, dict):
        raise ApprovalError("delivery requires an effective plan approval")
    code = validate_code_subject(subject, change_id=state.change_id)
    base = resolve_contract_base(root)
    head = resolve_commit(root)
    current_code = make_code_subject(
        root, change_id=state.change_id, approval_id=code["approval_id"], base=base, head=head,
        verification_config_digest=code.get("verification_config_digest"),
        knowledge_basis=code.get("knowledge_basis"),
        legacy_paths=code.get("path_representation") != "git-literal/v1",
    )
    if current_code["subject_id"] != code["subject_id"]:
        raise ApprovalError("delivery subject does not match the current complete Git diff")
    boundary = delivery_boundary(root, base=base, head=head)
    result: dict[str, Any] = {"trusted_base": base, "policy_digest": boundary.base.digest,
                              "required_checks_digest": boundary.base_checks["digest"],
                              "mode": "unchanged"}
    if boundary.base.v2 is not None:
        required, reason = boundary.base.v2.review_requirement(code["manifest"])
        result.update({"builtin_version": boundary.base.v2.builtin_checks_version,
                       "code_review_required": required, "code_review_reason": reason})
    if not boundary.changed:
        return result
    approval = validate_approval(state.effective_approval, change_id=state.change_id)
    require_risk_boundary_declaration(approval["subject"], change_id=state.change_id)
    accepted = [event for event in read_change_events(events_file, state.change_id)
                if event.type == ACCEPTANCE_EVENT]
    if not accepted:
        raise ApprovalError(
            "this delivery changes the recognition policy or required checks; the owner must "
            f"record the change with `keepsail policy accept {state.change_id}`")
    latest = accepted[-1]
    require_matching_acceptance(boundary, latest.payload, change_id=state.change_id,
                                plan_subject_id=approval["subject_id"])
    return {**result, "mode": "accepted", "acceptance_event_id": latest.event_id}
