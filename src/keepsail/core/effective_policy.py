"""Resolve the effective delivery policy from the local trusted Git base."""

from __future__ import annotations

from pathlib import Path

from keepsail.core.delivery_policy import reject_signed_plan_policy
from keepsail.core.policy_snapshot import PolicySnapshot, read_policy_snapshot
from keepsail.core.scope_match import resolve_commit


def load_effective_v2(root: Path, base: str) -> PolicySnapshot:
    """Read the committed v2 policy at the trusted base; its cost is constant per call."""
    snapshot = read_policy_snapshot(root, resolve_commit(root, base))
    reject_signed_plan_policy(snapshot.policy)
    return snapshot
