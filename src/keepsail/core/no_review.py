"""Verify a no-review decision against its historical policy and Git subject."""

from __future__ import annotations

from pathlib import Path

from keepsail.core.approval import ApprovalError, make_code_subject, validate_code_subject
from keepsail.core.effective_policy import load_effective_v2
from keepsail.core.events import Event


def verify_no_review_binding(root: Path, event: Event, subject: object) -> None:
    payload = event.payload
    if set(payload) != {"subject_id", "trusted_base", "policy_digest", "reason"}:
        raise ApprovalError("no-review decision has invalid policy bindings")
    base = payload.get("trusted_base")
    if not isinstance(base, str) or not base:
        raise ApprovalError("no-review decision lacks its trusted base")
    snapshot = load_effective_v2(root, base)
    if (snapshot.commit != base or snapshot.policy.policy_digest != payload.get("policy_digest")
            or snapshot.policy.builtin_checks_version != "keepsail-baseline/v2"):
        raise ApprovalError("no-review decision is not bound to an eligible trusted policy")
    code = validate_code_subject(subject, change_id=event.change_id)
    if payload.get("subject_id") != code["subject_id"]:
        raise ApprovalError("no-review decision is for another code subject")
    from keepsail.core.git_diff import require_literal_git_diff

    require_literal_git_diff(root, base=base, head=code["head"])
    actual = make_code_subject(
        root, change_id=event.change_id, approval_id=code["approval_id"], base=base,
        head=code["head"], verification_config_digest=code.get("verification_config_digest"),
        knowledge_basis=code.get("knowledge_basis"),
    )
    if actual["subject_id"] != code["subject_id"]:
        raise ApprovalError("no-review decision is not bound to the complete Git change")
    required, reason = snapshot.policy.review_requirement(code["manifest"])
    if required or payload.get("reason") != reason:
        raise ApprovalError("active policy does not permit this no-review decision")
