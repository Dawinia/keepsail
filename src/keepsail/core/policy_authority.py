"""Validation of committed policy trust and its signed authorizations.

This module has no private-key operations or network access.  Its callers must
obtain the authority from a trusted Git object and supply repository/ref identity
from their own trusted execution context, not from the candidate being checked.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from keepsail.core.approval import (
    ApprovalError,
    Recognition,
    _recognition_from_mapping,
    canonical_json,
    digest_record,
    evidence_is_recognized,
    load_recognition,
    resolve_contract_base,
    validate_evidence,
    validate_plan_subject,
)
from keepsail.core.git_objects import regular_blob_text
from keepsail.core.scope_match import covered_by_scope, resolve_commit

_HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_PURPOSES = frozenset({"policy-transition", "policy-recovery", "plan-decision"})
_AUTH_FIELDS = frozenset({
    "version", "repository_id", "target_ref", "base_sha", "predecessor_policy_digest",
    "target_policy_digest", "change_id", "plan_subject_id", "kind", "permitted_paths",
    "decision", "key_id", "signature",
})


class _UniqueLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: _UniqueLoader, node: yaml.MappingNode) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ApprovalError("duplicate or non-string key in authority configuration")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _fields(value: object, required: set[str] | frozenset[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != required:
        raise ApprovalError(f"{label} has missing or unknown fields")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ApprovalError(f"{label} must be non-empty text")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _HEX_DIGEST.fullmatch(value) is None:
        raise ApprovalError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _decode(value: object, size: int, label: str) -> bytes:
    if not isinstance(value, str):
        raise ApprovalError(f"{label} must be standard Base64")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ApprovalError(f"{label} must be standard Base64") from exc
    if len(raw) != size or base64.b64encode(raw).decode("ascii") != value:
        raise ApprovalError(f"{label} has an invalid length or encoding")
    return raw


def _target_ref(value: object) -> str:
    ref = _text(value, "target_ref")
    invalid = any(ord(ch) < 33 or ord(ch) == 127 or ch in "~^:?*[\\" for ch in ref)
    parts = ref.split("/")
    if (not ref.startswith("refs/heads/") or invalid or ".." in ref or "@{" in ref
            or any(not part or part.startswith(".") or part.endswith((".", ".lock"))
                   for part in parts)):
        raise ApprovalError("target_ref must be a full, valid branch ref")
    return ref


def _paths(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ApprovalError("permitted_paths must be a non-empty list")
    result: list[str] = []
    for item in value:
        path = _text(item, "permitted path")
        bare = path[:-1] if path.endswith("/") else path
        parsed = PurePosixPath(bare)
        if (not bare or parsed.is_absolute() or parsed.as_posix() != bare
                or any(part in {".", ".."} for part in bare.split("/"))
                or any(ch in path for ch in "\\*?[]\x00") or path in result):
            raise ApprovalError("permitted_paths must contain unique literal repository paths")
        result.append(path)
    return result


@dataclass(frozen=True)
class PolicyAuthority:
    """A parsed authority; an enabled authority has exactly one key."""

    repository_id: str
    target_ref: str
    enabled: bool
    key_id: str | None
    public_key: bytes | None
    purposes: frozenset[str]
    digest: str


def parse_authority(value: object) -> PolicyAuthority:
    raw = _fields(value, {"version", "repository_id", "target_ref", "enabled", "keys"},
                  label="policy authority")
    if raw["version"] != "policy-authority/v1" or type(raw["enabled"]) is not bool:
        raise ApprovalError("unsupported authority version or enabled value")
    repository = _text(raw["repository_id"], "repository_id")
    target = _target_ref(raw["target_ref"])
    keys = raw["keys"]
    if not isinstance(keys, list) or len(keys) != int(raw["enabled"]):
        raise ApprovalError("enabled authority requires exactly one key; disabled requires none")
    key_id: str | None = None
    public_key: bytes | None = None
    purposes: frozenset[str] = frozenset()
    if keys:
        key = _fields(keys[0], {"key_id", "algorithm", "public_key", "purposes"},
                      label="authority key")
        if key["algorithm"] != "ed25519":
            raise ApprovalError("unsupported authority key algorithm")
        public_key = _decode(key["public_key"], 32, "public_key")
        key_id = _digest(key["key_id"], "key_id")
        if key_id != sha256(public_key).hexdigest():
            raise ApprovalError("authority key_id does not match public key")
        selected = key["purposes"]
        if (not isinstance(selected, list) or not all(isinstance(p, str) for p in selected)
                or len(selected) != len(set(selected)) or not set(selected) <= _PURPOSES
                or "policy-transition" not in selected):
            raise ApprovalError("authority key purposes are invalid")
        purposes = frozenset(selected)
    return PolicyAuthority(repository, target, raw["enabled"], key_id, public_key, purposes,
                           digest_record(raw))


def parse_unique_yaml(text: str) -> object:
    """Parse YAML without silently accepting duplicate or non-string keys."""
    try:
        return yaml.load(text, Loader=_UniqueLoader)
    except yaml.YAMLError as exc:
        raise ApprovalError(f"policy configuration is invalid: {exc}") from exc


def parse_authority_yaml(text: str) -> PolicyAuthority:
    return parse_authority(parse_unique_yaml(text))


def _verify_signature(record: dict[str, Any], authority: PolicyAuthority, purpose: str,
                      *, repository_id: str, target_ref: str) -> None:
    if not authority.enabled or authority.public_key is None or purpose not in authority.purposes:
        raise ApprovalError(f"trusted authority does not allow {purpose}")
    if (repository_id != authority.repository_id or target_ref != authority.target_ref
            or record.get("repository_id") != repository_id
            or record.get("target_ref") != target_ref):
        raise ApprovalError("trusted repository or target ref does not match signed record")
    if record.get("key_id") != authority.key_id:
        raise ApprovalError("signed record does not identify the trusted key")
    signature = _decode(record.get("signature"), 64, "signature")
    body = {key: value for key, value in record.items() if key != "signature"}
    try:
        Ed25519PublicKey.from_public_bytes(authority.public_key).verify(
            signature, canonical_json(body).encode("utf-8")
        )
    except InvalidSignature as exc:
        raise ApprovalError("Ed25519 signature verification failed") from exc


def _verify_rotation(old: PolicyAuthority, new: PolicyAuthority, record: dict[str, Any], *,
                     required_purposes: frozenset[str] = frozenset()) -> None:
    """Validate a signed ordinary rotation after its signature has been verified."""
    if (not old.enabled or not new.enabled or old.repository_id != new.repository_id
            or old.target_ref != new.target_ref):
        raise ApprovalError("rotation cannot change trust identity or enabled state")
    if record.get("predecessor_authority_digest") != old.digest:
        raise ApprovalError("rotation predecessor authority digest does not match")
    if record.get("target_authority_digest") != new.digest:
        raise ApprovalError("rotation target authority digest does not match")
    if not new.purposes <= old.purposes:
        raise ApprovalError("ordinary key rotation cannot add purposes")
    if not required_purposes <= new.purposes:
        raise ApprovalError("rotated key lacks purposes required by the active policy")


def _validate_processes(value: object) -> None:
    if not isinstance(value, list) or not value:
        raise ApprovalError("recovery needs explicitly allowed review processes")
    seen: set[tuple[str, ...]] = set()
    for process in value:
        item = _fields(process, {"kind", "id", "version", "issuer", "evidence_form"},
                       label="recovery process")
        if not isinstance(item["kind"], str) or item["kind"] not in {"plan", "code"}:
            raise ApprovalError("unknown recovery review kind")
        identity = tuple(_text(item[k], k) for k in ("kind", "id", "version", "issuer",
                                                       "evidence_form"))
        if identity in seen:
            raise ApprovalError("duplicate recovery review process")
        seen.add(identity)


def _validate_continuations(value: object) -> None:
    if not isinstance(value, list):
        raise ApprovalError("continued_plans must be a list")
    seen: set[str] = set()
    for continuation in value:
        item = _fields(continuation, {"change_id", "subject_id", "approval_id",
                                      "evidence_digest", "predecessor_policy_digest"},
                       label="continued plan")
        change = _text(item["change_id"], "continued change_id")
        _text(item["subject_id"], "continued subject_id")
        _text(item["approval_id"], "continued approval_id")
        _digest(item["evidence_digest"], "continued evidence digest")
        _digest(item["predecessor_policy_digest"], "continued predecessor digest")
        if change in seen:
            raise ApprovalError("duplicate continued Change")
        seen.add(change)


def _validate_obligation_changes(value: object) -> None:
    if not isinstance(value, list):
        raise ApprovalError("obligation_changes must be a list")
    seen: set[tuple[str, ...]] = set()
    for change in value:
        item = _fields(change, {"kind", "source", "id", "old_digest", "new_digest", "reason"},
                       label="obligation change")
        identity = tuple(_text(item[k], k) for k in ("kind", "source", "id"))
        _digest(item["old_digest"], "old obligation digest")
        if item["new_digest"] is not None:
            _digest(item["new_digest"], "new obligation digest")
        _text(item["reason"], "obligation change reason")
        if identity in seen:
            raise ApprovalError("duplicate obligation change")
        seen.add(identity)


def verify_policy_authorization(
    value: object, authority: PolicyAuthority, *, repository_id: str, target_ref: str,
    base_sha: str, predecessor_policy_digest: str, target_policy_digest: str,
    change_id: str, plan_subject_id: str, actual_paths: list[str],
    target_authority: PolicyAuthority | None = None,
    frozen_plan_paths: list[str] | None = None,
    required_purposes: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Verify a policy authorization against independently resolved expected inputs."""
    if not isinstance(value, dict):
        raise ApprovalError("policy authorization must be an object")
    kind = value.get("kind")
    optional = {"continued_plans", "obligation_changes"}
    extras = {"reason", "review_processes"} if kind == "recovery" else set()
    if kind == "rotate_key":
        extras = {"predecessor_authority_digest", "target_authority_digest"}
    if not isinstance(kind, str) or kind not in {"transition", "recovery", "rotate_key"}:
        raise ApprovalError("unsupported policy authorization kind")
    fields = set(value)
    if not (_AUTH_FIELDS | extras) <= fields or fields - (_AUTH_FIELDS | extras | optional):
        raise ApprovalError("policy authorization has missing or unknown fields")
    if value["version"] != "policy-authorization/v1" or value["decision"] != "approve":
        raise ApprovalError("unsupported policy authorization or non-approval decision")
    if not isinstance(base_sha, str) or _COMMIT.fullmatch(base_sha) is None:
        raise ApprovalError("trusted base must be a full Git object id")
    _digest(predecessor_policy_digest, "predecessor policy digest")
    _digest(target_policy_digest, "target policy digest")
    bindings = {"base_sha": base_sha, "predecessor_policy_digest": predecessor_policy_digest,
                "target_policy_digest": target_policy_digest, "change_id": change_id,
                "plan_subject_id": plan_subject_id}
    if any(not isinstance(expected, str) or not expected or value[key] != expected
           for key, expected in bindings.items()):
        raise ApprovalError("policy authorization does not match its trusted bindings")
    paths = _paths(value["permitted_paths"])
    if not isinstance(actual_paths, list):
        raise ApprovalError("actual delivery paths must be a list")
    for path in actual_paths:
        _paths([path])
    if any(not covered_by_scope(path, paths) for path in actual_paths):
        raise ApprovalError("actual delivery is outside the authorized paths")
    if "continued_plans" in value:
        _validate_continuations(value["continued_plans"])
    if "obligation_changes" in value:
        _validate_obligation_changes(value["obligation_changes"])
    purpose = "policy-recovery" if kind == "recovery" else "policy-transition"
    _verify_signature(value, authority, purpose, repository_id=repository_id,
                      target_ref=target_ref)
    if kind in {"recovery", "rotate_key"}:
        if not frozen_plan_paths:
            raise ApprovalError("authorization needs the frozen plan's exact paths")
        _paths(frozen_plan_paths)
        if any(not path.endswith(".md") for path in frozen_plan_paths):
            raise ApprovalError("frozen plan paths must be Markdown files")
    plan_paths = frozen_plan_paths or []
    if kind == "recovery":
        _text(value["reason"], "recovery reason")
        _validate_processes(value["review_processes"])
        if target_authority is None or target_authority.digest != authority.digest:
            raise ApprovalError("recovery authorization cannot rotate the authority")
        allowed = {".harness/review-recognition.yaml",
                   f".harness/attestations/v3/{change_id}.jsonl", *plan_paths}
        if any(path not in allowed for path in actual_paths):
            raise ApprovalError("recovery delivery includes paths outside the exact allowed scope")
    elif kind == "rotate_key":
        if target_authority is None:
            raise ApprovalError("rotation needs the candidate authority")
        if predecessor_policy_digest != target_policy_digest:
            raise ApprovalError("key rotation cannot also change review recognition policy")
        allowed = {".harness/policy-authority.yaml",
                   f".harness/attestations/v3/{change_id}.jsonl", *plan_paths}
        if any(path not in allowed for path in actual_paths):
            raise ApprovalError("rotation delivery includes paths outside the exact allowed scope")
        _verify_rotation(authority, target_authority, value, required_purposes=required_purposes)
    elif target_authority is None or target_authority.digest != authority.digest:
        raise ApprovalError("transition authorization cannot rotate the authority")
    return dict(value)


