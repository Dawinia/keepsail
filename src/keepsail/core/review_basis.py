"""Resolve local review evidence against the trusted committed policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    _recognition_from_mapping,
    evidence_digest,
    evidence_is_recognized,
    resolve_contract_base,
    validate_approval,
    validate_evidence,
)
from keepsail.core.delivery_policy import verify_v2_review_evidence
from keepsail.core.git_objects import regular_blob_text
from keepsail.core.strict_yaml import parse_unique_yaml

APPROVAL_PROCESS_RETIRED = (
    "the process this approval relied on is no longer in the effective policy; obtain a "
    "plan approval recognized by the effective policy"
)


def validate_effective_plan_basis(root: Path, events_file: Path, state: Any) -> dict[str, str]:
    """Re-evaluate the active plan approval when the trusted target may have moved."""
    if state is None:
        raise ApprovalError("an effective plan approval is required")
    approval = validate_approval(state.effective_approval, change_id=state.change_id)
    evidence = next((item for item in state.evidence_references
                     if item.get("evidence_id") == approval["evidence_id"]), None)
    if (not isinstance(evidence, dict) or evidence.get("kind") != "plan"
            or evidence.get("decision") != "approve"
            or evidence.get("subject_id") != approval["subject_id"]
            or evidence_digest(evidence) != approval["evidence_digest"]):
        raise ApprovalError("effective plan approval lacks its exact review evidence")
    return resolve_local_review_basis(root, events_file, state, evidence)


def resolve_local_review_basis(
    root: Path, events_file: Path, state: Any, evidence: dict[str, Any], *,
    expected_base: str | None = None,
) -> dict[str, str]:
    """Verify an exact review conclusion; never trust a candidate policy file.

    ``events_file`` is kept for callers; review recognition no longer reads the
    ledger (there is no recovery or continued-plan basis).
    """
    del events_file
    if state is None:
        raise ApprovalError("review evidence requires an existing Change")
    evidence = validate_evidence(evidence, change_id=state.change_id)
    base = resolve_contract_base(root)
    if expected_base is not None and expected_base != base:
        raise ApprovalError("trusted recognition baseline changed during review import")
    approval = state.effective_approval
    is_effective = (isinstance(approval, dict)
                    and approval.get("evidence_id") == evidence.get("evidence_id"))
    raw_policy = parse_unique_yaml(
        regular_blob_text(root, base, ".harness/review-recognition.yaml")
    )
    provenance = evidence.get("provenance")
    evidence_policy = provenance.get("policy_digest") if isinstance(provenance, dict) else None
    if isinstance(raw_policy, dict) and raw_policy.get("version") == "review-recognition/v2":
        from keepsail.core.effective_policy import load_effective_v2

        snapshot = load_effective_v2(root, base)
        current_digest = snapshot.policy.policy_digest
        recognition = snapshot.policy.recognition_for(str(evidence["kind"]))
        if evidence_policy == current_digest:
            if recognition is None:
                raise ApprovalError("the active policy does not recognize this review kind")
            verify_v2_review_evidence(evidence, recognition, change_id=state.change_id)
            return {"mode": "current", "trusted_base": base, "policy_digest": current_digest}
    else:
        current = _recognition_from_mapping(raw_policy)
        if not current.policy_digest:
            raise ApprovalError("trusted review recognition has no digest")
        if evidence_policy == current.policy_digest and evidence_is_recognized(evidence, current):
            return {"mode": "current", "trusted_base": base,
                    "policy_digest": current.policy_digest}
    if is_effective:
        raise ApprovalError(APPROVAL_PROCESS_RETIRED)
    raise ApprovalError("review evidence process or policy digest is not user-recognized")
