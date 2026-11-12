"""Replay an owner-established initial policy from a trusted Git baseline.

The confirmation is retained evidence, not an authentication mechanism. The
host must independently treat the selected target commit as trusted; candidate
content cannot establish its own trust by supplying this record.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from keepsail.core.approval import ApprovalError
from keepsail.core.git_objects import regular_blob_bytes
from keepsail.core.policy_authority import parse_unique_yaml
from keepsail.core.policy_snapshot import PolicySnapshot, read_policy_snapshot
from keepsail.core.scope_match import is_ancestor, resolve_commit

INITIAL_CONFIRMATION = ".harness/policy-initial-trust.json"
_POLICY = ".harness/review-recognition.yaml"
_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def _unique_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ApprovalError("duplicate initial trust confirmation field")
        result[key] = value
    return result


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ApprovalError("cannot inspect initial policy history") from exc


def require_no_prior_enabled_policy(root: Path, initial_commit: str) -> None:
    """Inspect every ancestral policy blob; incomplete history cannot prove initial trust."""
    if _git(root, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ApprovalError("initial trust requires complete Git history")
    try:
        parents = _git(root, "rev-list", "--parents", "--max-count=1", initial_commit).decode(
            "ascii"
        ).strip().split()[1:]
        if not parents:
            return
        listing = _git(root, "rev-list", "--objects", *parents, "--", _POLICY)
        blobs = {line.split(b" ", 1)[0] for line in listing.splitlines()
                 if line.endswith(b" " + _POLICY.encode("ascii"))}
        for oid in blobs:
            raw = parse_unique_yaml(_git(root, "cat-file", "blob", oid.decode("ascii")).decode(
                "utf-8"
            ))
            if not isinstance(raw, dict) or type(raw.get("enabled")) is not bool:
                raise ApprovalError("prior policy history is invalid or cannot prove disabled")
            if raw["enabled"]:
                raise ApprovalError("initial trust cannot replace a previously enabled policy")
    except UnicodeError as exc:
        raise ApprovalError("initial policy history is not valid text") from exc


def prepare_initial_confirmation(
    root: Path, *, initial_commit: str, repository_id: str, target_ref: str,
    owner_confirmation: object,
) -> dict[str, Any]:
    """Construct a retained claim about an exact initial commit; grants no authority."""
    required = {"owner", "statement", "evidence_reference", "original_evidence"}
    if (not isinstance(owner_confirmation, dict) or set(owner_confirmation) != required
            or any(not isinstance(value, str) or not value.strip()
                   for value in owner_confirmation.values())):
        raise ApprovalError("initial trust needs complete original owner confirmation")
    if (not isinstance(initial_commit, str) or _OID.fullmatch(initial_commit) is None
            or resolve_commit(root, initial_commit) != initial_commit):
        raise ApprovalError("initial trust requires a full commit object ID")
    first = read_policy_snapshot(root, initial_commit, repository_id=repository_id,
                                 target_ref=target_ref)
    if first.policy.activation != {"kind": "initial"}:
        raise ApprovalError("initial confirmation must identify an initial policy")
    require_no_prior_enabled_policy(root, initial_commit)
    return {"version": "policy-initial-trust/v1", "repository_id": repository_id,
            "target_ref": target_ref, "initial_commit": initial_commit,
            "policy_digest": first.policy.policy_digest, "authority_digest": first.authority.digest,
            "owner_confirmation": owner_confirmation}


def verify_initial_policy(
    root: Path, snapshot: PolicySnapshot, *, repository_id: str, target_ref: str,
) -> dict[str, Any]:
    """Check the exact recorded first policy and its retained owner confirmation."""
    data = regular_blob_bytes(root, snapshot.commit, INITIAL_CONFIRMATION)
    try:
        record = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid JSON constant")),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ApprovalError("initial trust confirmation is invalid JSON") from exc
    fields = {"version", "repository_id", "target_ref", "initial_commit", "policy_digest",
              "authority_digest", "owner_confirmation"}
    if not isinstance(record, dict) or set(record) != fields:
        raise ApprovalError("initial trust confirmation has missing or unknown fields")
    confirmation = record["owner_confirmation"]
    initial = record["initial_commit"]
    if (not isinstance(initial, str) or _OID.fullmatch(initial) is None
            or resolve_commit(root, initial) != initial or initial == snapshot.commit
            or not is_ancestor(root, initial, snapshot.commit)):
        raise ApprovalError("initial policy commit is not an earlier reachable commit")
    try:
        introductions = _git(root, "log", "--format=%H", "--diff-filter=A", "--no-renames",
                             snapshot.commit, "--", INITIAL_CONFIRMATION).decode("ascii").split()
    except UnicodeError as exc:
        raise ApprovalError("initial confirmation history is invalid") from exc
    if len(introductions) != 1:
        raise ApprovalError("initial confirmation introduction is missing or ambiguous")
    introduced = resolve_commit(root, introductions[0])
    if (introduced == initial or not is_ancestor(root, initial, introduced)
            or not is_ancestor(root, introduced, snapshot.commit)
            or regular_blob_bytes(root, introduced, INITIAL_CONFIRMATION) != data):
        raise ApprovalError("initial confirmation changed or is not after the initial commit")
    expected = prepare_initial_confirmation(
        root, initial_commit=initial, repository_id=repository_id, target_ref=target_ref,
        owner_confirmation=confirmation,
    )
    if record != expected or expected["policy_digest"] != snapshot.policy.policy_digest:
        raise ApprovalError("initial confirmation does not match the committed first policy")
    return {"initial_commit": initial, "initial_authority_digest": expected["authority_digest"],
            "confirmation": confirmation, "confirmation_assurance": "retained-owner-claim"}
