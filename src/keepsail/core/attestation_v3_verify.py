"""Offline v3 transition and activation replay against committed Git authority."""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
from pathlib import Path
from typing import Any, ParamSpec, TypeVar

from keepsail.core.approval import (
    ApprovalError,
    evidence_is_recognized,
    load_recognition,
    validate_approval,
    validate_code_subject,
)
from keepsail.core.attestation_format import expand_attestation
from keepsail.core.attestation_replay import (
    _knowledge_attestation,
    _new_contract_blockers,
    check_recognized_attestation,
    derive_independence,
    events_from_stateful_attestation,
    gate_bypass_disclosure,
)
from keepsail.core.attestation_v3 import parse_v3_line, validate_v3
from keepsail.core.delivery_policy import parse_delivery_policy_yaml
from keepsail.core.git_diff import parse_name_status_z, require_literal_paths
from keepsail.core.git_objects import regular_blob_bytes, regular_blob_text
from keepsail.core.policy_authority import (
    parse_authority_yaml,
    parse_unique_yaml,
    verify_policy_authorization,
    verify_recovery_evidence,
    verify_v2_review_evidence,
)
from keepsail.core.policy_obligations import changed_obligations, require_signed_obligation_changes
from keepsail.core.policy_snapshot import read_policy_snapshot
from keepsail.core.reducer import derive_state
from keepsail.core.scope_match import is_ancestor, resolve_commit
from keepsail.core.verification_config import parse_verification_config, required_check_contract
from keepsail.core.verification_evidence import verify_check_evidence

_P = ParamSpec("_P")
_R = TypeVar("_R")
_activation_results: ContextVar[dict[tuple[str, str, str, str], dict[str, Any] | None] | None] = (
    ContextVar("keepsail_activation_replay", default=None)
)


@contextmanager
def activation_replay_scope() -> Iterator[None]:
    """Share committed activation replay only inside one operation or CLI invocation."""
    if _activation_results.get() is not None:
        yield
        return
    token = _activation_results.set({})
    try:
        yield
    finally:
        _activation_results.reset(token)


