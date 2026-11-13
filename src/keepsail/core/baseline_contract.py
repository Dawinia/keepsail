"""Stable identities for the built-in verification obligations."""

from __future__ import annotations

from typing import Any

from keepsail.core.approval import ApprovalError, digest_record

_CONTRACTS = {
    "keepsail-baseline/v1": (
        ("lifecycle-ordering", True, "fixed-matrix-without-no-review/v1"),
        ("scope-vs-plan-final", False, "declared-scope-advisory/v1"),
    ),
    "keepsail-baseline/v2": (
        ("lifecycle-ordering", True, "fixed-matrix-with-policy-no-review/v2"),
        ("scope-vs-plan-final", False, "declared-scope-advisory/v1"),
    ),
}


def builtin_check_contract(version: str) -> dict[str, Any]:
    definitions = _CONTRACTS.get(version)
    if definitions is None:
        raise ApprovalError("unsupported built-in checks version")
    checks: list[dict[str, Any]] = []
    for identifier, required, semantics in definitions:
        body = {"source": "baseline", "id": identifier, "must_pass": required,
                "semantics": semantics}
        checks.append({**body, "definition_digest": digest_record(body)})
    body = {"version": version, "checks": checks}
    return {**body, "digest": digest_record(body)}
