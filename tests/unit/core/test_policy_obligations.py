from copy import deepcopy
from types import SimpleNamespace

import pytest

from keepsail.core.approval import ApprovalError, Recognition, digest_record
from keepsail.core.delivery_policy import parse_delivery_policy
from keepsail.core.policy_obligations import changed_obligations, require_signed_obligation_changes
from keepsail.engineering.verification_config import (
    parse_verification_config,
    required_check_contract,
)


def setup_policy(mode="full", scope=None):
    process = {"id": "existing", "version": "v1", "issuers": ["reviewer"],
               "evidence_forms": ["json"], "requirements": {}}
    checks = required_check_contract(parse_verification_config(
        "checks:\n  - id: test\n    command: [python, -m, pytest]\n", strict=True))
    code_review = {"mode": mode}
    if mode == "scope":
        code_review["scope"] = scope or ["src"]
    raw = {"version": "review-recognition/v2", "enabled": True,
           "processes_by_kind": {"plan": deepcopy(process), "code": deepcopy(process)},
           "code_review": code_review, "required_checks_digest": checks["digest"],
           "builtin_checks_version": "keepsail-baseline/v1", "activation": {"kind": "initial"}}
    raw["policy_digest"] = digest_record(raw)
    old = Recognition("review-recognition/v1", "existing", "v1", frozenset({"plan", "code"}),
                      frozenset({"reviewer"}), frozenset({"json"}), {}, "a" * 64)
    return raw, {"plan": old, "code": old}, checks


def compare(raw, old, before, after=None, *, old_mode="full", old_scope=()):
    raw = deepcopy(raw)
    raw["policy_digest"] = digest_record({k: v for k, v in raw.items() if k != "policy_digest"})
    return changed_obligations(old_processes=old, old_code_review=old_mode, old_scope=old_scope,
                               old_builtin="keepsail-baseline/v1", old_checks=before,
                               new_policy=parse_delivery_policy(raw), new_checks=after or before)


def test_existing_v1_obligations_map_to_full_v2_without_weakening():
    raw, old, checks = setup_policy()
    assert compare(raw, old, checks) == []


def test_reduced_review_changed_checks_and_builtin_change_need_exact_signed_inventory():
    raw, old, checks = setup_policy()
    raw["code_review"] = {"mode": "off"}
    raw["processes_by_kind"].pop("code")
    raw["builtin_checks_version"] = "keepsail-baseline/v2"
    after = deepcopy(checks)
    after["checks"] = []
    after["layers"]["baseline"] = False
    after["digest"] = digest_record({k: v for k, v in after.items() if k != "digest"})
    changes = compare(raw, old, checks, after)
    assert {(x["kind"], x["id"]) for x in changes} == {
        ("recognition", "code"), ("code_review", "scope"), ("required_check", "test"),
        ("builtin_contract", "version"), ("builtin_contract", "enabled"),
    }
    signed = [{**item, "reason": "owner explicitly accepts this change"} for item in changes]
    require_signed_obligation_changes(changes, {"obligation_changes": signed})
    with pytest.raises(ApprovalError, match="exactly authorized"):
        require_signed_obligation_changes(changes, {"obligation_changes": signed[:-1]})
    altered = deepcopy(signed)
    altered[0]["old_digest"] = "f" * 64
    with pytest.raises(ApprovalError, match="exactly authorized"):
        require_signed_obligation_changes(changes, {"obligation_changes": altered})


def test_scope_may_become_broader_without_dropping_the_old_review_requirement():
    raw, old, checks = setup_policy("scope", ["src"])
    assert compare(raw, old, checks, old_mode="scope", old_scope=("src/secure",)) == []
    raw["code_review"]["scope"] = ["src/secure"]
    changes = compare(raw, old, checks, old_mode="scope", old_scope=("src",))
    assert [(x["kind"], x["id"]) for x in changes] == [("code_review", "scope")]


