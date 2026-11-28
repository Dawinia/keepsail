"""Read a structurally valid policy snapshot from committed Git objects.

The snapshot read from the trusted baseline commit is the effective policy.
Whether that commit reached the target branch through the gate is the host's
branch protection and CI responsibility, not something replayed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keepsail.core.approval import ApprovalError
from keepsail.core.delivery_policy import DeliveryPolicy, parse_delivery_policy_yaml
from keepsail.core.git_objects import regular_blob_text
from keepsail.core.scope_match import GitScopeError, resolve_commit
from keepsail.core.verification_config import (
    parse_verification_config,
    required_check_contract,
)


@dataclass(frozen=True)
class PolicySnapshot:
    commit: str
    policy: DeliveryPolicy
    checks: dict[str, Any]


def read_policy_snapshot(root: Path, commit: str) -> PolicySnapshot:
    """Validate the committed policy and that its checks digest matches the committed config."""
    try:
        resolved = resolve_commit(root, commit)
    except GitScopeError as exc:
        raise ApprovalError("cannot resolve policy snapshot commit") from exc
    policy = parse_delivery_policy_yaml(
        regular_blob_text(root, resolved, ".harness/review-recognition.yaml")
    )
    config = parse_verification_config(
        regular_blob_text(root, resolved, ".harness/verification.yaml"), strict=True
    )
    checks = required_check_contract(config)
    if checks["digest"] != policy.required_checks_digest:
        raise ApprovalError("required checks digest does not match the committed configuration")
    return PolicySnapshot(resolved, policy, checks)