def verify_signed_plan_decision(
    value: object, authority: PolicyAuthority, *, repository_id: str, target_ref: str,
    policy_digest: str, change_id: str, subject_id: str, evidence_id: str,
    decision: str, supersedes: str | None,
) -> dict[str, Any]:
    """Verify the signed body and its exact mapping to a plan evidence envelope."""
    record = _fields(value, {"version", "repository_id", "target_ref", "policy_digest",
                             "change_id", "subject_id", "decision", "evidence_id",
                             "supersedes", "key_id", "signature"},
                     label="signed plan decision")
    if record["version"] != "signed-plan-decision/v1" or decision not in {"approve", "reject"}:
        raise ApprovalError("unsupported signed plan decision")
    _digest(policy_digest, "policy digest")
    bindings = {"policy_digest": policy_digest, "change_id": change_id,
                "subject_id": subject_id, "evidence_id": evidence_id,
                "decision": decision, "supersedes": supersedes}
    if any(record[key] != expected for key, expected in bindings.items()):
        raise ApprovalError("signed plan decision does not match its evidence envelope")
    for key in ("change_id", "subject_id", "evidence_id"):
        _text(record[key], key)
    if supersedes is not None:
        _text(supersedes, "supersedes")
    _verify_signature(record, authority, "plan-decision", repository_id=repository_id,
                      target_ref=target_ref)
    return dict(record)


