"""Guard committed deliveries against weakening trusted obligations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    _recognition_from_mapping,
    load_recognition,
    make_code_subject,
    resolve_contract_base,
    validate_code_subject,
)
from keepsail.core.delivery_policy import parse_delivery_policy
from keepsail.core.git_diff import require_literal_git_diff
from keepsail.core.git_objects import optional_regular_blob_text, regular_blob_text
from keepsail.core.policy_authority import (
    parse_authority_yaml,
    parse_unique_yaml,
    validate_authorization_import,
)
from keepsail.core.policy_obligations import (
    changed_obligations,
    changed_required_checks,
    require_signed_obligation_changes,
)
from keepsail.core.review_verdict import read_change_events
from keepsail.core.scope_match import resolve_commit
from keepsail.core.verification_config import parse_verification_config, required_check_contract

_POLICY = ".harness/review-recognition.yaml"
_AUTHORITY = ".harness/policy-authority.yaml"
_VERIFICATION = ".harness/verification.yaml"


def committed_transition_required(
    root: Path, *, base: str, head: str, changed_paths: set[str],
) -> bool:
    """Detect changes that cannot be authorized by a legacy attestation alone."""
    if not changed_paths.intersection({_POLICY, _AUTHORITY, _VERIFICATION}):
        return False
    old_text = optional_regular_blob_text(root, base, _POLICY)
    old_raw = parse_unique_yaml(old_text) if old_text is not None else None
    if not isinstance(old_raw, dict) or old_raw.get("enabled") is not True:
        if _POLICY in changed_paths:
            proposed = parse_unique_yaml(regular_blob_text(root, head, _POLICY))
            if isinstance(proposed, dict) and proposed.get("version") == "review-recognition/v2":
                raise ApprovalError("initial v2 trust needs separate owner establishment")
        return False
    if old_raw.get("version") == "review-recognition/v2":
        # The v3 verifier checks the entire candidate policy, authority and check
        # contract against this exact base and head, including any authorization.
        # Require it for every change to those files rather than applying v1 rules.
        return True
    if old_raw.get("version") != "review-recognition/v1":
        raise ApprovalError("unsupported active review policy")
    old = _recognition_from_mapping(old_raw)
    required = False
    if _POLICY in changed_paths:
        candidate = parse_unique_yaml(regular_blob_text(root, head, _POLICY))
        if not isinstance(candidate, dict):
            raise ApprovalError("candidate review policy is invalid")
        if candidate.get("version") == "review-recognition/v1":
            if _recognition_from_mapping(candidate).policy_digest != old.policy_digest:
                raise ApprovalError("legacy policy changes require an authorized v2 transition")
        else:
            parse_delivery_policy(candidate)
            required = True
    if _VERIFICATION in changed_paths:
        old_checks = required_check_contract(parse_verification_config(
            regular_blob_text(root, base, _VERIFICATION)))
        new_checks = required_check_contract(parse_verification_config(
            regular_blob_text(root, head, _VERIFICATION), strict=True))
        required = bool(changed_required_checks(old_checks, new_checks)) or required
    if _AUTHORITY in changed_paths:
        before = optional_regular_blob_text(root, base, _AUTHORITY)
        after = optional_regular_blob_text(root, head, _AUTHORITY)
        if after is None:
            raise ApprovalError("candidate removed policy authority")
        new_authority = parse_authority_yaml(after)
        if before is None:
            if new_authority.enabled:
                raise ApprovalError("initial enabled trust needs separate owner establishment")
        else:
            old_authority = parse_authority_yaml(before)
            if not old_authority.enabled and new_authority.enabled:
                raise ApprovalError("initial enabled trust needs separate owner establishment")
            required = old_authority.digest != new_authority.digest or required
    return required


def validate_delivery_obligations(
    root: Path, events_file: Path, state: Any, subject: object,
) -> dict[str, Any]:
    """Recompute trusted and candidate obligations before accepting completion.

    An active v2 baseline is first checked through its activation chain.
    """
    if state is None or not isinstance(state.effective_approval, dict):
        raise ApprovalError("delivery requires an effective plan approval")
    code = validate_code_subject(subject, change_id=state.change_id)
    base = resolve_contract_base(root)
    head = resolve_commit(root)
    require_literal_git_diff(root, base=base, head=head)
    current_code = make_code_subject(
        root, change_id=state.change_id, approval_id=code["approval_id"], base=base, head=head,
        verification_config_digest=code.get("verification_config_digest"),
        knowledge_basis=code.get("knowledge_basis"),
    )
    if current_code["subject_id"] != code["subject_id"]:
        raise ApprovalError("delivery subject does not match the current complete Git diff")
    paths = sorted({path for row in code["manifest"]
                    for path in (row.get("old_path"), row.get("path")) if isinstance(path, str)})
    trusted_policy = parse_unique_yaml(regular_blob_text(root, base, _POLICY))
    if (isinstance(trusted_policy, dict)
            and trusted_policy.get("version") == "review-recognition/v2"):
        from keepsail.core.effective_policy import load_effective_v2

        snapshot = load_effective_v2(root, base)
        candidate_policy = parse_delivery_policy(
            parse_unique_yaml(regular_blob_text(root, head, _POLICY))
        )
        candidate_authority = parse_authority_yaml(regular_blob_text(root, head, _AUTHORITY))
        config = parse_verification_config(
            regular_blob_text(root, head, _VERIFICATION), strict=True
        )
        checks = required_check_contract(config)
        if checks["digest"] != candidate_policy.required_checks_digest:
            raise ApprovalError("candidate required checks differ from the target policy")
        policy_changed = candidate_policy.policy_digest != snapshot.policy.policy_digest
        authority_changed = candidate_authority.digest != snapshot.authority.digest
        checks_changed = checks["digest"] != snapshot.checks["digest"]
        if authority_changed and (policy_changed or checks_changed):
            raise ApprovalError("key rotation must be a separate authority-only transition")
        if policy_changed and candidate_policy.activation != {
            "kind": "transition", "change": state.change_id
        }:
            raise ApprovalError("target policy does not identify this transition")
        if checks_changed and not policy_changed:
            raise ApprovalError("required check changes require an authorized policy transition")
        required, reason = snapshot.policy.review_requirement(code["manifest"])
        result = {"trusted_base": base, "policy_digest": snapshot.policy.policy_digest,
                  "required_checks_digest": snapshot.checks["digest"], "mode": "unchanged",
                  "builtin_version": snapshot.policy.builtin_checks_version,
                  "code_review_required": required, "code_review_reason": reason}
        if not policy_changed and not authority_changed:
            return result
        allowed_kinds = {"rotate_key"} if authority_changed else {"transition", "recovery"}
        for event in reversed(read_change_events(events_file, state.change_id)):
            if event.type != "policy_authorization_imported":
                continue
            record = event.payload.get("authorization")
            if not isinstance(record, dict) or record.get("kind") not in allowed_kinds:
                continue
            try:
                validate_authorization_import(root, state, state.change_id, event.payload,
                                              for_use=True, actual_paths=paths)
                if policy_changed:
                    old_processes = {kind: process for kind in ("plan", "code")
                                     if (process := snapshot.policy.recognition_for(kind))}
                    changes = changed_obligations(
                        old_processes=old_processes, old_code_review=snapshot.policy.code_review,
                        old_scope=snapshot.policy.scope,
                        old_builtin=snapshot.policy.builtin_checks_version,
                        old_checks=snapshot.checks, new_policy=candidate_policy, new_checks=checks,
                    )
                    require_signed_obligation_changes(changes, record)
                elif record.get("obligation_changes", []):
                    raise ApprovalError("key rotation cannot alter delivery obligations")
            except (ApprovalError, ValueError, KeyError, TypeError):
                continue
            return {**result, "mode": record["kind"],
                    "authorization_digest": event.payload["authorization_digest"]}
        raise ApprovalError("v2 obligation changes lack matching signed authorization")
    old_recognition = load_recognition(root, ref=base)
    if not old_recognition.policy_digest:
        raise ApprovalError("trusted review policy lacks a digest")
    old_config = parse_verification_config(regular_blob_text(root, base, _VERIFICATION))
    new_text = regular_blob_text(root, head, _VERIFICATION)
    new_config = parse_verification_config(new_text, strict=True)
    old_checks = required_check_contract(old_config)
    new_checks = required_check_contract(new_config)
    check_changes = changed_required_checks(old_checks, new_checks)
    candidate_raw = parse_unique_yaml(regular_blob_text(root, head, _POLICY))
    if not isinstance(candidate_raw, dict):
        raise ApprovalError("candidate review policy is invalid")
    candidate_version = candidate_raw.get("version")
    candidate_v2 = None
    if candidate_version == "review-recognition/v1":
        candidate = _recognition_from_mapping(candidate_raw)
        policy_changed = candidate.policy_digest != old_recognition.policy_digest
    elif candidate_version == "review-recognition/v2":
        candidate_v2 = parse_delivery_policy(candidate_raw)
        policy_changed = True
        if (candidate_v2.activation != {"kind": "transition", "change": state.change_id}
                or candidate_v2.required_checks_digest != new_checks["digest"]):
            raise ApprovalError("candidate policy activation or required checks do not match")
    else:
        raise ApprovalError("candidate review policy is missing, disabled or unsupported")

    old_authority_text = optional_regular_blob_text(root, base, _AUTHORITY)
    new_authority_text = optional_regular_blob_text(root, head, _AUTHORITY)
    authority_changed = False
    if old_authority_text is None:
        if new_authority_text is not None:
            proposed = parse_authority_yaml(new_authority_text)
            if proposed.enabled:
                raise ApprovalError("initial enabled trust needs separate owner establishment")
    else:
        if new_authority_text is None:
            raise ApprovalError("candidate removed the trusted policy authority")
        old_authority = parse_authority_yaml(old_authority_text)
        new_authority = parse_authority_yaml(new_authority_text)
        if not old_authority.enabled and new_authority.enabled:
            raise ApprovalError("initial enabled trust needs separate owner establishment")
        authority_changed = old_authority.digest != new_authority.digest

    if not policy_changed and not check_changes and not authority_changed:
        return {"trusted_base": base, "policy_digest": old_recognition.policy_digest,
                "required_checks_digest": old_checks["digest"], "mode": "unchanged"}
    if policy_changed and candidate_v2 is None:
        raise ApprovalError("legacy policy changes require an authorized v2 transition")
    if check_changes and candidate_v2 is None:
        raise ApprovalError("required check changes require an authorized v2 transition")
    if authority_changed and (policy_changed or check_changes):
        raise ApprovalError("key rotation must be a separate authority-only transition")

    expected_kind = {"rotate_key"} if authority_changed else {"transition", "recovery"}
    for event in reversed(read_change_events(events_file, state.change_id)):
        if event.type != "policy_authorization_imported":
            continue
        record = event.payload.get("authorization")
        if not isinstance(record, dict) or record.get("kind") not in expected_kind:
            continue
        try:
            validate_authorization_import(root, state, state.change_id, event.payload,
                                          for_use=True, actual_paths=paths)
            if candidate_v2 is not None:
                old_processes = {kind: old_recognition for kind in old_recognition.kinds}
                changes = changed_obligations(
                    old_processes=old_processes, old_code_review="full", old_scope=(),
                    old_builtin="keepsail-baseline/v1", old_checks=old_checks,
                    new_policy=candidate_v2, new_checks=new_checks,
                )
                require_signed_obligation_changes(changes, record)
            elif record.get("obligation_changes", []):
                raise ApprovalError("key rotation cannot alter delivery obligations")
        except (ApprovalError, ValueError, KeyError, TypeError):
            continue
        return {"trusted_base": base, "policy_digest": old_recognition.policy_digest,
                "required_checks_digest": old_checks["digest"], "mode": record["kind"],
                "authorization_digest": event.payload["authorization_digest"]}
    raise ApprovalError("delivery obligation changes lack matching signed authorization")
