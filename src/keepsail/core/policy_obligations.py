"""Effective delivery obligations and their complete, generic difference.

A risk-boundary change is recorded as a structural difference between two
normalized objects: the effective obligation object of the recognition policy,
and the required-check contract.  Completeness comes from the generic diff, not
from a list of known fields; semantic labels are an added reading aid only.
"""

from __future__ import annotations

from typing import Any

from keepsail.core.approval import ApprovalError, canonical_json, digest_record
from keepsail.core.scope_match import covered_by_scope
from keepsail.core.strict_yaml import literal_paths

OBLIGATIONS_VERSION = "effective-obligations/v1"
CHECKS_OBJECT_VERSION = "required-check-object/v1"
_DIRECTIONS = frozenset({"added", "removed", "changed"})


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


def _code_review(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("mode") not in {"full", "scope", "off"}:
        raise ApprovalError("invalid code review policy")
    return {"mode": raw["mode"], "scope": list(raw.get("scope", []))}


def v1_obligations(raw: dict[str, Any]) -> dict[str, Any]:
    """Make v1's implied full review and baseline/v1 contract explicit.

    ``raw`` must already be validated as an enabled v1 recognition policy.
    Every field covered by the v1 digest is carried, so differing v1 digests
    produce a non-empty difference (kinds only distribute the process).
    """
    process = {key: value for key, value in raw["process"].items()
               if key not in {"kinds", "policy_digest"}}
    return {"schema": OBLIGATIONS_VERSION, "state": "enabled", "version": raw["version"],
            "enabled": raw["enabled"],
            "processes_by_kind": {kind: dict(process) for kind in raw["process"]["kinds"]},
            "code_review": {"mode": "full", "scope": []},
            "builtin_checks_version": "keepsail-baseline/v1",
            "activation": None}


def v2_obligations(raw: dict[str, Any]) -> dict[str, Any]:
    """Return the v2 digest object without its digest-only fields, in v1's shape.

    ``required_checks_digest`` is represented by the required-check object,
    which is compared separately; ``activation`` is informational but retained
    so that every change to the policy digest is visible.
    """
    return {"schema": OBLIGATIONS_VERSION, "state": "enabled", "version": raw["version"],
            "enabled": raw["enabled"],
            "processes_by_kind": {kind: dict(process)
                                  for kind, process in raw["processes_by_kind"].items()},
            "code_review": _code_review(raw["code_review"]),
            "builtin_checks_version": raw["builtin_checks_version"],
            "activation": raw.get("activation")}


def inactive_obligations(state: str) -> dict[str, Any]:
    if state not in {"disabled", "removed"}:
        raise ApprovalError("unknown inactive policy state")
    return {"state": state}


def checks_object(contract: dict[str, Any]) -> dict[str, Any]:
    """Align required checks by ``(source, id)``, keeping order and every digested field."""
    check_definitions(contract)
    by_source: dict[str, dict[str, Any]] = {}
    for row in contract["checks"]:
        by_source.setdefault(row["source"], {})[row["id"]] = {
            key: value for key, value in row.items()
            if key not in {"source", "id", "definition_digest"}
        }
    return {"schema": CHECKS_OBJECT_VERSION, "version": contract["version"],
            "layers": dict(contract["layers"]),
            "order": [[row["source"], row["id"]] for row in contract["checks"]],
            "checks": by_source}


def _pointer(path: tuple[str, ...]) -> str:
    return "".join("/" + part.replace("~", "~0").replace("/", "~1") for part in path)


def _leaves(value: object, path: tuple[str, ...]) -> list[tuple[tuple[str, ...], object]]:
    if isinstance(value, dict) and value:
        rows: list[tuple[tuple[str, ...], object]] = []
        for key in sorted(value):
            rows.extend(_leaves(value[key], (*path, str(key))))
        return rows
    return [(path, value)]


def structural_diff(before: object, after: object, *, obj: str) -> list[dict[str, Any]]:
    """Generic field-by-field difference; lists and scalars compare as whole values."""
    rows: list[dict[str, Any]] = []

    def walk(old: object, new: object, path: tuple[str, ...]) -> None:
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(set(old) | set(new), key=str):
                child = (*path, str(key))
                if key not in new:
                    for leaf, value in _leaves(old[key], child):
                        rows.append({"object": obj, "path": _pointer(leaf),
                                     "direction": "removed", "before": value})
                elif key not in old:
                    for leaf, value in _leaves(new[key], child):
                        rows.append({"object": obj, "path": _pointer(leaf),
                                     "direction": "added", "after": value})
                else:
                    walk(old[key], new[key], child)
        elif canonical_json(old) != canonical_json(new):
            # Compare as the digest does: canonical JSON distinguishes 1 from true.
            rows.append({"object": obj, "path": _pointer(path), "direction": "changed",
                         "before": old, "after": new})

    walk(before, after, ())
    return rows


def obligation_differences(
    base_policy: dict[str, Any], target_policy: dict[str, Any],
    base_checks: dict[str, Any], target_checks: dict[str, Any],
) -> list[dict[str, Any]]:
    return [*structural_diff(base_policy, target_policy, obj="policy"),
            *structural_diff(checks_object(base_checks), checks_object(target_checks),
                             obj="checks")]


def validate_differences(value: object) -> list[dict[str, Any]]:
    """Structural check of a recorded difference list (values are compared, not trusted)."""
    if not isinstance(value, list):
        raise ApprovalError("obligation_changes must be a list")
    for row in value:
        if not isinstance(row, dict) or row.get("direction") not in _DIRECTIONS:
            raise ApprovalError("invalid obligation change")
        expected = {"object", "path", "direction"} | (
            {"before"} if row["direction"] != "added" else set()
        ) | ({"after"} if row["direction"] != "removed" else set())
        if (set(row) != expected or row["object"] not in {"policy", "checks"}
                or not isinstance(row["path"], str)):
            raise ApprovalError("invalid obligation change")
    return value


def _review_not_weaker(old: dict[str, Any], new: dict[str, Any]) -> bool:
    old_mode, new_mode = old["mode"], new["mode"]
    if old_mode == "scope":
        literal_paths(old["scope"], label="code review scope")
    if new_mode == "scope":
        literal_paths(new["scope"], label="code review scope")
    if old_mode == "off" or new_mode == "full":
        return True
    if old_mode == "full" or new_mode == "off":
        return False
    return all(covered_by_scope(path, list(new["scope"])) for path in old["scope"])


def semantic_labels(
    base_policy: dict[str, Any], target_policy: dict[str, Any],
    differences: list[dict[str, Any]],
) -> list[str]:
    """Readable summary; the difference list remains the complete record."""
    labels: list[str] = []

    def add(label: str) -> None:
        if label not in labels:
            labels.append(label)

    base_state, target_state = base_policy.get("state"), target_policy.get("state")
    if base_state == "enabled" and target_state in {"disabled", "removed"}:
        add("policy " + ("disabled" if target_state == "disabled" else "file removed"))
    if base_state != "enabled" and target_state == "enabled":
        add("policy enabled")
    if (base_state == target_state == "enabled"
            and base_policy["version"] != target_policy["version"]):
        add(f"policy version {base_policy['version']} -> {target_policy['version']}")
    for row in differences:
        parts = row["path"].split("/")[1:]
        if row["object"] == "policy" and parts[:1] == ["processes_by_kind"] and len(parts) > 1:
            kind = parts[1]
            before = base_policy.get("processes_by_kind", {}).get(kind)
            after = target_policy.get("processes_by_kind", {}).get(kind)
            if before is None:
                add(f"{kind} review process added")
            elif after is None:
                add(f"{kind} review process removed")
            else:
                add(f"{kind} review process replaced or changed")
        elif row["object"] == "policy" and parts[:1] == ["builtin_checks_version"]:
            add("built-in check contract changed")
        elif row["object"] == "policy" and parts[:1] == ["activation"]:
            add("activation description changed (informational)")
        elif row["object"] == "checks" and parts[:1] == ["layers"] and len(parts) > 1:
            add(f"required check layer {parts[1]} "
                + ("enabled" if row.get("after") is True else "disabled"))
        elif row["object"] == "checks" and parts[:1] == ["order"]:
            add("required check order changed")
        elif row["object"] == "checks" and parts[:1] == ["checks"] and len(parts) > 2:
            source, check = parts[1], parts[2]
            presence = _check_presence(differences, source, check)
            if presence == "removed":
                add(f"required check removed: {source}/{check}")
            elif presence == "added":
                add(f"required check added: {source}/{check}")
            else:
                add(f"required check definition changed: {source}/{check}")
    if (base_state == target_state == "enabled"
            and base_policy["code_review"] != target_policy["code_review"]):
        old, new = base_policy["code_review"], target_policy["code_review"]
        weaker = not _review_not_weaker(old, new)
        stronger = not _review_not_weaker(new, old)
        add(f"code review {'relaxed' if weaker else 'strengthened' if stronger else 'changed'} "
            f"({old['mode']} -> {new['mode']})")
    return labels


def _check_presence(differences: list[dict[str, Any]], source: str, check: str) -> str:
    """Every required check has a ``command``; its own row tells whether the check moved."""
    command = _pointer(("checks", source, check, "command"))
    row = next((item for item in differences
                if item["object"] == "checks" and item["path"] == command), None)
    return row["direction"] if row is not None and row["direction"] != "changed" else "changed"
