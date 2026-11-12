"""Strict policy-v2 parsing and actual-manifest code-review applicability.

Parsing a candidate is not activation.  A caller may use a policy as authority
only after resolving and validating it from its independently trusted baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from keepsail.core.approval import ApprovalError, Recognition, digest_record
from keepsail.core.policy_authority import _paths, parse_unique_yaml
from keepsail.core.scope_match import covered_by_scope
from keepsail.core.slug import SlugError, validate_slug

_POLICY_FIELDS = frozenset({
    "version", "enabled", "processes_by_kind", "code_review", "required_checks_digest",
    "builtin_checks_version", "activation", "policy_digest",
})


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
    activation: dict[str, str]

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
        for path in paths:
            _paths([path])
        if self.code_review == "full":
            return True, "policy requires code review for all changes"
        if self.code_review == "off":
            return False, "policy does not require code review"
        matches = sorted(path for path in paths if covered_by_scope(path, list(self.scope)))
        if matches:
            return True, "policy scope matched: " + ", ".join(matches)
        return False, "no actual changed path matched the policy scope"


def parse_delivery_policy(value: object) -> DeliveryPolicy:
    if not isinstance(value, dict) or set(value) != _POLICY_FIELDS:
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
    activation = value["activation"]
    if not isinstance(activation, dict):
        raise ApprovalError("policy activation must be an object")
    if activation == {"kind": "initial"}:
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
        scope = tuple(_paths(code["scope"]))
    else:
        if set(code) != {"mode"}:
            raise ApprovalError("full/off code review cannot contain scope or unknown fields")
        scope = ()
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
        if not forms <= {"json", "signed-plan-decision"}:
            raise ApprovalError("unsupported review evidence form")
        if kind != "plan" and "signed-plan-decision" in forms:
            raise ApprovalError("signed plan decisions cannot authorize code review")
        if not isinstance(process["requirements"], dict):
            raise ApprovalError("process requirements must be an object")
        parsed[kind] = Recognition("review-recognition/v2", pid, version, frozenset({kind}),
                                   issuers, forms, dict(process["requirements"]), claimed)
    return DeliveryPolicy(claimed, parsed, mode, scope, checks, baseline, dict(activation))


def parse_delivery_policy_yaml(text: str) -> DeliveryPolicy:
    return parse_delivery_policy(parse_unique_yaml(text))