def test_scoped_v1_to_v2_requires_authorizing_the_effective_review_reduction():
    raw, old, checks = setup_policy("scope", ["src"])
    raw["builtin_checks_version"] = "keepsail-baseline/v2"
    changes = compare(raw, old, checks, old_mode="scope", old_scope=("src",))
    assert {item["kind"] for item in changes} == {"code_review", "builtin_contract"}
    parsed = parse_delivery_policy(raw | {"policy_digest": digest_record(
        {k: v for k, v in raw.items() if k != "policy_digest"})})
    historical = changed_obligations(
        old_processes=old, old_code_review="scope", old_scope=("src",),
        old_builtin="keepsail-baseline/v1", old_checks=checks, new_policy=parsed,
        new_checks=checks, historical_replay=True,
    )
    assert [item["kind"] for item in historical] == ["builtin_contract"]
    current_signed = [{**item, "reason": "owner explicitly approves"} for item in changes]
    historical_signed = [{**item, "reason": "owner explicitly approved"} for item in historical]
    require_signed_obligation_changes(changes, {"obligation_changes": current_signed},
                                      historical_changes=historical)
    require_signed_obligation_changes(changes, {"obligation_changes": historical_signed},
                                      historical_changes=historical)
    with pytest.raises(ApprovalError, match="exactly authorized"):
        require_signed_obligation_changes(changes, {"obligation_changes": historical_signed})


def test_narrowing_scoped_v1_names_its_effective_full_review_obligation():
    raw, old, checks = setup_policy("scope", ["src/secure"])
    raw["builtin_checks_version"] = "keepsail-baseline/v2"
    changes = compare(raw, old, checks, old_mode="scope", old_scope=("src",))
    review = next(item for item in changes if item["kind"] == "code_review")
    assert review["old_digest"] == digest_record({"mode": "full", "scope": []})


def test_merge_rejects_initial_activation_over_an_active_policy(tmp_path, monkeypatch):
    from keepsail.core import attestation_v3_verify as replay
    from keepsail.core import git_objects

    old_raw, _, checks = setup_policy("full")
    old = parse_delivery_policy(old_raw)
    new_raw = deepcopy(old_raw)
    new_raw["code_review"] = {"mode": "off"}
    new_raw["builtin_checks_version"] = "keepsail-baseline/v2"
    new_raw["policy_digest"] = digest_record({k: v for k, v in new_raw.items()
                                             if k != "policy_digest"})
    candidate = parse_delivery_policy(new_raw)
    authority = SimpleNamespace(digest="same-authority")
    before = SimpleNamespace(policy=old, authority=authority, checks=checks)
    after = SimpleNamespace(policy=candidate, authority=authority, checks=checks)
    record = {"trusted_base": "base", "policy_digest": old.policy_digest,
              "change_id": "delivery", "snapshot": {},
              "authorization": {"kind": "transition"}}
    monkeypatch.setattr(replay, "validate_v3", lambda value: value)
    monkeypatch.setattr(replay, "resolve_commit", lambda root, ref: ref)
    monkeypatch.setattr(replay, "verify_v2_activation", lambda *args, **kwargs: None)
    monkeypatch.setattr(replay, "read_policy_snapshot",
                        lambda root, ref, **kwargs: before if ref == "base" else after)
    monkeypatch.setattr(git_objects, "optional_regular_blob_bytes", lambda *args: None)
    monkeypatch.setattr(replay, "validate_code_subject", lambda *args, **kwargs: {"manifest": []})
    monkeypatch.setattr(replay, "validate_approval", lambda *args, **kwargs: {
        "subject_id": "plan:test", "subject": {"artifacts": []}})
    with pytest.raises(ApprovalError, match="target policy does not identify this signed"):
        replay.verify_v3_delivery(tmp_path, record, base="base", head="head",
                                  repository_id="owner/project", target_ref="refs/heads/main")