def verify_v2_review_evidence(
    value: object, recognition: Recognition, authority: PolicyAuthority, *,
    repository_id: str, target_ref: str, change_id: str,
) -> dict[str, Any]:
    """Validate kind-specific recognition, provenance and any required signature."""
    evidence = validate_evidence(value, change_id=change_id)
    if recognition.version != "review-recognition/v2" or recognition.policy_digest is None:
        raise ApprovalError("review evidence requires a v2 recognition basis")
    provenance = evidence.get("provenance")
    if (not isinstance(provenance, dict)
            or provenance.get("policy_digest") != recognition.policy_digest):
        raise ApprovalError("review evidence is bound to another recognition policy")
    signed = evidence.get("form", "json") == "signed-plan-decision"
    if signed:
        verify_signed_plan_decision(
            evidence.get("original_evidence"), authority, repository_id=repository_id,
            target_ref=target_ref, policy_digest=recognition.policy_digest, change_id=change_id,
            subject_id=evidence["subject_id"], evidence_id=evidence["evidence_id"],
            decision=evidence["decision"], supersedes=evidence.get("supersedes"),
        )
    if not evidence_is_recognized(evidence, recognition, signed_plan_verified=signed):
        raise ApprovalError("review evidence process, kind, issuer or form is not recognized")
    return evidence