def _with_activation_scope(function: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(function)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with activation_replay_scope():
            return function(*args, **kwargs)
    return wrapped


@_with_activation_scope
def verify_v3_transition(
    root: Path, value: object, *, base: str, head: str, repository_id: str, target_ref: str,
) -> dict[str, Any]:
    """Replay an activation using the old v1 baseline and committed Git objects."""
    record = validate_v3(value)
    base_sha, head_sha = resolve_commit(root, base), resolve_commit(root, head)
    if record["trusted_base"] != base_sha:
        raise ApprovalError("v3 attestation is bound to a different trusted base")
    recognition = load_recognition(root, ref=base_sha)
    if record["policy_digest"] != recognition.policy_digest or not recognition.policy_digest:
        raise ApprovalError("v3 attestation is bound to a different trusted policy")
    change = record["change_id"]
    snapshot = record["snapshot"]
    approval = validate_approval(snapshot.get("approval"), change_id=change)
    code = validate_code_subject(snapshot.get("code_subject"), change_id=change)
    plan_paths = [item["path"] for item in approval["subject"]["artifacts"]
                  if item.get("role") == "plan"]
    paths = sorted({path for row in code["manifest"]
                    for path in (row.get("old_path"), row.get("path")) if isinstance(path, str)})
    try:
        raw_diff = subprocess.check_output(
            ["git", "diff", "--name-status", "-z", "--find-renames", f"{base_sha}...{head_sha}"],
            cwd=root,
        ).decode("utf-8")
        entries = parse_name_status_z(raw_diff)
        require_literal_paths(entries)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError, ValueError) as exc:
        raise ApprovalError(f"cannot inspect v3 Git diff: {exc}") from exc
    attestation_path = f".harness/attestations/v3/{change}.jsonl"
    if not any(entry.status == "A" and entry.paths == (attestation_path,) for entry in entries):
        raise ApprovalError("v3 activation attestation must be newly added in the exact diff")
    if parse_v3_line(regular_blob_bytes(root, head_sha, attestation_path)) != record:
        raise ApprovalError("v3 attestation does not match the committed Git blob")
    candidate = parse_delivery_policy_yaml(regular_blob_text(root, head_sha,
                                                              ".harness/review-recognition.yaml"))
    if candidate.activation != {"kind": "transition", "change": change}:
        raise ApprovalError("v3 activation does not identify this transition")
    old_config = parse_verification_config(regular_blob_text(root, base_sha,
                                                              ".harness/verification.yaml"))
    new_config = parse_verification_config(regular_blob_text(root, head_sha,
                                                              ".harness/verification.yaml"),
                                           strict=True)
    old_checks = required_check_contract(old_config)
    new_checks = required_check_contract(new_config)
    if candidate.required_checks_digest != new_checks["digest"]:
        raise ApprovalError("candidate required checks do not match the target policy")
    authority = parse_authority_yaml(regular_blob_text(root, base_sha,
                                                       ".harness/policy-authority.yaml"))
    target_authority = parse_authority_yaml(regular_blob_text(root, head_sha,
                                                              ".harness/policy-authority.yaml"))
    authorization = record["authorization"]
    if not isinstance(authorization, dict) or authorization.get("kind") not in {
        "transition", "recovery"
    }:
        raise ApprovalError("v3 policy transition requires its signed authorization")
    verify_policy_authorization(
        authorization, authority, repository_id=repository_id, target_ref=target_ref,
        base_sha=base_sha, predecessor_policy_digest=recognition.policy_digest,
        target_policy_digest=candidate.policy_digest, change_id=change,
        plan_subject_id=approval["subject_id"], actual_paths=paths,
        target_authority=target_authority, frozen_plan_paths=plan_paths,
    )
    changes = changed_obligations(
        old_processes={kind: recognition for kind in recognition.kinds}, old_code_review="full",
        old_scope=(), old_builtin="keepsail-baseline/v1", old_checks=old_checks,
        new_policy=candidate, new_checks=new_checks,
    )
    require_signed_obligation_changes(changes, authorization)

    def verify_review(evidence: dict[str, Any], kind: str) -> None:
        basis = record["recognition_basis"][kind]
        if not isinstance(basis, dict):
            raise ApprovalError(f"missing {kind} recognition basis")
        if basis["mode"] == "current":
            provenance = evidence.get("provenance")
            if (not evidence_is_recognized(evidence, recognition)
                    or not isinstance(provenance, dict)
                    or provenance.get("policy_digest") != recognition.policy_digest):
                raise ApprovalError("review does not match the trusted old recognition")
        elif basis["mode"] == "recovery":
            observed = verify_recovery_evidence(
                evidence, authorization, authority, repository_id=repository_id,
                target_ref=target_ref, base_sha=base_sha,
                base_policy_digest=record["policy_digest"],
                target_policy_digest=candidate.policy_digest, change_id=change,
                plan_subject_id=approval["subject_id"], frozen_plan_paths=plan_paths,
                actual_paths=paths, target_authority=target_authority,
            )
            if {k: v for k, v in observed.items() if k != "trusted_base"} != basis:
                raise ApprovalError("recovery review basis differs from its signed authorization")
        else:
            raise ApprovalError("continued-plan basis needs an activated v2 predecessor")

    lines = expand_attestation(snapshot, for_v3=True)
    with tempfile.TemporaryDirectory(prefix="keepsail-v3-replay-") as temp:
        path = Path(temp) / "lifecycle.jsonl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        blockers = check_recognized_attestation(path, change)
        state = derive_state(path).get(change)
        if state is None:
            raise ApprovalError("v3 lifecycle has no matching Change")
        blockers.extend(_new_contract_blockers(
            root, state, change, entries, recognition=recognition, base=base_sha, head=head_sha,
            attestation_path=path, evidence_validator=verify_review,
        ))
        _knowledge_attestation(root, path, state, base=base_sha, head=head_sha)
        events = events_from_stateful_attestation(root, change, path=path)
        disclosure = gate_bypass_disclosure(events)
        independence = derive_independence(events)
        if disclosure["undisclosed"]:
            blockers.append("gate bypass lacks its required disclosure")
        for kind in ("plan_review", "code_review"):
            if independence[kind]["skipped"] and not independence[kind]["override"]:
                blockers.append(f"{kind} was skipped without the required override")
        verify_check_evidence(state.current_verification, subject_id=code["subject_id"],
                              required_contract=old_checks, builtin_version="keepsail-baseline/v1",
                              trusted_base=base_sha)
        if blockers:
            raise ApprovalError("; ".join(blockers))
    return {"change": change, "trusted_base": base_sha, "head": head_sha,
            "policy_digest": recognition.policy_digest,
            "target_policy_digest": candidate.policy_digest,
            "required_checks_digest": old_checks["digest"],
            "coverage": [row["path"] for row in state.coverage_manifest],
            "independence": independence, "gate_bypass": disclosure}