@pytest.mark.parametrize(("replaying", "old_inventory", "accepted"), [
    (False, False, True), (True, False, True), (True, True, True), (False, True, False),
])
def test_v3_replay_uses_the_signed_current_or_historical_inventory(
    tmp_path, monkeypatch, replaying, old_inventory, accepted,
):
    from keepsail.core import attestation_v3_verify as replay
    from keepsail.core import git_objects
    from keepsail.core.delivery_policy import DeliveryPolicy

    raw, _, checks = setup_policy("scope", ["src"])
    old_policy = parse_delivery_policy(raw)
    raw["builtin_checks_version"] = "keepsail-baseline/v2"
    raw["activation"] = {"kind": "transition", "change": "delivery"}
    raw["policy_digest"] = digest_record({k: v for k, v in raw.items() if k != "policy_digest"})
    target = parse_delivery_policy(raw)
    processes = {kind: old_policy.recognition_for(kind) for kind in ("plan", "code")}
    assert all(processes.values())
    args = dict(old_processes=processes, old_code_review="scope", old_scope=("src",),
                old_builtin="keepsail-baseline/v1", old_checks=checks, new_policy=target,
                new_checks=checks)
    changes = changed_obligations(**args, historical_replay=old_inventory)
    signed = [{**item, "reason": "owner explicitly approved"} for item in changes]
    authority = SimpleNamespace(digest="same-authority")
    before = SimpleNamespace(policy=old_policy, authority=authority, checks=checks)
    after = SimpleNamespace(policy=target, authority=authority, checks=checks)
    record = {"trusted_base": "base", "policy_digest": old_policy.policy_digest,
              "change_id": "delivery", "snapshot": {},
              "authorization": {"kind": "transition", "obligation_changes": signed}}
    monkeypatch.setattr(replay, "validate_v3", lambda value: value)
    monkeypatch.setattr(replay, "resolve_commit", lambda root, ref: ref)
    monkeypatch.setattr(replay, "verify_v2_activation", lambda *args, **kwargs: None)
    monkeypatch.setattr(replay, "read_policy_snapshot",
                        lambda root, ref, **kwargs: before if ref == "base" else after)
    monkeypatch.setattr(git_objects, "optional_regular_blob_bytes", lambda *args: None)
    monkeypatch.setattr(replay, "validate_code_subject", lambda *args, **kwargs: {"manifest": []})
    monkeypatch.setattr(replay, "validate_approval", lambda *args, **kwargs: {
        "subject_id": "plan:test", "subject": {"artifacts": []}})
    monkeypatch.setattr(replay, "verify_policy_authorization", lambda *args, **kwargs: None)

    class ReachedReviewRequirement(Exception):
        pass

    def stop_after_obligations(*args):
        raise ReachedReviewRequirement

    monkeypatch.setattr(DeliveryPolicy, "review_requirement", stop_after_obligations)
    with pytest.raises(ReachedReviewRequirement if accepted else ApprovalError):
        replay.verify_v3_delivery(tmp_path, record, base="base", head="head",
                                  repository_id="owner/project", target_ref="refs/heads/main",
                                  _historical_replay=replaying)


@pytest.mark.parametrize(
    ("old_scope", "new_scope", "weakened"),
    [
        ("src/", "src/", False),
        ("src/", "src", False),
        ("src", "src/", True),
        ("src/secure/", "src/", False),
        ("src/", "src/secure/", True),
    ],
)
def test_scope_comparison_preserves_directory_boundary(old_scope, new_scope, weakened):
    raw, old, checks = setup_policy("scope", [new_scope])
    changes = compare(raw, old, checks, old_mode="scope", old_scope=(old_scope,))
    assert any(item["kind"] == "code_review" for item in changes) is weakened


def test_mutating_a_check_contract_without_recomputing_its_evidence_is_rejected():
    raw, old, checks = setup_policy()
    changed = deepcopy(checks)
    changed["checks"][0]["command"] = ["true"]
    changed["digest"] = digest_record({k: v for k, v in changed.items() if k != "digest"})
    with pytest.raises(ApprovalError, match="definition digest"):
        compare(raw, old, checks, changed)