def verify_recovery_evidence(
    evidence: dict[str, Any], authorization: dict[str, Any], authority: PolicyAuthority, *,
    repository_id: str, target_ref: str, base_sha: str, base_policy_digest: str,
    target_policy_digest: str, change_id: str, plan_subject_id: str,
    frozen_plan_paths: list[str], actual_paths: list[str], target_authority: PolicyAuthority,
) -> dict[str, str]:
    """Apply one signed recovery source to one authorized Change and review kind."""
    evidence = validate_evidence(evidence, change_id=change_id)
    if authorization.get("kind") != "recovery":
        raise ApprovalError("review recovery requires a recovery authorization")
    verify_policy_authorization(
        authorization, authority, repository_id=repository_id, target_ref=target_ref,
        base_sha=base_sha, predecessor_policy_digest=base_policy_digest,
        target_policy_digest=target_policy_digest, change_id=change_id,
        plan_subject_id=plan_subject_id, actual_paths=actual_paths,
        frozen_plan_paths=frozen_plan_paths, target_authority=target_authority,
    )
    if evidence["kind"] == "plan" and evidence["subject_id"] != plan_subject_id:
        raise ApprovalError("recovery evidence targets another plan")
    authorization_digest = digest_record(authorization)
    recovery_digest = digest_record({"version": "recovery-recognition/v1",
                                     "base_policy_digest": base_policy_digest,
                                     "authorization_digest": authorization_digest})
    process, form = evidence["process"], evidence.get("form", "json")
    allowed = next((item for item in authorization["review_processes"]
                    if item["kind"] == evidence["kind"] and item["id"] == process["id"]
                    and item["version"] == process["version"]
                    and item["issuer"] == evidence["issuer"]
                    and item["evidence_form"] == form), None)
    if allowed is None:
        raise ApprovalError("review process is outside the recovery authorization")
    recognition = Recognition("review-recognition/v2", allowed["id"], allowed["version"],
                              frozenset({allowed["kind"]}), frozenset({allowed["issuer"]}),
                              frozenset({allowed["evidence_form"]}), {}, recovery_digest)
    verify_v2_review_evidence(evidence, recognition, authority, repository_id=repository_id,
                              target_ref=target_ref, change_id=change_id)
    return {"mode": "recovery", "trusted_base": base_sha, "policy_digest": recovery_digest,
            "authorization_digest": authorization_digest}


