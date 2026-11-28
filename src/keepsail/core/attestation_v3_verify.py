"""Offline v3 delivery verification against committed Git evidence.

The effective policy and required checks are read directly from the trusted
base commit.  There is no activation-chain replay and no signature check: a
risk-boundary change is verified by recomputing its difference and requiring
the owner's recorded acceptance to match it exactly.  Whether the trusted base
itself passed the gate is the host's branch protection and CI responsibility.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    evidence_is_recognized,
    validate_approval,
    validate_code_subject,
)
from keepsail.core.attestation_format import expand_attestation
from keepsail.core.attestation_replay import (
    _knowledge_attestation,
    _new_contract_blockers,
    check_recognized_attestation,
    derive_independence,
    events_from_stateful_attestation,
    gate_bypass_disclosure,
)
from keepsail.core.attestation_v3 import parse_v3_line, validate_v3
from keepsail.core.completion_transaction import wrap_derived_completion
from keepsail.core.delivery_policy import verify_v2_review_evidence
from keepsail.core.git_diff import DiffEntry, parse_name_status_z
from keepsail.core.git_objects import regular_blob_bytes
from keepsail.core.reducer import derive_state
from keepsail.core.risk_boundary import (
    RiskBoundary,
    require_matching_acceptance,
    require_risk_boundary_declaration,
    validate_authorization_record,
)
from keepsail.core.scope_match import resolve_commit
from keepsail.core.transition_guard import delivery_boundary
from keepsail.core.verification_evidence import verify_check_evidence


def _require_current_bases(record: dict[str, Any]) -> None:
    for kind in ("plan", "code"):
        basis = record["recognition_basis"][kind]
        if basis is not None and basis["mode"] != "current":
            raise ApprovalError(
                f"{kind} recognition basis {basis['mode']!r} is retained only for historical "
                "attestations; new deliveries must use the effective policy")


def _diff_entries(root: Path, base_sha: str, head_sha: str) -> list[DiffEntry]:
    try:
        raw_diff = subprocess.check_output(
            ["git", "diff", "--name-status", "-z", "--find-renames", f"{base_sha}...{head_sha}"],
            cwd=root,
        ).decode("utf-8")
        return parse_name_status_z(raw_diff)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError, ValueError) as exc:
        raise ApprovalError(f"cannot inspect v3 Git diff: {exc}") from exc


def _require_committed_record(root: Path, record: dict[str, Any], entries: list[DiffEntry],
                              head_sha: str) -> None:
    path = f".harness/attestations/v3/{record['change_id']}.jsonl"
    if not any(entry.status == "A" and entry.paths == (path,) for entry in entries):
        raise ApprovalError("v3 attestation must be newly added in the exact diff")
    if parse_v3_line(regular_blob_bytes(root, head_sha, path)) != record:
        raise ApprovalError("v3 attestation does not match the committed Git blob")


def _verify_authorization(record: dict[str, Any], approval: dict[str, Any],
                          boundary: RiskBoundary) -> dict[str, Any] | None:
    authorization = record["authorization"]
    change = record["change_id"]
    if not boundary.changed:
        if authorization is not None:
            raise ApprovalError("ordinary delivery changes no obligations but carries an "
                                "authorization")
        return None
    if authorization is None:
        raise ApprovalError("this delivery changes the recognition policy or required checks "
                            "and needs the owner's recorded policy acceptance")
    validate_authorization_record(authorization)
    require_risk_boundary_declaration(approval["subject"], change_id=change)
    require_matching_acceptance(boundary, authorization["acceptance"], change_id=change,
                                plan_subject_id=approval["subject_id"])
    return {"event_id": authorization["event_id"], "actor": authorization["actor"],
            "ts": authorization["ts"], "labels": boundary.labels,
            "obligation_changes": boundary.differences,
            "target_policy_digest": boundary.target.digest,
            "target_policy_state": boundary.target.state}


def _lifecycle_checks(
    root: Path, record: dict[str, Any], entries: list[DiffEntry], *, base_sha: str,
    head_sha: str, code: dict[str, Any], plan_recognition: Any, verify_review: Any,
    required_contract: dict[str, Any], builtin_version: str,
    code_review_required: bool | None,
) -> tuple[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    change = record["change_id"]
    lines = expand_attestation(record["snapshot"], for_v3=True)
    with tempfile.TemporaryDirectory(prefix="keepsail-v3-delivery-") as temp:
        replay_path = Path(temp) / "lifecycle.jsonl"
        replay_path.write_text("\n".join(wrap_derived_completion(lines)) + "\n",
                               encoding="utf-8", newline="\n")
        state = derive_state(replay_path).get(change)
        if state is None:
            raise ApprovalError("v3 lifecycle has no matching Change")
        if code_review_required is None:
            blockers = check_recognized_attestation(replay_path, change)
            extra: dict[str, Any] = {}
        else:
            blockers = check_recognized_attestation(
                replay_path, change, builtin_version=builtin_version,
                repository_root=root, code_review_required=code_review_required,
            )
            extra = {"code_review_required": code_review_required}
        blockers.extend(_new_contract_blockers(
            root, state, change, entries, recognition=plan_recognition, base=base_sha,
            head=head_sha, attestation_path=replay_path, evidence_validator=verify_review,
            **extra,
        ))
        _knowledge_attestation(root, replay_path, state, base=base_sha, head=head_sha)
        events = events_from_stateful_attestation(root, change, path=replay_path)
        disclosure = gate_bypass_disclosure(events)
        independence = derive_independence(events)
        if disclosure["undisclosed"]:
            blockers.append("gate bypass lacks its required disclosure")
        for kind in ("plan_review", "code_review"):
            if independence[kind]["skipped"] and not independence[kind]["override"]:
                blockers.append(f"{kind} was skipped without the required override")
        checks_summary = verify_check_evidence(
            state.current_verification, subject_id=code["subject_id"],
            required_contract=required_contract, builtin_version=builtin_version,
            trusted_base=base_sha,
        )
        if blockers:
            raise ApprovalError("; ".join(blockers))
    return state, checks_summary, independence, disclosure


def verify_v3_transition(
    root: Path, value: object, *, base: str, head: str, **_identity: str | None,
) -> dict[str, Any]:
    """Verify a risk-boundary delivery from an enabled v1 base under v1 obligations.

    Identity keywords (repository id, target ref) from older callers are
    ignored: nothing here compares identities or signatures.
    """
    record = validate_v3(value)
    base_sha, head_sha = resolve_commit(root, base), resolve_commit(root, head)
    if record["trusted_base"] != base_sha:
        raise ApprovalError("v3 attestation is bound to a different trusted base")
    boundary = delivery_boundary(root, base=base_sha, head=head_sha)
    recognition = boundary.base.v1
    if recognition is None or not recognition.policy_digest:
        raise ApprovalError("v3 transition verification requires an enabled v1 trusted base")
    if record["policy_digest"] != recognition.policy_digest:
        raise ApprovalError("v3 attestation is bound to a different trusted policy")
    _require_current_bases(record)
    change = record["change_id"]
    snapshot = record["snapshot"]
    approval = validate_approval(snapshot.get("approval"), change_id=change)
    code = validate_code_subject(snapshot.get("code_subject"), change_id=change)
    entries = _diff_entries(root, base_sha, head_sha)
    _require_committed_record(root, record, entries, head_sha)
    if not boundary.changed:
        raise ApprovalError("v3 under a v1 policy is only for a risk-boundary change")
    authorization = _verify_authorization(record, approval, boundary)
    old_checks = boundary.base_checks

    def verify_review(evidence: dict[str, Any], kind: str) -> None:
        basis = record["recognition_basis"][kind]
        if not isinstance(basis, dict):
            raise ApprovalError(f"missing {kind} recognition basis")
        provenance = evidence.get("provenance")
        if (basis["mode"] != "current" or not evidence_is_recognized(evidence, recognition)
                or not isinstance(provenance, dict)
                or provenance.get("policy_digest") != recognition.policy_digest):
            raise ApprovalError("review does not match the trusted old recognition")

    state, checks_summary, independence, disclosure = _lifecycle_checks(
        root, record, entries, base_sha=base_sha, head_sha=head_sha, code=code,
        plan_recognition=recognition, verify_review=verify_review,
        required_contract=old_checks, builtin_version="keepsail-baseline/v1",
        code_review_required=None,
    )
    return {"change": change, "trusted_base": base_sha, "head": head_sha,
            "policy_digest": recognition.policy_digest,
            "target_policy_digest": boundary.target.digest,
            "required_checks_digest": old_checks["digest"],
            "required_checks": [{"source": item["source"], "id": item["id"]}
                                for item in old_checks["checks"]],
            **checks_summary,
            "builtin_checks_version": "keepsail-baseline/v1",
            "code_review_required": True,
            "code_review_reason": "trusted v1 policy requires code review for this delivery",
            "coverage": [row["path"] for row in state.coverage_manifest],
            "risk_boundary": authorization,
            "independence": independence, "gate_bypass": disclosure}


def verify_v3_delivery(
    root: Path, value: object, *, base: str, head: str, **_identity: str | None,
) -> dict[str, Any]:
    """Verify a delivery under the enabled v2 base's obligations, read directly."""
    record = validate_v3(value)
    base_sha, head_sha = resolve_commit(root, base), resolve_commit(root, head)
    boundary = delivery_boundary(root, base=base_sha, head=head_sha)
    policy = boundary.base.v2
    if policy is None:
        raise ApprovalError("v3 delivery verification requires an enabled v2 trusted base")
    if record["trusted_base"] != base_sha or record["policy_digest"] != policy.policy_digest:
        raise ApprovalError("delivery does not use the active trusted policy")
    _require_current_bases(record)
    change = record["change_id"]
    code = validate_code_subject(record["snapshot"].get("code_subject"), change_id=change)
    approval = validate_approval(record["snapshot"].get("approval"), change_id=change)
    authorization = _verify_authorization(record, approval, boundary)
    required, reason = policy.review_requirement(code["manifest"])
    if (record["recognition_basis"]["code"] is None) != (not required):
        raise ApprovalError("v3 code recognition basis disagrees with the active policy")
    entries = _diff_entries(root, base_sha, head_sha)
    _require_committed_record(root, record, entries, head_sha)
    plan_recognition = policy.recognition_for("plan")
    if plan_recognition is None:
        raise ApprovalError("active policy has no plan review process")

    def verify_review(evidence: dict[str, Any], kind: str) -> None:
        claimed = record["recognition_basis"][kind]
        if not isinstance(claimed, dict):
            raise ApprovalError(f"missing {kind} recognition basis")
        recognition = policy.recognition_for(kind)
        if claimed["mode"] != "current" or recognition is None:
            raise ApprovalError("review is not recognized by the active policy")
        verify_v2_review_evidence(evidence, recognition, change_id=change)

    state, checks_summary, independence, disclosure = _lifecycle_checks(
        root, record, entries, base_sha=base_sha, head_sha=head_sha, code=code,
        plan_recognition=plan_recognition, verify_review=verify_review,
        required_contract=boundary.base_checks,
        builtin_version=policy.builtin_checks_version, code_review_required=required,
    )
    return {"change": change, "trusted_base": base_sha, "head": head_sha,
            "policy_digest": policy.policy_digest,
            "target_policy_digest": boundary.target.digest,
            "required_checks_digest": boundary.base_checks["digest"],
            "required_checks": [{"source": item["source"], "id": item["id"]}
                                for item in boundary.base_checks["checks"]],
            **checks_summary,
            "builtin_checks_version": policy.builtin_checks_version,
            "code_review_required": required, "code_review_reason": reason,
            "coverage": [row["path"] for row in state.coverage_manifest],
            "risk_boundary": authorization,
            "independence": independence, "gate_bypass": disclosure}
