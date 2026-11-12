"""Resolve local review evidence against a trusted policy or signed recovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    digest_record,
    evidence_digest,
    evidence_is_recognized,
    load_recognition,
    make_code_subject,
    resolve_contract_base,
    validate_approval,
    validate_code_subject,
    validate_evidence,
)
from keepsail.core.git_objects import regular_blob_text
from keepsail.core.policy_authority import (
    parse_authority_yaml,
    parse_unique_yaml,
    validate_authorization_import,
    verify_recovery_evidence,
    verify_v2_review_evidence,
)
from keepsail.core.review_verdict import read_change_events
from keepsail.core.scope_match import resolve_commit


def recovery_recognition_digest(base_policy_digest: str, authorization_digest: str) -> str:
    return digest_record({"version": "recovery-recognition/v1",
                          "base_policy_digest": base_policy_digest,
                          "authorization_digest": authorization_digest})


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
    """Verify an exact review conclusion; never trust a candidate policy file."""
    if state is None:
        raise ApprovalError("review evidence requires an existing Change")
    evidence = validate_evidence(evidence, change_id=state.change_id)
    base = resolve_contract_base(root)
    if expected_base is not None and expected_base != base:
        raise ApprovalError("trusted recognition baseline changed during review import")
    continuation_error: ApprovalError | None = None
    raw_policy = parse_unique_yaml(
        regular_blob_text(root, base, ".harness/review-recognition.yaml")
    )
    if isinstance(raw_policy, dict) and raw_policy.get("version") == "review-recognition/v2":
        from keepsail.core.effective_policy import continued_plan_basis, load_effective_v2

        snapshot = load_effective_v2(root, base)
        provenance = evidence.get("provenance")
        evidence_policy = provenance.get("policy_digest") if isinstance(provenance, dict) else None
        current_digest = snapshot.policy.policy_digest
        if evidence_policy == current_digest:
            recognition = snapshot.policy.recognition_for(str(evidence["kind"]))
            if recognition is None:
                raise ApprovalError("the active policy does not recognize this review kind")
            verify_v2_review_evidence(
                evidence, recognition, snapshot.authority,
                repository_id=snapshot.authority.repository_id,
                target_ref=snapshot.authority.target_ref, change_id=state.change_id,
            )
            return {"mode": "current", "trusted_base": base, "policy_digest": current_digest}
        if evidence["kind"] == "plan":
            try:
                return continued_plan_basis(root, snapshot, state, evidence)
            except ApprovalError as exc:
                # A distinct, signed recovery may still apply below. Preserve a
                # useful reason for an existing approval if no recovery matches.
                approval = state.effective_approval
                if (isinstance(approval, dict)
                        and approval.get("evidence_id") == evidence.get("evidence_id")):
                    continuation_error = exc
        policy_digest = evidence_policy
    else:
        current = load_recognition(root, ref=base)
        if not current.policy_digest:
            raise ApprovalError("trusted review recognition has no digest")
        current_digest = current.policy_digest
        provenance = evidence.get("provenance")
        policy_digest = provenance.get("policy_digest") if isinstance(provenance, dict) else None
        if policy_digest == current_digest and evidence_is_recognized(evidence, current):
            return {"mode": "current", "trusted_base": base, "policy_digest": current_digest}

    for event in read_change_events(events_file, state.change_id):
        if event.type != "policy_authorization_imported":
            continue
        payload = event.payload
        record = payload.get("authorization")
        authorization_digest = payload.get("authorization_digest")
        if (not isinstance(record, dict) or record.get("kind") != "recovery"
                or not isinstance(authorization_digest, str)):
            continue
        recovery_digest = recovery_recognition_digest(current_digest, authorization_digest)
        if policy_digest != recovery_digest:
            continue
        actual_paths: list[str] | None = None
        if evidence["kind"] == "plan":
            if evidence["subject_id"] != record.get("plan_subject_id"):
                raise ApprovalError("recovery evidence targets another plan")
        else:
            code = validate_code_subject(state.current_code_subject, change_id=state.change_id)
            if evidence["subject_id"] != code["subject_id"]:
                raise ApprovalError("recovery evidence targets another code subject")
            actual = make_code_subject(
                root, change_id=state.change_id, approval_id=code["approval_id"], base=base,
                verification_config_digest=code.get("verification_config_digest"),
                knowledge_basis=code.get("knowledge_basis"),
            )
            if actual["subject_id"] != code["subject_id"]:
                raise ApprovalError("recovery code subject is not the current complete Git diff")
            actual_paths = sorted({path for row in code["manifest"]
                                   for path in (row.get("old_path"), row.get("path"))
                                   if isinstance(path, str)})
        validate_authorization_import(root, state, state.change_id, payload,
                                      for_use=True, actual_paths=actual_paths)
        authority = parse_authority_yaml(
            regular_blob_text(root, base, ".harness/policy-authority.yaml")
        )
        target_authority = authority
        if actual_paths is not None:
            target_authority = parse_authority_yaml(regular_blob_text(
                root, resolve_commit(root), ".harness/policy-authority.yaml"
            ))
        pending = (state.pending_revision.get("subject")
                   if isinstance(state.pending_revision, dict) else None)
        effective = (state.effective_approval.get("subject")
                     if isinstance(state.effective_approval, dict) else None)
        plan = next((item for item in (pending, effective) if isinstance(item, dict)
                     and item.get("subject_id") == record["plan_subject_id"]), None)
        if plan is None:
            raise ApprovalError("recovery plan is no longer available")
        plan_paths = [artifact["path"] for artifact in plan["artifacts"]
                      if artifact.get("role") == "plan"]
        return verify_recovery_evidence(
            evidence, record, authority, repository_id=payload["repository_id"],
            target_ref=payload["target_ref"], base_sha=base,
            base_policy_digest=current_digest,
            target_policy_digest=record["target_policy_digest"], change_id=state.change_id,
            plan_subject_id=record["plan_subject_id"], frozen_plan_paths=plan_paths,
            actual_paths=actual_paths or [], target_authority=target_authority,
        )
    if continuation_error is not None:
        raise ApprovalError(
            f"existing plan approval cannot be continued: {continuation_error}; "
            "obtain an approval recognized by the active policy"
        ) from continuation_error
    raise ApprovalError("review evidence process or policy digest is not user-recognized")