def validate_authorization_import(
    root: Path, state: Any, change_id: str, payload: object, *,
    for_use: bool = False, actual_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Recheck an import against the current plan and committed trusted authority."""
    item = _fields(payload, {"authorization", "authorization_digest", "trusted_base",
                             "repository_id", "target_ref", "target_authority"},
                   label="policy authorization import")
    if state is None:
        raise ApprovalError("policy authorization requires an existing Change")
    allowed_import_states = {"AWAITING_PLAN_REVIEW", "PLAN_APPROVED", "PLAN_REJECTED"}
    if not for_use and state.current_state not in allowed_import_states:
        raise ApprovalError("policy authorization must be imported before implementation starts")
    record = item["authorization"]
    if not isinstance(record, dict) or item["authorization_digest"] != digest_record(record):
        raise ApprovalError("policy authorization digest does not match")
    candidate = state.pending_revision
    pending = (candidate.get("subject") if isinstance(candidate, dict)
               and candidate.get("status") != "withdrawn" else None)
    effective = (state.effective_approval.get("subject")
                 if isinstance(state.effective_approval, dict) else None)
    subject = next((choice for choice in (pending, effective) if isinstance(choice, dict)
                    and choice.get("subject_id") == record.get("plan_subject_id")), None)
    plan = validate_plan_subject(subject, change_id=change_id)
    plan_paths = [artifact["path"] for artifact in plan["artifacts"]
                  if artifact.get("role") == "plan"]
    if not plan_paths:
        raise ApprovalError("policy authorization needs a frozen plan artifact")
    base = resolve_contract_base(root)
    if item["trusted_base"] != base:
        raise ApprovalError("trusted baseline changed before policy authorization import")
    authority_text = regular_blob_text(root, base, ".harness/policy-authority.yaml")
    authority = parse_authority_yaml(authority_text)
    policy_raw = parse_unique_yaml(
        regular_blob_text(root, base, ".harness/review-recognition.yaml")
    )
    required_purposes: frozenset[str] = frozenset()
    if isinstance(policy_raw, dict) and policy_raw.get("version") == "review-recognition/v2":
        from keepsail.core.effective_policy import load_effective_v2

        snapshot = load_effective_v2(root, base)
        predecessor_digest = snapshot.policy.policy_digest
        plan_recognition = snapshot.policy.recognition_for("plan")
        if plan_recognition and "signed-plan-decision" in plan_recognition.evidence_forms:
            required_purposes = frozenset({"plan-decision"})
    else:
        recognition = load_recognition(root, ref=base)
        if recognition.policy_digest is None:
            raise ApprovalError("trusted review recognition has no digest")
        predecessor_digest = recognition.policy_digest
    target_raw = item["target_authority"]
    if record.get("kind") == "rotate_key":
        if target_raw is None:
            raise ApprovalError("rotation import needs the proposed authority configuration")
        target = parse_authority(target_raw)
    else:
        if target_raw is not None:
            raise ApprovalError("only rotation may supply a target authority")
        target = authority
    paths = actual_paths or []
    if for_use and actual_paths is not None:
        from keepsail.core.delivery_policy import parse_delivery_policy_yaml

        head = resolve_commit(root)
        candidate_text = regular_blob_text(root, head, ".harness/review-recognition.yaml")
        candidate_raw = parse_unique_yaml(candidate_text)
        if (record.get("kind") == "rotate_key" and isinstance(candidate_raw, dict)
                and candidate_raw.get("version") == "review-recognition/v1"):
            candidate = _recognition_from_mapping(candidate_raw)
        else:
            candidate = parse_delivery_policy_yaml(candidate_text)
        if candidate.policy_digest != record.get("target_policy_digest"):
            raise ApprovalError("target policy does not match the signed authorization")
        candidate_authority = regular_blob_text(root, head, ".harness/policy-authority.yaml")
        actual_authority = parse_authority_yaml(candidate_authority)
        if record.get("kind") == "rotate_key" and actual_authority.digest != target.digest:
            raise ApprovalError("rotation authority differs from the imported proposal")
        target = actual_authority
    repository = _text(item["repository_id"], "repository_id")
    target_ref = _target_ref(item["target_ref"])
    verify_policy_authorization(
        record, authority, repository_id=repository, target_ref=target_ref, base_sha=base,
        predecessor_policy_digest=predecessor_digest,
        target_policy_digest=_digest(record.get("target_policy_digest"), "target policy digest"),
        change_id=change_id,
        plan_subject_id=plan["subject_id"], actual_paths=paths, target_authority=target,
        frozen_plan_paths=plan_paths, required_purposes=required_purposes,
    )
    return dict(item)
