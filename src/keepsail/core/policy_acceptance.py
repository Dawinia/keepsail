"""Recompute the exact ``policy_change_accepted`` payload for one Change.

The owner's acceptance binds the Change's *effective* plan approval and the
recomputed risk-boundary difference between the trusted base and the
committed ``HEAD``.  It deliberately binds no base SHA or HEAD, so rebases and
code fixes keep it valid; a changed target policy, check definition, obligation
difference or approved plan invalidates it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    has_unresolved_candidate,
    resolve_contract_base,
    validate_approval,
)
from keepsail.core.risk_boundary import (
    RiskBoundary,
    compare_risk_boundary,
    require_risk_boundary_declaration,
    validate_acceptance_payload,
)
from keepsail.core.scope_match import resolve_commit


def expected_acceptance(root: Path, state: Any) -> tuple[RiskBoundary, dict[str, Any]]:
    if state is None:
        raise ApprovalError("policy accept requires an existing Change")
    base = resolve_contract_base(root)
    head = resolve_commit(root)
    # The trusted policy is checked first: a signed-plan base is refused with its
    # migration guidance before any Change-specific condition.
    boundary = compare_risk_boundary(root, base=base, head=head)
    if has_unresolved_candidate(state) or state.current_state in {
        "AWAITING_PLAN_REVIEW", "PLAN_REJECTED",
    }:
        raise ApprovalError("the plan has a pending or rejected revision; policy accept binds "
                            "only an effective plan approval")
    if not isinstance(state.effective_approval, dict):
        raise ApprovalError("policy accept requires an effective plan approval")
    approval = validate_approval(state.effective_approval, change_id=state.change_id)
    if boundary is None:
        raise ApprovalError("the trusted base has no enabled policy; the first enabled policy is "
                            "adoption (`keepsail init` or `keepsail policy enable`), not a "
                            "policy accept")
    if not boundary.changed:
        raise ApprovalError("the committed HEAD changes neither the recognition policy nor the "
                            "required checks; there is nothing to accept")
    require_risk_boundary_declaration(approval["subject"], change_id=state.change_id)
    return boundary, boundary.acceptance(change_id=state.change_id,
                                         plan_subject_id=approval["subject_id"])


def validate_new_acceptance(root: Path, state: Any, payload: object) -> None:
    _, expected = expected_acceptance(root, state)
    if validate_acceptance_payload(payload) != expected:
        raise ApprovalError("policy acceptance does not match the recomputed change")