def _introduction_commit(root: Path, trusted: str, path: str) -> str:
    try:
        introductions = subprocess.check_output(
            ["git", "log", "--format=%H", "--diff-filter=A", "--no-renames", trusted,
             "--", path], cwd=root, text=True, encoding="utf-8",
        ).splitlines()
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise ApprovalError("cannot locate the attestation introduction") from exc
    if len(introductions) != 1:
        raise ApprovalError("attestation introduction is missing or ambiguous")
    return resolve_commit(root, introductions[0])


@_with_activation_scope
def verify_v2_activation(
    root: Path, *, trusted_commit: str, repository_id: str, target_ref: str,
) -> dict[str, Any]:
    """Replay an activation, avoiding repeated ancestor replay within this call."""
    commit = resolve_commit(root, trusted_commit)
    cache = _activation_results.get()
    assert cache is not None
    key = (str(root.resolve()), commit, repository_id, target_ref)
    if key in cache:
        result = cache[key]
        if result is None:
            raise ApprovalError("cyclic policy activation chain")
        return deepcopy(result)
    cache[key] = None
    try:
        result = _verify_v2_activation(root, trusted_commit=commit, repository_id=repository_id,
                                       target_ref=target_ref)
        cache[key] = deepcopy(result)
        return result
    except Exception:
        del cache[key]
        raise


def _verify_v2_activation(
    root: Path, *, trusted_commit: str, repository_id: str, target_ref: str,
) -> dict[str, Any]:
    """Replay the exact transition that introduced the active policy's attestation."""
    snapshot = read_policy_snapshot(root, trusted_commit, repository_id=repository_id,
                                    target_ref=target_ref)
    if snapshot.policy.activation["kind"] == "initial":
        from keepsail.core.initial_policy import verify_initial_policy

        initial = verify_initial_policy(root, snapshot, repository_id=repository_id,
                                        target_ref=target_ref)
        rotation = None
        if initial["initial_authority_digest"] != snapshot.authority.digest:
            rotation = _verify_current_rotation(
                root, snapshot.commit, snapshot.policy.policy_digest, snapshot.authority.digest,
                repository_id, target_ref,
            )
        return {"trusted_base": snapshot.commit, "activation_commit": initial["initial_commit"],
                "predecessor_base": None, "policy_digest": snapshot.policy.policy_digest,
                "required_checks_digest": snapshot.checks["digest"], "change": None,
                "initial_confirmation": initial["confirmation"],
                "confirmation_assurance": initial["confirmation_assurance"],
                "authority_rotation": rotation}
    change = snapshot.policy.activation["change"]
    path = f".harness/attestations/v3/{change}.jsonl"
    trusted_bytes = regular_blob_bytes(root, snapshot.commit, path)
    record = parse_v3_line(trusted_bytes)
    if record["change_id"] != change:
        raise ApprovalError("active policy refers to another transition Change")
    introduction = _introduction_commit(root, snapshot.commit, path)
    predecessor = record["trusted_base"]
    if (predecessor == introduction or not is_ancestor(root, predecessor, introduction)
            or not is_ancestor(root, introduction, snapshot.commit)):
        raise ApprovalError("activation or its predecessor is not reachable from trusted base")
    if regular_blob_bytes(root, introduction, path) != trusted_bytes:
        raise ApprovalError("active activation attestation changed after its introduction")
    introduced_authority = parse_authority_yaml(
        regular_blob_text(root, introduction, ".harness/policy-authority.yaml")
    )
    predecessor_policy = parse_unique_yaml(regular_blob_text(
        root, predecessor, ".harness/review-recognition.yaml"
    ))
    verifier = (verify_v3_delivery if isinstance(predecessor_policy, dict)
                and predecessor_policy.get("version") == "review-recognition/v2"
                else verify_v3_transition)
    result = verifier(root, record, base=predecessor, head=introduction,
                      repository_id=repository_id, target_ref=target_ref)
    if result["target_policy_digest"] != snapshot.policy.policy_digest:
        raise ApprovalError("active policy does not match the replayed transition")
    rotation = None
    if introduced_authority.digest != snapshot.authority.digest:
        rotation = _verify_current_rotation(root, snapshot.commit, snapshot.policy.policy_digest,
                                            snapshot.authority.digest, repository_id, target_ref)
    return {"trusted_base": snapshot.commit, "activation_commit": introduction,
            "predecessor_base": predecessor, "policy_digest": snapshot.policy.policy_digest,
            "required_checks_digest": snapshot.checks["digest"], "change": change,
            "authority_rotation": rotation}


