"""Strict v3 attestation envelope; structural parsing does not grant authority."""

from __future__ import annotations

import json
import re
from typing import Any

from keepsail.core.approval import ApprovalError, canonical_json, digest_record
from keepsail.core.slug import SlugError, validate_slug

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ApprovalError("duplicate v3 attestation key")
        result[key] = value
    return result


def _basis(value: object, *, kind: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ApprovalError(f"v3 {kind} recognition basis must be an object")
    mode = value.get("mode")
    if not isinstance(mode, str):
        raise ApprovalError(f"invalid v3 {kind} recognition mode")
    expected = {"mode", "policy_digest"}
    if mode in {"recovery", "continued_plan"}:
        expected.add("authorization_digest")
    if (set(value) != expected or mode not in {"current", "recovery", "continued_plan"}
            or (kind == "code" and mode == "continued_plan")):
        raise ApprovalError(f"invalid v3 {kind} recognition basis")
    for key in expected - {"mode"}:
        if not isinstance(value[key], str) or _SHA256.fullmatch(value[key]) is None:
            raise ApprovalError(f"invalid v3 {kind} recognition digest")
    return dict(value)


def validate_v3(value: object) -> dict[str, Any]:
    """Check envelope and embedded snapshot identities, not delivery authority."""
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "change_id", "trusted_base", "policy_digest", "recognition_basis",
        "authorization", "snapshot", "digest"
    } or value["schema_version"] != "attestation/v3":
        raise ApprovalError("invalid v3 attestation envelope")
    change, base, policy_digest = value["change_id"], value["trusted_base"], value["policy_digest"]
    if (not isinstance(change, str) or not change or not isinstance(base, str)
            or _COMMIT.fullmatch(base) is None or not isinstance(policy_digest, str)
            or _SHA256.fullmatch(policy_digest) is None):
        raise ApprovalError("invalid v3 attestation identity or trusted base")
    try:
        validate_slug(change)
    except SlugError as exc:
        raise ApprovalError("invalid v3 attestation Change") from exc
    content = {key: item for key, item in value.items() if key != "digest"}
    if value["digest"] != digest_record(content):
        raise ApprovalError("v3 attestation digest mismatch")
    basis = value["recognition_basis"]
    if not isinstance(basis, dict) or set(basis) != {"plan", "code"}:
        raise ApprovalError("v3 attestation needs separate plan and code recognition bases")
    plan = _basis(basis["plan"], kind="plan")
    code = _basis(basis["code"], kind="code") if basis["code"] is not None else None
    authorization = value["authorization"]
    if authorization is not None and not isinstance(authorization, dict):
        raise ApprovalError("v3 authorization must be an object or null")
    for item in (plan, code):
        if (item is not None and item["mode"] == "current"
                and item["policy_digest"] != policy_digest):
            raise ApprovalError("v3 current basis does not match the trusted policy")
        if item is not None and item["mode"] == "recovery":
            if (authorization is None
                    or item["authorization_digest"] != digest_record(authorization)):
                raise ApprovalError("v3 recovery basis does not match its signed authorization")
            expected = digest_record({"version": "recovery-recognition/v1",
                                      "base_policy_digest": policy_digest,
                                      "authorization_digest": item["authorization_digest"]})
            if item["policy_digest"] != expected:
                raise ApprovalError("v3 recovery recognition digest does not match")
    snapshot = value["snapshot"]
    if (not isinstance(snapshot, dict) or snapshot.get("schema_version") != "attestation/v2"
            or snapshot.get("change_id") != change):
        raise ApprovalError("v3 lifecycle snapshot does not match the Change")
    snapshot_content = {k: v for k, v in snapshot.items() if k != "digest"}
    if snapshot.get("digest") != digest_record(snapshot_content):
        raise ApprovalError("v3 lifecycle snapshot digest does not match")
    # A separate trusted verifier must validate snapshot semantics, Git objects,
    # signatures, obligations, and all recognition bases before accepting this.
    return dict(value)


def make_v3(*, change_id: str, trusted_base: str, policy_digest: str,
            recognition_basis: dict[str, Any], authorization: dict[str, Any] | None,
            snapshot: dict[str, Any]) -> dict[str, Any]:
    body = {"schema_version": "attestation/v3", "change_id": change_id,
            "trusted_base": trusted_base, "policy_digest": policy_digest,
            "recognition_basis": recognition_basis, "authorization": authorization,
            "snapshot": snapshot}
    return validate_v3({**body, "digest": digest_record(body)})


def parse_v3_line(data: bytes) -> dict[str, Any]:
    if not data.endswith(b"\n") or data.count(b"\n") != 1:
        raise ApprovalError("v3 attestation must be one complete JSON line")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApprovalError("invalid v3 attestation JSON") from exc
    result = validate_v3(value)
    if canonical_json(result).encode("utf-8") + b"\n" != data:
        raise ApprovalError("v3 attestation JSON is not canonical")
    return result
