"""Adoption: the owner writes the first enabled recognition policy.

Before any policy is enabled there is no recognized review process, hence no
plan approval and nothing for keepsail's gate to protect.  The first enabled
policy is therefore initial setup (``keepsail init`` / ``keepsail policy
enable``), committed by the owner as the adoption commit before branch
protection and CI are turned on.  Trust starts from that first owner-written
policy; later changes are risk-boundary changes (plan declaration plus
``keepsail policy accept``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from keepsail.core.approval import ApprovalError, digest_record, resolve_contract_base
from keepsail.core.delivery_policy import parse_delivery_policy, require_activatable_policy
from keepsail.core.risk_boundary import POLICY_PATH, read_policy_side
from keepsail.core.scope_match import GitScopeError
from keepsail.core.strict_yaml import literal_paths, parse_unique_yaml
from keepsail.core.verification_config import parse_verification_config, required_check_contract

OWNER_PROCESS = {"id": "owner-plan-review", "version": "owner-plan-review/v1",
                 "issuers": ["owner"], "evidence_forms": ["json"], "requirements": {}}
CODE_REVIEW_MODES = ("off", "full", "scope")


@dataclass(frozen=True)
class PolicyChoice:
    """Whose review conclusions count, and which deliveries need code review."""

    recognizer: str = "owner"  # "owner" or "external"
    process_id: str | None = None
    process_version: str | None = None
    issuer: str | None = None
    evidence_form: str = "json"
    code_review: str = "off"
    scope: tuple[str, ...] = ()

    def process(self) -> dict[str, Any]:
        if self.recognizer == "owner":
            return dict(OWNER_PROCESS, issuers=list(OWNER_PROCESS["issuers"]),
                        evidence_forms=list(OWNER_PROCESS["evidence_forms"]), requirements={})
        if self.recognizer != "external":
            raise ApprovalError("recognizer must be 'owner' or 'external'")
        values = (self.process_id, self.process_version, self.issuer)
        if not all(isinstance(v, str) and v.strip() and v == v.strip() for v in values):
            raise ApprovalError("an external review process needs an id, version and issuer")
        if self.evidence_form != "json":
            raise ApprovalError("only json review conclusions are supported for new policies")
        return {"id": self.process_id, "version": self.process_version,
                "issuers": [self.issuer], "evidence_forms": ["json"], "requirements": {}}


def build_enabled_policy(choice: PolicyChoice, verification_text: str) -> dict[str, Any]:
    if choice.code_review not in CODE_REVIEW_MODES:
        raise ApprovalError("code review must be off, full or scope")
    checks = required_check_contract(parse_verification_config(verification_text, strict=True))
    process = choice.process()
    processes = {"plan": process}
    code_review: dict[str, Any] = {"mode": choice.code_review}
    if choice.code_review != "off":
        processes["code"] = dict(process)
    if choice.code_review == "scope":
        code_review["scope"] = literal_paths(list(choice.scope), label="code review scope")
    elif choice.scope:
        raise ApprovalError("a code review scope applies only to --code-review scope")
    policy: dict[str, Any] = {
        "version": "review-recognition/v2", "enabled": True,
        "processes_by_kind": processes, "code_review": code_review,
        "required_checks_digest": checks["digest"],
        "builtin_checks_version": "keepsail-baseline/v2",
    }
    policy["policy_digest"] = digest_record(policy)
    require_activatable_policy(parse_delivery_policy(policy))
    return policy


def render_policy(policy: dict[str, Any]) -> str:
    return ("# Owner-written review recognition policy (adoption).\n"
            "# Commit it to the target branch as the adoption commit, then enable branch\n"
            "# protection and CI. Change it later only through a Change that declares\n"
            "# RISK-BOUNDARY and the owner's `keepsail policy accept`.\n"
            + yaml.safe_dump(policy, sort_keys=False, allow_unicode=True))


def required_check_summary(verification_text: str) -> list[str]:
    contract = required_check_contract(parse_verification_config(verification_text, strict=True))
    return [f"{item['source']}/{item['id']}: {item['command']}" for item in contract["checks"]]


def trusted_policy_enabled(root: Path) -> bool:
    try:
        base = resolve_contract_base(root)
    except (ApprovalError, GitScopeError):
        return False
    return read_policy_side(root, base).state == "enabled"


def workspace_policy_state(root: Path) -> str:
    path = root / POLICY_PATH
    if not path.exists():
        return "missing"
    raw = parse_unique_yaml(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and raw.get("enabled") is False:
        return "disabled"
    if isinstance(raw, dict) and raw.get("enabled") is True:
        return "enabled"
    raise ApprovalError("the workspace review recognition policy is malformed")


def enable_policy(root: Path, choice: PolicyChoice) -> dict[str, Any]:
    """Write the first enabled policy; refused once any enabled policy is trusted."""
    if trusted_policy_enabled(root):
        raise ApprovalError("the trusted base already has an enabled policy; change it with a "
                            "Change that declares RISK-BOUNDARY and `keepsail policy accept`")
    if workspace_policy_state(root) == "enabled":
        raise ApprovalError("the workspace policy is already enabled; commit it as the "
                            "adoption commit, or edit it before committing")
    verification = root / ".harness/verification.yaml"
    policy = build_enabled_policy(choice, verification.read_text(encoding="utf-8"))
    (root / POLICY_PATH).write_text(render_policy(policy), encoding="utf-8", newline="\n")
    return policy
