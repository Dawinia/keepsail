"""Read a structurally valid policy snapshot from committed Git objects.

This does not authenticate an activation or grant authority.  The verifier must
also validate the activation chain before treating the snapshot as effective.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keepsail.core.approval import ApprovalError
from keepsail.core.delivery_policy import DeliveryPolicy, parse_delivery_policy_yaml
from keepsail.core.git_objects import regular_blob_text
from keepsail.core.policy_authority import PolicyAuthority, parse_authority_yaml
from keepsail.core.scope_match import GitScopeError, resolve_commit
from keepsail.core.verification_config import (
    parse_verification_config,
    required_check_contract,
)


@dataclass(frozen=True)
class PolicySnapshot:
    commit: str
    policy: DeliveryPolicy
    authority: PolicyAuthority
    checks: dict[str, Any]


def read_policy_snapshot(
    root: Path, commit: str, *, repository_id: str, target_ref: str,
) -> PolicySnapshot:
    """Validate committed contents and independently supplied identity, not activation."""
    try:
        resolved = resolve_commit(root, commit)
    except GitScopeError as exc:
        raise ApprovalError("cannot resolve policy snapshot commit") from exc
    policy = parse_delivery_policy_yaml(
        regular_blob_text(root, resolved, ".harness/review-recognition.yaml")
    )
    authority_text = regular_blob_text(root, resolved, ".harness/policy-authority.yaml")
    authority = parse_authority_yaml(authority_text)
    if (not authority.enabled or authority.repository_id != repository_id
            or authority.target_ref != target_ref):
        raise ApprovalError("policy authority does not match the supplied repository and ref")
    plan_process = policy.recognition_for("plan")
    if (plan_process is not None and "signed-plan-decision" in plan_process.evidence_forms
            and "plan-decision" not in authority.purposes):
        raise ApprovalError("trusted authority lacks the policy's plan-decision purpose")
    config = parse_verification_config(
        regular_blob_text(root, resolved, ".harness/verification.yaml"), strict=True
    )
    checks = required_check_contract(config)
    if checks["digest"] != policy.required_checks_digest:
        raise ApprovalError("required checks digest does not match the committed configuration")
    return PolicySnapshot(resolved, policy, authority, checks)
