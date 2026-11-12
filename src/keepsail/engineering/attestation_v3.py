"""Produce and verify v3 transition attestations against committed v1 trust."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    resolve_contract_base,
)
from keepsail.core.attestation_format import (
    inactive_knowledge_checkpoint,
    make_attestation,
)
from keepsail.core.attestation_v3 import make_v3
from keepsail.core.attestation_v3_verify import verify_v2_activation as verify_v2_activation
from keepsail.core.attestation_v3_verify import verify_v3_transition as verify_v3_transition
from keepsail.core.context import _approval_lineage
from keepsail.core.git_objects import regular_blob_text
from keepsail.core.knowledge import read_inputs
from keepsail.core.knowledge_checkpoint import make_checkpoint
from keepsail.core.review_basis import resolve_local_review_basis
from keepsail.core.review_verdict import read_change_events
from keepsail.core.transition_guard import validate_delivery_obligations
from keepsail.core.verification_config import parse_verification_config, required_check_contract
from keepsail.core.verification_evidence import verify_check_evidence


def build_v3_attestation(root: Path, events_file: Path, change: str) -> dict[str, Any]:
    """Freeze existing evidence; creating a record does not activate its policy."""
    inputs = read_inputs(root, events_file=events_file)
    state = inputs.states.get(change)
    if state is None or state.current_state != "READY_TO_MERGE":
        raise ApprovalError("v3 attestation requires a completed Change")
    approval = state.effective_approval
    code = state.current_code_subject
    if not isinstance(approval, dict) or not isinstance(code, dict):
        raise ApprovalError("v3 attestation requires current plan and code subjects")
    base = resolve_contract_base(root)
    basis = validate_delivery_obligations(root, events_file, state, code)
    policy_digest = basis["policy_digest"]
    config = parse_verification_config(regular_blob_text(root, base, ".harness/verification.yaml"))
    verify_check_evidence(state.current_verification, subject_id=code["subject_id"],
                          required_contract=required_check_contract(config),
                          builtin_version=basis.get("builtin_version", "keepsail-baseline/v1"),
                          trusted_base=base)
    evidence = {item["evidence_id"]: item for item in state.evidence_references}
    plan_evidence = evidence.get(approval["evidence_id"])
    events = read_change_events(events_file, change)
    if not isinstance(plan_evidence, dict):
        raise ApprovalError("v3 attestation needs retained plan review evidence")
    plan_basis = resolve_local_review_basis(root, events_file, state, plan_evidence,
                                            expected_base=base)
    code_basis = None
    if basis.get("code_review_required", True):
        review = next((event for event in reversed(events) if event.type == "code_review_passed"
                       and event.payload.get("code_subject", {}).get("subject_id")
                       == code["subject_id"]), None)
        code_evidence = evidence.get(review.payload.get("evidence_id")) if review else None
        if not isinstance(code_evidence, dict):
            raise ApprovalError("v3 attestation needs retained code review evidence")
        code_basis = resolve_local_review_basis(root, events_file, state, code_evidence,
                                                expected_base=base)
    else:
        from keepsail.core.no_review import verify_no_review_binding

        no_review = next((event for event in reversed(events)
                          if event.type == "code_review_not_required"
                          and event.payload.get("subject_id") == code["subject_id"]), None)
        if no_review is None or no_review.payload.get("trusted_base") != base:
            raise ApprovalError("v3 attestation lacks the current no-review decision")
        verify_no_review_binding(root, no_review, code)
    authorization = None
    if basis["mode"] != "unchanged":
        imported = next((event for event in reversed(events)
                         if event.type == "policy_authorization_imported"
                         and event.payload.get("authorization_digest")
                         == basis.get("authorization_digest")), None)
        if imported is None:
            raise ApprovalError("v3 transition authorization is not retained")
        authorization = imported.payload["authorization"]
    checkpoint = (make_checkpoint(root, change, inputs, base) if inputs.policy is not None
                  else inactive_knowledge_checkpoint())
    lineage = _approval_lineage(root, change, approval, lines=inputs.effective_lines,
                                effective=True)
    snapshot = make_attestation(change, inputs, checkpoint, lineage, for_v3=True)
    bases = {"plan": {k: v for k, v in plan_basis.items() if k != "trusted_base"},
             "code": ({k: v for k, v in code_basis.items() if k != "trusted_base"}
                      if code_basis is not None else None)}
    return make_v3(change_id=change, trusted_base=base, policy_digest=policy_digest,
                   recognition_basis=bases, authorization=authorization, snapshot=snapshot)
