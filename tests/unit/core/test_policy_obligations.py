from copy import deepcopy

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


def test_mutating_a_check_contract_without_recomputing_its_evidence_is_rejected():
    raw, old, checks = setup_policy()
    changed = deepcopy(checks)
    changed["checks"][0]["command"] = ["true"]
    changed["digest"] = digest_record({k: v for k, v in changed.items() if k != "digest"})
    with pytest.raises(ApprovalError, match="definition digest"):
        compare(raw, old, checks, changed)