def _verify_current_rotation(root: Path, trusted: str, policy_digest: str, authority_digest: str,
                             repository_id: str, target_ref: str) -> dict[str, str]:
    """Find and replay the unique rotation that established the current key."""
    try:
        raw_paths = subprocess.check_output(
            ["git", "ls-tree", "-r", "-z", "--name-only", trusted, "--",
             ".harness/attestations/v3"], cwd=root,
        ).decode("utf-8")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise ApprovalError("cannot enumerate trusted v3 attestations") from exc
    if raw_paths and not raw_paths.endswith("\0"):
        raise ApprovalError("incomplete trusted attestation listing")
    matches: list[tuple[str, dict[str, Any], bytes]] = []
    for path in raw_paths.split("\0"):
        if not path or not path.endswith(".jsonl"):
            continue
        data = regular_blob_bytes(root, trusted, path)
        record = parse_v3_line(data)
        if path != f".harness/attestations/v3/{record['change_id']}.jsonl":
            raise ApprovalError("trusted v3 attestation path does not match its Change")
        authorization = record["authorization"]
        if (isinstance(authorization, dict) and authorization.get("kind") == "rotate_key"
                and authorization.get("target_authority_digest") == authority_digest
                and record["policy_digest"] == policy_digest):
            matches.append((path, record, data))
    if len(matches) != 1:
        raise ApprovalError("current authority has no unique retained rotation")
    path, record, data = matches[0]
    introduction = _introduction_commit(root, trusted, path)
    predecessor = record["trusted_base"]
    if (predecessor == introduction or not is_ancestor(root, predecessor, introduction)
            or not is_ancestor(root, introduction, trusted)
            or regular_blob_bytes(root, introduction, path) != data):
        raise ApprovalError("rotation evidence or its predecessor is not reachable unchanged")
    result = verify_v3_delivery(root, record, base=predecessor, head=introduction,
                                repository_id=repository_id, target_ref=target_ref)
    if result["target_policy_digest"] != policy_digest:
        raise ApprovalError("rotation changed the active policy")
    return {"change": record["change_id"], "commit": introduction,
            "predecessor_base": predecessor, "authority_digest": authority_digest}


