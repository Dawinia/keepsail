"""Detect and verify risk-boundary changes: plan declaration plus owner record.

A risk-boundary change alters the effective recognition policy of an *enabled*
trusted baseline, or the required-check contract.  The Change making it still
delivers under the baseline's obligations; the change itself must be declared
by the frozen plan (``RISK-BOUNDARY`` commitment) and accepted by the owner's
recorded ``policy accept``.  Nothing here is a signature or replay: the record
makes the change visible and owner-authorized, it is not cryptographic identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    Recognition,
    _recognition_from_mapping,
    validate_plan_subject,
)
from keepsail.core.delivery_policy import (
    DeliveryPolicy,
    parse_delivery_policy,
    reject_signed_plan_policy,
    require_activatable_policy,
)
from keepsail.core.git_objects import optional_regular_blob_text, regular_blob_text
from keepsail.core.policy_obligations import (
    inactive_obligations,
    obligation_differences,
    semantic_labels,
    v1_obligations,
    v2_obligations,
    validate_differences,
)
from keepsail.core.strict_yaml import parse_unique_yaml
from keepsail.core.verification_config import parse_verification_config, required_check_contract

POLICY_PATH = ".harness/review-recognition.yaml"
VERIFICATION_PATH = ".harness/verification.yaml"
ACCEPTANCE_VERSION = "policy-acceptance/v1"
ACCEPTANCE_EVENT = "policy_change_accepted"
RISK_BOUNDARY_COMMITMENT = "RISK-BOUNDARY"
_ACCEPTANCE_FIELDS = frozenset({
    "version", "change_id", "plan_subject_id", "predecessor_policy_digest",
    "target_policy_digest", "target_policy_state", "predecessor_checks_digest",
    "target_checks_digest", "obligation_changes",
})
_LEGACY_SIGNED_KINDS = frozenset({"transition", "recovery", "rotate_key"})


@dataclass(frozen=True)
class PolicySide:
    """One side of a comparison: enabled (v1 or v2), disabled, or removed."""

    state: str
    digest: str | None
    obligations: dict[str, Any]
    v1: Recognition | None = None
    v2: DeliveryPolicy | None = None


def read_policy_side(root: Path, commit: str) -> PolicySide:
    text = optional_regular_blob_text(root, commit, POLICY_PATH)
    if text is None:
        return PolicySide("removed", None, inactive_obligations("removed"))
    raw = parse_unique_yaml(text)
    if not isinstance(raw, dict) or type(raw.get("enabled")) is not bool:
        raise ApprovalError("review recognition policy needs a boolean enabled field")
    if raw["enabled"] is False:
        if raw.get("version") != "review-recognition/v1":
            raise ApprovalError(
                "a disabled review recognition policy must be review-recognition/v1")
        return PolicySide("disabled", None, inactive_obligations("disabled"))
    if raw.get("version") == "review-recognition/v1":
        recognition = _recognition_from_mapping(raw)
        return PolicySide("enabled", recognition.policy_digest, v1_obligations(raw),
                          v1=recognition)
    if raw.get("version") == "review-recognition/v2":
        policy = parse_delivery_policy(raw)
        return PolicySide("enabled", policy.policy_digest, v2_obligations(raw), v2=policy)
    raise ApprovalError("unsupported review recognition policy version")


def read_checks(root: Path, commit: str, *, strict: bool) -> dict[str, Any]:
    return required_check_contract(parse_verification_config(
        regular_blob_text(root, commit, VERIFICATION_PATH), strict=strict))


@dataclass(frozen=True)
class RiskBoundary:
    base: PolicySide
    target: PolicySide
    base_checks: dict[str, Any]
    target_checks: dict[str, Any]
    differences: list[dict[str, Any]]

    @property
    def changed(self) -> bool:
        return bool(self.differences)

    @property
    def labels(self) -> list[str]:
        return semantic_labels(self.base.obligations, self.target.obligations, self.differences)

    def acceptance(self, *, change_id: str, plan_subject_id: str) -> dict[str, Any]:
        return {"version": ACCEPTANCE_VERSION, "change_id": change_id,
                "plan_subject_id": plan_subject_id,
                "predecessor_policy_digest": self.base.digest,
                "target_policy_digest": self.target.digest,
                "target_policy_state": self.target.state,
                "predecessor_checks_digest": self.base_checks["digest"],
                "target_checks_digest": self.target_checks["digest"],
                "obligation_changes": self.differences}


def compare_risk_boundary(root: Path, *, base: str, head: str) -> RiskBoundary | None:
    """Recompute both sides from committed Git objects; the workspace is not read.

    Returns ``None`` when the trusted base has no enabled policy: first
    enablement is adoption (``init`` / ``policy enable``), not a Change.
    """
    base_side = read_policy_side(root, base)
    if base_side.state != "enabled":
        return None
    if base_side.v2 is not None:
        reject_signed_plan_policy(base_side.v2)
    target = read_policy_side(root, head)
    base_checks = read_checks(root, base, strict=base_side.v2 is not None)
    if base_side.v2 is not None and base_side.v2.required_checks_digest != base_checks["digest"]:
        raise ApprovalError("required checks digest does not match the committed configuration")
    target_checks = read_checks(root, head, strict=True)
    if target.v2 is not None:
        if target.v2.required_checks_digest != target_checks["digest"]:
            raise ApprovalError(
                "required checks digest does not match the committed configuration")
        if target.digest != base_side.digest:
            require_activatable_policy(target.v2)
    differences = obligation_differences(base_side.obligations, target.obligations,
                                         base_checks, target_checks)
    result = RiskBoundary(base_side, target, base_checks, target_checks, differences)
    digests_differ = (base_side.digest != target.digest or base_side.state != target.state
                      or base_checks["digest"] != target_checks["digest"])
    if digests_differ != bool(differences):
        raise ApprovalError("internal error: policy digests and their obligation difference "
                            "disagree; refusing to record an incomplete change")
    return result


def require_risk_boundary_declaration(subject: object, *, change_id: str) -> None:
    """The frozen plan object itself must carry a non-empty RISK-BOUNDARY commitment."""
    plan = validate_plan_subject(subject, change_id=change_id)
    if not any(item.get("id") == RISK_BOUNDARY_COMMITMENT
               and isinstance(item.get("text"), str) and item["text"].strip()
               for item in plan["commitments"]):
        raise ApprovalError(
            "this Change alters the recognition policy or required checks; the approved plan "
            f"must declare it with a non-empty {RISK_BOUNDARY_COMMITMENT} commitment "
            f"(plan ready --commitment {RISK_BOUNDARY_COMMITMENT}=<text>)")


def validate_acceptance_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _ACCEPTANCE_FIELDS:
        raise ApprovalError("policy acceptance has missing or unknown fields")
    if value["version"] != ACCEPTANCE_VERSION:
        raise ApprovalError("unsupported policy acceptance version")
    if value["target_policy_state"] not in {"enabled", "disabled", "removed"}:
        raise ApprovalError("invalid target policy state")
    if (value["target_policy_state"] == "enabled") != isinstance(
            value["target_policy_digest"], str):
        raise ApprovalError("target policy digest must be null exactly when the policy is inactive")
    for key in ("change_id", "plan_subject_id", "predecessor_policy_digest",
                "predecessor_checks_digest", "target_checks_digest"):
        if not isinstance(value[key], str) or not value[key]:
            raise ApprovalError(f"policy acceptance needs {key}")
    validate_differences(value["obligation_changes"])
    return value


def validate_authorization_record(value: object) -> dict[str, Any]:
    """A v3 ``authorization``: the acceptance payload plus its ledger event's outer fields."""
    if isinstance(value, dict) and (value.get("kind") in _LEGACY_SIGNED_KINDS
                                    or value.get("version") == "policy-authorization/v1"):
        raise ApprovalError("signed policy authorizations are no longer accepted for new "
                            "deliveries; record the owner's decision with `keepsail policy "
                            "accept`")
    if not isinstance(value, dict) or set(value) != {"acceptance", "event_id", "actor", "ts"}:
        raise ApprovalError("v3 authorization must hold acceptance, event_id, actor and ts")
    actor = value["actor"]
    if (not isinstance(actor, dict) or set(actor) != {"type", "identifier"}
            or not all(isinstance(actor[key], str) and actor[key] for key in actor)):
        raise ApprovalError("v3 authorization actor is invalid")
    if not all(isinstance(value[key], str) and value[key] for key in ("event_id", "ts")):
        raise ApprovalError("v3 authorization needs its event id and timestamp")
    validate_acceptance_payload(value["acceptance"])
    return value


def require_matching_acceptance(
    boundary: RiskBoundary, acceptance: object, *, change_id: str, plan_subject_id: str,
) -> None:
    expected = boundary.acceptance(change_id=change_id, plan_subject_id=plan_subject_id)
    if validate_acceptance_payload(acceptance) != expected:
        raise ApprovalError(
            "the recorded policy acceptance does not match the recomputed change (target "
            "policy, check definitions, obligation changes or the approved plan differ); run "
            f"`keepsail policy accept {change_id}` again")


LEGACY_TRUST_FILES = (".harness/policy-authority.yaml", ".harness/policy-initial-trust.json")


def legacy_trust_notice(root: Path) -> str | None:
    """One line naming legacy signed-trust files that are now ignored."""
    present = [name for name in LEGACY_TRUST_FILES if (root / name).exists()]
    if not present:
        return None
    return (f"keepsail: {', '.join(present)} no longer used and can be deleted (deleting is not a "
            "risk-boundary change; keep policy-authority.yaml until the new verifier is on the "
            "target branch)")
