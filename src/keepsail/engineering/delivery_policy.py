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
from keepsail.core.git_diff import require_literal_git_diff
from keepsail.core.git_objects import optional_regular_blob_text
from keepsail.core.policy_authority import parse_unique_yaml
from keepsail.core.policy_snapshot import PolicySnapshot as PolicySnapshot
from keepsail.core.policy_snapshot import read_policy_snapshot as read_policy_snapshot
from keepsail.core.scope_match import GitScopeError


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
        require_literal_git_diff(root, base=base, head="HEAD")
        current = make_code_subject(
            root, change_id=state.change_id, approval_id=subject["approval_id"], base=base,
            verification_config_digest=subject.get("verification_config_digest"),
            knowledge_basis=subject.get("knowledge_basis"),
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
