"""Verify required-check results against trusted normalized definitions."""

from __future__ import annotations

from typing import Any

from keepsail.core.approval import ApprovalError
from keepsail.core.baseline_contract import builtin_check_contract
from keepsail.core.policy_obligations import check_definitions


def verify_check_evidence(
    verification: object, *, subject_id: str, required_contract: dict[str, Any],
    builtin_version: str, trusted_base: str,
) -> dict[str, int]:
    """Require every enabled, mandatory check to pass for the frozen code subject."""
    if (not isinstance(verification, dict) or verification.get("subject_id") != subject_id
            or verification.get("outcome") != "passed"
            or verification.get("snapshot_unchanged") is not True):
        raise ApprovalError("verification does not prove the frozen code subject passed")
    layers, expected = check_definitions(required_contract)
    builtin = builtin_check_contract(builtin_version)
    project_count = len(expected)
    if layers["baseline"]:
        expected.update({(row["source"], row["id"]): row["definition_digest"]
                         for row in builtin["checks"] if row["must_pass"]})
    evidence = verification.get("check_evidence")
    if (not isinstance(evidence, dict) or set(evidence) != {
        "version", "required_checks_digest", "trusted_base", "builtin_checks_version",
        "builtin_checks_digest", "results"
    } or evidence["version"] != "verification-check-evidence/v1"
            or evidence["required_checks_digest"] != required_contract["digest"]
            or evidence["trusted_base"] != trusted_base
            or evidence["builtin_checks_version"] != builtin_version
            or evidence["builtin_checks_digest"] != builtin["digest"]):
        raise ApprovalError("verification check evidence uses a different trusted contract")
    rows = evidence["results"]
    if not isinstance(rows, list):
        raise ApprovalError("verification check results must be a list")
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {
            "source", "id", "status", "exit_code", "must_pass", "definition_digest"
        } or not isinstance(row["source"], str) or not row["source"]
                or not isinstance(row["id"], str) or not row["id"]
                or not isinstance(row["status"], str)
                or row["status"] not in {"pass", "fail", "spawn_error", "timeout", "skipped"}
                or type(row["exit_code"]) is not int or type(row["must_pass"]) is not bool):
            raise ApprovalError("invalid verification check result")
        key = (row["source"], row["id"])
        if key in seen:
            raise ApprovalError("duplicate verification check result")
        seen[key] = row
    for key, definition_digest in expected.items():
        row = seen.get(key)
        if (row is None or row["status"] != "pass" or row["exit_code"] != 0
                or row["must_pass"] is not True
                or row["definition_digest"] != definition_digest):
            raise ApprovalError(f"required check missing, failed or changed: {key[0]}/{key[1]}")
    return {"required_project_checks": project_count, "required_total_checks": len(expected)}
