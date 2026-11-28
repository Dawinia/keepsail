"""Strict policy-v2 parsing and actual-manifest code-review applicability.

Parsing a candidate does not make it effective.  A caller uses a policy as the
delivery authority only when it is read from the committed trusted baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    Recognition,
    digest_record,
    evidence_is_recognized,
    validate_evidence,
)
from keepsail.core.git_diff import DiffEntry, require_literal_paths
from keepsail.core.scope_match import covered_by_scope
from keepsail.core.slug import SlugError, validate_slug
from keepsail.core.strict_yaml import literal_paths, parse_unique_yaml

_POLICY_FIELDS = frozenset({
    "version", "enabled", "processes_by_kind", "code_review", "required_checks_digest",
    "builtin_checks_version", "policy_digest",
})
# ``activation`` is retained only as a historical description when present.
_OPTIONAL_POLICY_FIELDS = frozenset({"activation"})
SIGNED_PLAN_FORM = "signed-plan-decision"
SIGNED_PLAN_MIGRATION = (
    "the trusted policy recognizes signed-plan-decision plan conclusions, which this "
    "keepsail version no longer verifies; with the previous keepsail version, deliver one "
    "signed transition that changes the plan process to a json owner conclusion, merge it, "
    "and only then upgrade (see docs/getting-started.md, 'Upgrading from signed policy "
    "transitions')"
)


def _strings(value: object, label: str) -> frozenset[str]:
    if (not isinstance(value, list) or not value
            or not all(isinstance(item, str) and item and item == item.strip() for item in value)
            or len(value) != len(set(value))):
        raise ApprovalError(f"{label} must be a non-empty list of unique strings")
    return frozenset(value)


@dataclass(frozen=True)
class DeliveryPolicy:
    policy_digest: str
    processes: dict[str, Recognition]
    code_review: str
    scope: tuple[str, ...]
    required_checks_digest: str
    builtin_checks_version: str
    activation: dict[str, str] | None

    def recognition_for(self, kind: str) -> Recognition | None:
        if kind == "code" and self.code_review == "off":
            return None
        return self.processes.get(kind)

    def review_requirement(self, manifest: list[dict[str, Any]]) -> tuple[bool, str]:
        """Evaluate changed paths including the old side of every rename/copy."""
        paths: list[str] = []
        for row in manifest:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                raise ApprovalError("invalid actual change manifest")
            paths.append(row["path"])
            if "old_path" in row:
                if not isinstance(row["old_path"], str):
                    raise ApprovalError("invalid old path in change manifest")
                paths.append(row["old_path"])
        if self.code_review == "full":
            return True, "policy requires code review for all changes"
        if self.code_review == "off":
            return False, "policy does not require code review"
        try:
            require_literal_paths([DiffEntry("M", (path,)) for path in paths])
        except ValueError as exc:
            raise ApprovalError(str(exc)) from exc
        matches = sorted(path for path in paths if covered_by_scope(path, list(self.scope)))
        if matches:
            return True, "policy scope matched: " + ", ".join(matches)
        if self.builtin_checks_version == "keepsail-baseline/v1":
            return True, "legacy built-in v1 requires code review outside the policy scope"
        return False, "no actual changed path matched the policy scope"


def parse_delivery_policy(value: object) -> DeliveryPolicy:
    if (not isinstance(value, dict) or not _POLICY_FIELDS <= set(value)
            or set(value) - _POLICY_FIELDS - _OPTIONAL_POLICY_FIELDS):
        raise ApprovalError("review-recognition/v2 has missing or unknown fields")
    if value["version"] != "review-recognition/v2" or value["enabled"] is not True:
        raise ApprovalError("review-recognition/v2 must be enabled")
    claimed = value["policy_digest"]
    calculated = digest_record({key: item for key, item in value.items() if key != "policy_digest"})
    if not isinstance(claimed, str) or claimed != calculated:
        raise ApprovalError("review-recognition/v2 policy digest does not match")
    checks = value["required_checks_digest"]
    if (not isinstance(checks, str) or len(checks) != 64
            or any(ch not in "0123456789abcdef" for ch in checks)):
        raise ApprovalError("required checks digest must be a SHA-256 digest")
    baseline = value["builtin_checks_version"]
    if not isinstance(baseline, str) or baseline not in {
        "keepsail-baseline/v1", "keepsail-baseline/v2"
    }:
        raise ApprovalError("unsupported built-in checks version")
    activation = value.get("activation")
    if "activation" in value and not isinstance(activation, dict):
        raise ApprovalError("policy activation must be an object")
    if activation is None or activation == {"kind": "initial"}:
        pass
    elif (set(activation) != {"kind", "change"} or activation.get("kind") != "transition"
          or not isinstance(activation.get("change"), str) or not activation["change"].strip()):
        raise ApprovalError("invalid policy activation locator")
    else:
        try:
            validate_slug(activation["change"])
        except SlugError as exc:
            raise ApprovalError("invalid policy activation Change") from exc
    code = value["code_review"]
    if (not isinstance(code, dict) or not isinstance(code.get("mode"), str)
            or code["mode"] not in {"full", "scope", "off"}):
        raise ApprovalError("invalid code review policy")
    mode = code["mode"]
    if mode == "scope":
        if set(code) != {"mode", "scope"}:
            raise ApprovalError("scoped code review requires only mode and scope")
        scope = tuple(literal_paths(code["scope"], label="code review scope"))
    else:
        if set(code) != {"mode"}:
            raise ApprovalError("full/off code review cannot contain scope or unknown fields")
        scope = ()
    if mode == "off" and baseline != "keepsail-baseline/v2":
        raise ApprovalError("policies permitting no code review require built-in contract v2")
    processes = value["processes_by_kind"]
    if (not isinstance(processes, dict) or not {"plan"} <= set(processes)
            or not set(processes) <= {"plan", "code"}
            or (mode in {"full", "scope"} and "code" not in processes)):
        raise ApprovalError("policy needs plan and any required code review processes")
    parsed: dict[str, Recognition] = {}
    for kind, process in processes.items():
        if not isinstance(process, dict) or set(process) != {
            "id", "version", "issuers", "evidence_forms", "requirements"
        }:
            raise ApprovalError(f"{kind} process has missing or unknown fields")
        pid, version = process["id"], process["version"]
        if not all(isinstance(s, str) and s and s == s.strip() for s in (pid, version)):
            raise ApprovalError(f"{kind} process needs an id and version")
        issuers = _strings(process["issuers"], f"{kind} issuers")
        forms = _strings(process["evidence_forms"], f"{kind} evidence forms")
        if not forms <= {"json", SIGNED_PLAN_FORM}:
            raise ApprovalError("unsupported review evidence form")
        if kind != "plan" and SIGNED_PLAN_FORM in forms:
            raise ApprovalError("signed plan decisions cannot authorize code review")
        if not isinstance(process["requirements"], dict):
            raise ApprovalError("process requirements must be an object")
        parsed[kind] = Recognition("review-recognition/v2", pid, version, frozenset({kind}),
                                   issuers, forms, dict(process["requirements"]), claimed)
    return DeliveryPolicy(claimed, parsed, mode, scope, checks, baseline,
                          dict(activation) if activation is not None else None)


def reject_signed_plan_policy(policy: DeliveryPolicy) -> None:
    """A trusted signed-plan policy must be migrated by the previous version first."""
    plan = policy.processes.get("plan")
    if plan is not None and SIGNED_PLAN_FORM in plan.evidence_forms:
        raise ApprovalError(SIGNED_PLAN_MIGRATION)


def verify_v2_review_evidence(
    value: object, recognition: Recognition, *, change_id: str,
) -> dict[str, Any]:
    """Validate kind-specific recognition and provenance; no form is signature-bound."""
    evidence = validate_evidence(value, change_id=change_id)
    if recognition.version != "review-recognition/v2" or recognition.policy_digest is None:
        raise ApprovalError("review evidence requires a v2 recognition basis")
    provenance = evidence.get("provenance")
    if (not isinstance(provenance, dict)
            or provenance.get("policy_digest") != recognition.policy_digest):
        raise ApprovalError("review evidence is bound to another recognition policy")
    if not evidence_is_recognized(evidence, recognition):
        raise ApprovalError("review evidence process, kind, issuer or form is not recognized")
    return evidence


def require_activatable_policy(policy: DeliveryPolicy) -> None:
    """New policies must have usable, portable review obligations."""
    reject_signed_plan_policy(policy)
    if policy.code_review != "full" and policy.builtin_checks_version != "keepsail-baseline/v2":
        raise ApprovalError("new no-review policies require built-in contract v2")
    if any(PureWindowsPath(path).drive or path.startswith("~")
           for path in policy.scope):
        raise ApprovalError("new review scopes must use literal repository-relative paths")


def parse_delivery_policy_yaml(text: str) -> DeliveryPolicy:
    return parse_delivery_policy(parse_unique_yaml(text))