@_with_activation_scope
def verify_v3_delivery(
    root: Path, value: object, *, base: str, head: str, repository_id: str, target_ref: str,
) -> dict[str, Any]:
    """Replay delivery and any signed transition under the active v2 obligations."""
    from keepsail.core.effective_policy import continued_plan_basis

    record = validate_v3(value)
    base_sha, head_sha = resolve_commit(root, base), resolve_commit(root, head)
    verify_v2_activation(root, trusted_commit=base_sha, repository_id=repository_id,
                         target_ref=target_ref)
    snapshot = read_policy_snapshot(root, base_sha, repository_id=repository_id,
                                    target_ref=target_ref)
    from keepsail.core.git_objects import optional_regular_blob_bytes
    from keepsail.core.initial_policy import INITIAL_CONFIRMATION

    initial_confirmation = optional_regular_blob_bytes(root, base_sha, INITIAL_CONFIRMATION)
    if (initial_confirmation is not None and optional_regular_blob_bytes(
            root, head_sha, INITIAL_CONFIRMATION) != initial_confirmation):
        raise ApprovalError("retained initial trust confirmation cannot be changed or removed")
    candidate = read_policy_snapshot(root, head_sha, repository_id=repository_id,
                                     target_ref=target_ref)
    if (record["trusted_base"] != base_sha
            or record["policy_digest"] != snapshot.policy.policy_digest):
        raise ApprovalError("delivery does not use the active trusted policy")
    change = record["change_id"]
    code = validate_code_subject(record["snapshot"].get("code_subject"), change_id=change)
    approval = validate_approval(record["snapshot"].get("approval"), change_id=change)
    plan_paths = [item["path"] for item in approval["subject"]["artifacts"]
                  if item.get("role") == "plan"]
    actual_paths = sorted({path for row in code["manifest"]
                           for path in (row.get("old_path"), row.get("path"))
                           if isinstance(path, str)})
    policy_changed = candidate.policy.policy_digest != snapshot.policy.policy_digest
    authority_changed = candidate.authority.digest != snapshot.authority.digest
    checks_changed = candidate.checks["digest"] != snapshot.checks["digest"]
    authorization = record["authorization"]
    if not policy_changed and not authority_changed:
        if checks_changed or authorization is not None:
            raise ApprovalError("ordinary delivery changes obligations or has unused authorization")
    else:
        if not isinstance(authorization, dict):
            raise ApprovalError("policy or authority change needs its signed authorization")
        kind = authorization.get("kind")
        if authority_changed:
            if kind != "rotate_key" or policy_changed or checks_changed:
                raise ApprovalError("rotation must change only the authority")
        elif (kind not in {"transition", "recovery"}
              or candidate.policy.activation != {"kind": "transition", "change": change}):
            raise ApprovalError("target policy does not identify this signed transition")
        required_purposes: frozenset[str] = frozenset()
        plan_process = snapshot.policy.recognition_for("plan")
        if plan_process and "signed-plan-decision" in plan_process.evidence_forms:
            required_purposes = frozenset({"plan-decision"})
        verify_policy_authorization(
            authorization, snapshot.authority, repository_id=repository_id, target_ref=target_ref,
            base_sha=base_sha, predecessor_policy_digest=snapshot.policy.policy_digest,
            target_policy_digest=candidate.policy.policy_digest, change_id=change,
            plan_subject_id=approval["subject_id"], actual_paths=actual_paths,
            target_authority=candidate.authority, frozen_plan_paths=plan_paths,
            required_purposes=required_purposes,
        )
        if policy_changed:
            old_processes = {kind: process for kind in ("plan", "code")
                             if (process := snapshot.policy.recognition_for(kind))}
            changes = changed_obligations(
                old_processes=old_processes, old_code_review=snapshot.policy.code_review,
                old_scope=snapshot.policy.scope, old_builtin=snapshot.policy.builtin_checks_version,
                old_checks=snapshot.checks, new_policy=candidate.policy,
                new_checks=candidate.checks,
            )
            require_signed_obligation_changes(changes, authorization)
        elif authorization.get("obligation_changes", []):
            raise ApprovalError("key rotation cannot change delivery obligations")
    required, reason = snapshot.policy.review_requirement(code["manifest"])
    if (record["recognition_basis"]["code"] is None) != (not required):
        raise ApprovalError("v3 code recognition basis disagrees with the active policy")
    path = f".harness/attestations/v3/{change}.jsonl"
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--name-status", "-z", "--find-renames", f"{base_sha}...{head_sha}"],
            cwd=root,
        ).decode("utf-8")
        entries = parse_name_status_z(diff)
        require_literal_paths(entries)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError, ValueError) as exc:
        raise ApprovalError(f"cannot inspect ordinary delivery Git diff: {exc}") from exc
    if not any(entry.status == "A" and entry.paths == (path,) for entry in entries):
        raise ApprovalError("ordinary v3 attestation must be newly added in the exact diff")
    if parse_v3_line(regular_blob_bytes(root, head_sha, path)) != record:
        raise ApprovalError("ordinary v3 attestation differs from its committed Git blob")
    plan_recognition = snapshot.policy.recognition_for("plan")
    if plan_recognition is None:
        raise ApprovalError("active policy has no plan review process")
    lines = expand_attestation(record["snapshot"], for_v3=True)
    with tempfile.TemporaryDirectory(prefix="keepsail-v3-delivery-") as temp:
        replay_path = Path(temp) / "lifecycle.jsonl"
        replay_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        state = derive_state(replay_path).get(change)
        if state is None:
            raise ApprovalError("ordinary v3 lifecycle has no matching Change")

        def verify_review(evidence: dict[str, Any], kind: str) -> None:
            claimed = record["recognition_basis"][kind]
            if not isinstance(claimed, dict):
                raise ApprovalError(f"missing {kind} recognition basis")
            if kind == "plan" and claimed["mode"] == "continued_plan":
                actual = continued_plan_basis(root, snapshot, state, evidence)
                if {k: v for k, v in actual.items() if k != "trusted_base"} != claimed:
                    raise ApprovalError("continued plan basis does not match the signed list")
                return
            if claimed["mode"] == "recovery":
                if not isinstance(authorization, dict):
                    raise ApprovalError("recovery basis has no signed authorization")
                actual = verify_recovery_evidence(
                    evidence, authorization, snapshot.authority, repository_id=repository_id,
                    target_ref=target_ref, base_sha=base_sha,
                    base_policy_digest=snapshot.policy.policy_digest,
                    target_policy_digest=candidate.policy.policy_digest, change_id=change,
                    plan_subject_id=approval["subject_id"], frozen_plan_paths=plan_paths,
                    actual_paths=actual_paths, target_authority=candidate.authority,
                )
                if {k: v for k, v in actual.items() if k != "trusted_base"} != claimed:
                    raise ApprovalError("recovery basis differs from signed authorization")
                return
            recognition = snapshot.policy.recognition_for(kind)
            if claimed["mode"] != "current" or recognition is None:
                raise ApprovalError("review is not recognized by the active policy")
            verify_v2_review_evidence(evidence, recognition, snapshot.authority,
                                      repository_id=repository_id, target_ref=target_ref,
                                      change_id=change)

        blockers = check_recognized_attestation(
            replay_path, change, builtin_version=snapshot.policy.builtin_checks_version,
            repository_root=root, code_review_required=required,
        )
        blockers.extend(_new_contract_blockers(
            root, state, change, entries, recognition=plan_recognition, base=base_sha,
            head=head_sha, attestation_path=replay_path, evidence_validator=verify_review,
            code_review_required=required,
        ))
        _knowledge_attestation(root, replay_path, state, base=base_sha, head=head_sha)
        events = events_from_stateful_attestation(root, change, path=replay_path)
        disclosure = gate_bypass_disclosure(events)
        independence = derive_independence(events)
        if disclosure["undisclosed"]:
            blockers.append("gate bypass lacks its required disclosure")
        for kind in ("plan_review", "code_review"):
            if independence[kind]["skipped"] and not independence[kind]["override"]:
                blockers.append(f"{kind} was skipped without the required override")
        verify_check_evidence(state.current_verification, subject_id=code["subject_id"],
                              required_contract=snapshot.checks,
                              builtin_version=snapshot.policy.builtin_checks_version,
                              trusted_base=base_sha)
        if blockers:
            raise ApprovalError("; ".join(blockers))
    return {"change": change, "trusted_base": base_sha, "head": head_sha,
            "policy_digest": snapshot.policy.policy_digest,
            "target_policy_digest": candidate.policy.policy_digest,
            "required_checks_digest": snapshot.checks["digest"],
            "code_review_required": required, "code_review_reason": reason,
            "coverage": [row["path"] for row in state.coverage_manifest],
            "independence": independence, "gate_bypass": disclosure}
