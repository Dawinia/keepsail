"""Resolve an activated delivery policy from the local trusted Git base."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    digest_record,
    evidence_digest,
    evidence_is_recognized,
    load_recognition,
    validate_approval,
)
from keepsail.core.attestation_v3 import parse_v3_line
from keepsail.core.attestation_v3_verify import verify_v2_activation
from keepsail.core.git_objects import regular_blob_bytes, regular_blob_text
from keepsail.core.policy_authority import (
    parse_authority_yaml,
    parse_unique_yaml,
    verify_v2_review_evidence,
)
from keepsail.core.policy_snapshot import PolicySnapshot, read_policy_snapshot
from keepsail.core.scope_match import resolve_commit


def load_effective_v2(root: Path, base: str) -> PolicySnapshot:
    """Replay activation before using v2; local identity is not host authentication."""
    commit = resolve_commit(root, base)
    authority = parse_authority_yaml(
        regular_blob_text(root, commit, ".harness/policy-authority.yaml")
    )
    verify_v2_activation(root, trusted_commit=commit, repository_id=authority.repository_id,
                         target_ref=authority.target_ref)
    return read_policy_snapshot(root, commit, repository_id=authority.repository_id,
                                target_ref=authority.target_ref)


def continued_plan_basis(
    root: Path, snapshot: PolicySnapshot, state: Any, evidence: dict[str, Any],
) -> dict[str, str]:
    """Retain only an exact approval explicitly listed by the activated transition."""
    if evidence.get("kind") != "plan" or state is None:
        raise ApprovalError("only an existing plan approval can be continued")
    approval = validate_approval(state.effective_approval, change_id=state.change_id)
    activation = snapshot.policy.activation
    if activation.get("kind") != "transition":
        raise ApprovalError("continued plan requires an activated transition")
    path = f".harness/attestations/v3/{activation['change']}.jsonl"
    record = parse_v3_line(regular_blob_bytes(root, snapshot.commit, path))
    authorization = record["authorization"]
    if not isinstance(authorization, dict):
        raise ApprovalError("activation has no signed continuation list")
    provenance = evidence.get("provenance")
    predecessor_digest = provenance.get("policy_digest") if isinstance(provenance, dict) else None
    expected = {"change_id": state.change_id, "subject_id": approval["subject_id"],
                "approval_id": approval["approval_id"],
                "evidence_digest": evidence_digest(evidence),
                "predecessor_policy_digest": predecessor_digest}
    if (approval["evidence_id"] != evidence.get("evidence_id")
            or approval["evidence_digest"] != expected["evidence_digest"]
            or evidence.get("subject_id") != expected["subject_id"]
            or evidence.get("decision") != "approve"
            or expected not in authorization.get("continued_plans", [])):
        raise ApprovalError("plan approval is not in the exact signed continuation list")
    prior_base = record["trusted_base"]
    prior_raw = parse_unique_yaml(regular_blob_text(root, prior_base,
                                                     ".harness/review-recognition.yaml"))
    if isinstance(prior_raw, dict) and prior_raw.get("version") == "review-recognition/v2":
        prior = load_effective_v2(root, prior_base)
        predecessor = prior.policy.recognition_for("plan")
        if predecessor is None or predecessor.policy_digest != predecessor_digest:
            raise ApprovalError("continued plan predecessor policy does not match")
        verify_v2_review_evidence(evidence, predecessor, prior.authority,
                                  repository_id=prior.authority.repository_id,
                                  target_ref=prior.authority.target_ref, change_id=state.change_id)
    else:
        predecessor = load_recognition(root, ref=prior_base)
        if (predecessor.policy_digest != predecessor_digest
                or not evidence_is_recognized(evidence, predecessor)):
            raise ApprovalError("continued plan evidence does not match its predecessor policy")
    assert isinstance(predecessor_digest, str)
    return {"mode": "continued_plan", "trusted_base": snapshot.commit,
            "policy_digest": predecessor_digest,
            "authorization_digest": digest_record(authorization)}
