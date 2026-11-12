"""Identify old delivery obligations a signed transition would alter."""

from __future__ import annotations

from typing import Any

from keepsail.core.approval import ApprovalError, Recognition, digest_record
from keepsail.core.delivery_policy import DeliveryPolicy
from keepsail.core.policy_authority import _paths
from keepsail.core.scope_match import covered_by_scope


def _process(recognition: Recognition | None) -> dict[str, Any] | None:
    if recognition is None:
        return None
    return {"id": recognition.process_id, "version": recognition.process_version,
            "issuers": sorted(recognition.issuers),
            "evidence_forms": sorted(recognition.evidence_forms),
            "requirements": recognition.requirements}


def _review_not_weaker(old_mode: str, old_scope: tuple[str, ...],
                       new_mode: str, new_scope: tuple[str, ...]) -> bool:
    if old_mode not in {"full", "scope", "off"} or new_mode not in {"full", "scope", "off"}:
        raise ApprovalError("unknown code-review obligation")
    if old_mode == "scope":
        _paths(list(old_scope))
    if new_mode == "scope":
        _paths(list(new_scope))
    if old_mode == "off" or new_mode == "full":
        return True
    if old_mode == "full" or new_mode == "off":
        return False
    return all(covered_by_scope(path.rstrip("/"), list(new_scope)) for path in old_scope)


def check_definitions(contract: object) -> tuple[dict[str, bool], dict[tuple[str, str], str]]:
    if (not isinstance(contract, dict)
            or set(contract) != {"version", "layers", "checks", "digest"}
            or contract["version"] != "required-checks/v1"):
        raise ApprovalError("invalid required check contract digest or shape")
    calculated = digest_record({k: v for k, v in contract.items() if k != "digest"})
    if contract["digest"] != calculated:
        raise ApprovalError("invalid required check contract digest or shape")
    layers = contract["layers"]
    if (not isinstance(layers, dict)
            or set(layers) != {"baseline", "framework_adapter", "user_checks"}
            or not all(type(value) is bool for value in layers.values())):
        raise ApprovalError("invalid required check layer settings")
    checks = contract["checks"]
    if not isinstance(checks, list):
        raise ApprovalError("invalid required check definitions")
    definitions: dict[tuple[str, str], str] = {}
    for row in checks:
        if (not isinstance(row, dict) or set(row) != {
            "source", "id", "command", "shell", "workdir", "env", "timeout_seconds", "capture",
            "must_pass", "definition_digest"
        } or not isinstance(row["source"], str) or not row["source"]
                or not isinstance(row["id"], str) or not row["id"] or row["must_pass"] is not True):
            raise ApprovalError("invalid required check definition")
        identity = (row["source"], row["id"])
        digest = row["definition_digest"]
        definition = {k: v for k, v in row.items() if k != "definition_digest"}
        if (identity in definitions or not isinstance(digest, str)
                or digest != digest_record(definition)):
            raise ApprovalError("duplicate or invalid required check definition digest")
        definitions[identity] = digest
    return layers, definitions


def changed_obligations(
    *, old_processes: dict[str, Recognition], old_code_review: str, old_scope: tuple[str, ...],
    old_builtin: str, old_checks: dict[str, Any], new_policy: DeliveryPolicy,
    new_checks: dict[str, Any],
) -> list[dict[str, Any]]:
    """Describe reductions/replacements; never infer their authorization from the candidate."""
    changes: list[dict[str, Any]] = []

    def add(kind: str, source: str, identifier: str, old: object, new: object | None) -> None:
        changes.append({"kind": kind, "source": source, "id": identifier,
                        "old_digest": digest_record(old),
                        "new_digest": digest_record(new) if new is not None else None})

    for kind in ("plan", "code"):
        old = _process(old_processes.get(kind))
        new = _process(new_policy.recognition_for(kind))
        if old is not None and old != new:
            add("recognition", "review", kind, old, new)
    if not _review_not_weaker(old_code_review, old_scope, new_policy.code_review, new_policy.scope):
        add("code_review", "policy", "scope",
            {"mode": old_code_review, "scope": list(old_scope)},
            {"mode": new_policy.code_review, "scope": list(new_policy.scope)})
    if old_builtin != new_policy.builtin_checks_version:
        add("builtin_contract", "baseline", "version", old_builtin,
            new_policy.builtin_checks_version)
    changes.extend(changed_required_checks(old_checks, new_checks))
    return sorted(changes, key=lambda row: (row["kind"], row["source"], row["id"]))


def changed_required_checks(
    old_checks: dict[str, Any], new_checks: dict[str, Any],
) -> list[dict[str, Any]]:
    """Find removed or replaced old requirements, regardless of candidate policy."""
    old_layers, before = check_definitions(old_checks)
    new_layers, after = check_definitions(new_checks)
    changes: list[dict[str, Any]] = []
    if old_layers["baseline"] and not new_layers["baseline"]:
        changes.append({"kind": "builtin_contract", "source": "baseline", "id": "enabled",
                        "old_digest": digest_record(True), "new_digest": digest_record(False)})
    for identity, old_digest in before.items():
        new_digest = after.get(identity)
        if old_digest != new_digest:
            changes.append({"kind": "required_check", "source": identity[0], "id": identity[1],
                            "old_digest": old_digest, "new_digest": new_digest})
    return sorted(changes, key=lambda row: (row["kind"], row["source"], row["id"]))


def require_signed_obligation_changes(
    changes: list[dict[str, Any]], authorization: dict[str, Any],
) -> None:
    """Require the already signature-verified record to enumerate exact changes."""
    signed = authorization.get("obligation_changes", [])
    if not isinstance(signed, list):
        raise ApprovalError("signed obligation changes must be a list")
    normalized: list[dict[str, Any]] = []
    for item in signed:
        if (not isinstance(item, dict)
                or set(item) != {"kind", "source", "id", "old_digest", "new_digest", "reason"}
                or not isinstance(item["reason"], str) or not item["reason"].strip()):
            raise ApprovalError("signed obligation change is invalid")
        normalized.append({key: item[key] for key in ("kind", "source", "id", "old_digest",
                                                       "new_digest")})
    try:
        normalized.sort(key=lambda row: (row["kind"], row["source"], row["id"]))
    except TypeError as exc:
        raise ApprovalError("signed obligation change identity is invalid") from exc
    if normalized != changes:
        raise ApprovalError("old obligation changes are not exactly authorized")
