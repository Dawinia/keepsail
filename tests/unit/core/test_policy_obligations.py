"""Effective-obligation objects and their complete generic difference (plan C2)."""

import random
from copy import deepcopy

import pytest
import yaml

from keepsail.core.approval import ApprovalError, digest_record, recognition_policy_digest
from keepsail.core.policy_obligations import (
    checks_object,
    inactive_obligations,
    obligation_differences,
    semantic_labels,
    structural_diff,
    v1_obligations,
    v2_obligations,
)
from keepsail.engineering.verification_config import (
    parse_verification_config,
    required_check_contract,
)

PROCESS = {"id": "existing", "version": "v1", "issuers": ["reviewer"],
           "evidence_forms": ["json"], "requirements": {}}


def contract(config=None):
    value = config or {"checks": [{"id": "test", "command": ["python", "-m", "pytest"]}]}
    return required_check_contract(parse_verification_config(yaml.safe_dump(value), strict=True))


def v1_raw():
    raw = {"version": "review-recognition/v1", "enabled": True, "process": {
        **deepcopy(PROCESS), "kinds": ["plan", "code"]}}
    raw["process"]["policy_digest"] = recognition_policy_digest(raw)
    return raw


def v2_raw(mode="full", *, scope=None, builtin="keepsail-baseline/v1", activation=None):
    code_review = {"mode": mode, **({"scope": scope or ["src"]} if mode == "scope" else {})}
    raw = {"version": "review-recognition/v2", "enabled": True,
           "processes_by_kind": {"plan": deepcopy(PROCESS), "code": deepcopy(PROCESS)},
           "code_review": code_review, "required_checks_digest": contract()["digest"],
           "builtin_checks_version": builtin}
    if activation is not None:
        raw["activation"] = activation
    raw["policy_digest"] = digest_record(raw)
    return raw


def paths(rows, direction=None):
    return {row["path"] for row in rows if direction is None or row["direction"] == direction}


def test_v1_and_v2_share_one_normalized_shape_and_full_review_is_not_a_difference():
    old, new = v1_obligations(v1_raw()), v2_obligations(v2_raw("full"))
    assert set(old) == set(new)
    rows = obligation_differences(old, new, contract(), contract())
    assert rows == [{"object": "policy", "path": "/version", "direction": "changed",
                     "before": "review-recognition/v1", "after": "review-recognition/v2"}]
    assert not any(label.startswith("code review") for label in semantic_labels(old, new, rows))


def test_v1_implied_full_review_is_listed_when_relaxed_to_off():
    old = v1_obligations(v1_raw())
    new = v2_obligations(v2_raw("off", builtin="keepsail-baseline/v2"))
    rows = obligation_differences(old, new, contract(), contract())
    assert {"object": "policy", "path": "/code_review/mode", "direction": "changed",
            "before": "full", "after": "off"} in rows
    assert {"object": "policy", "path": "/builtin_checks_version", "direction": "changed",
            "before": "keepsail-baseline/v1", "after": "keepsail-baseline/v2"} in rows
    labels = semantic_labels(old, new, rows)
    assert "code review relaxed (full -> off)" in labels
    assert "built-in check contract changed" in labels


@pytest.mark.parametrize("state", ["disabled", "removed"])
def test_deactivation_lists_every_baseline_obligation_as_removed(state):
    old = v1_obligations(v1_raw())
    rows = obligation_differences(old, inactive_obligations(state), contract(), contract())
    assert {"object": "policy", "path": "/state", "direction": "changed",
            "before": "enabled", "after": state} in rows
    removed = paths(rows, "removed")
    assert {"/code_review/mode", "/builtin_checks_version", "/processes_by_kind/plan/id",
            "/processes_by_kind/code/id", "/processes_by_kind/code/issuers"} <= removed
    full = next(row for row in rows if row["path"] == "/code_review/mode")
    assert full["before"] == "full"
    assert semantic_labels(old, inactive_obligations(state), rows)[0].startswith("policy ")


def test_strengthening_and_new_process_kinds_are_recorded():
    off = v2_obligations(v2_raw("off", builtin="keepsail-baseline/v2"))
    raw = v2_raw("off", builtin="keepsail-baseline/v2")
    del raw["processes_by_kind"]["code"]
    plan_only = v2_obligations(raw)
    rows = obligation_differences(plan_only, off, contract(), contract())
    assert {"/processes_by_kind/code/id", "/processes_by_kind/code/version"} <= paths(rows, "added")
    assert "code review process added" in semantic_labels(plan_only, off, rows)
    full = v2_obligations(v2_raw("full", builtin="keepsail-baseline/v2"))
    rows = obligation_differences(off, full, contract(), contract())
    assert "code review strengthened (off -> full)" in semantic_labels(off, full, rows)
    narrow = v2_obligations(v2_raw("scope", scope=["src"], builtin="keepsail-baseline/v2"))
    wide = v2_obligations(v2_raw("scope", scope=["src", "docs"], builtin="keepsail-baseline/v2"))
    rows = obligation_differences(narrow, wide, contract(), contract())
    assert rows == [{"object": "policy", "path": "/code_review/scope", "direction": "changed",
                     "before": ["src"], "after": ["src", "docs"]}]
    assert "code review strengthened (scope -> scope)" in semantic_labels(narrow, wide, rows)


def test_activation_only_is_recorded_as_an_informational_change():
    old = v2_obligations(v2_raw(activation={"kind": "initial"}))
    new = v2_obligations(v2_raw())
    rows = obligation_differences(old, new, contract(), contract())
    assert paths(rows) == {"/activation"}
    assert semantic_labels(old, new, rows) == ["activation description changed (informational)"]


@pytest.mark.parametrize(("field", "value"), [
    ("command", ["python", "-m", "pytest", "-q"]),
    ("shell", "sh"),
    ("workdir", "sub"),
    ("env", {"A": "1"}),
    ("timeout_seconds", 99),
    ("capture", "stdout"),
])
def test_each_check_definition_field_alone_is_a_path_under_its_check(field, value):
    base = {"checks": [{"id": "test", "command": ["python", "-m", "pytest"]}]}
    changed = deepcopy(base)
    if field == "shell":
        changed["checks"][0]["command"] = "python -m pytest"
    changed["checks"][0][field] = value
    before, after = contract(base), contract(changed)
    rows = obligation_differences({}, {}, before, after)
    assert rows and all(row["object"] == "checks" for row in rows)
    assert any(path == f"/checks/user/test/{field}"
               or path.startswith(f"/checks/user/test/{field}/") for path in paths(rows))
    assert semantic_labels({}, {}, rows) == ["required check definition changed: user/test"]


def test_must_pass_false_removes_the_check_and_new_checks_are_added():
    base = {"checks": [{"id": "test", "command": ["python", "-c", "pass"]}]}
    optional = {"checks": [{"id": "test", "command": ["python", "-c", "pass"],
                            "must_pass": False}]}
    rows = obligation_differences({}, {}, contract(base), contract(optional))
    assert paths(rows, "removed") >= {"/checks/user/test/command", "/checks/user/test/must_pass"}
    assert "required check removed: user/test" in semantic_labels({}, {}, rows)
    more = {"checks": [*base["checks"], {"id": "lint", "command": ["ruff", "check"]}]}
    rows = obligation_differences({}, {}, contract(base), contract(more))
    assert "/checks/user/lint/command" in paths(rows, "added")
    assert "required check added: user/lint" in semantic_labels({}, {}, rows)


@pytest.mark.parametrize("layer", ["baseline", "framework_adapter", "user_checks"])
def test_each_layer_switch_is_recorded_even_when_the_selected_checks_do_not_change(layer):
    on = {"layers": {name: {"enabled": True} for name in
                     ("baseline", "framework_adapter", "user_checks")}, "checks": []}
    off = deepcopy(on)
    off["layers"][layer]["enabled"] = False
    rows = obligation_differences({}, {}, contract(on), contract(off))
    assert rows == [{"object": "checks", "path": f"/layers/{layer}", "direction": "changed",
                     "before": True, "after": False}]
    assert semantic_labels({}, {}, rows) == [f"required check layer {layer} disabled"]
    rows = obligation_differences({}, {}, contract(off), contract(on))
    assert semantic_labels({}, {}, rows) == [f"required check layer {layer} enabled"]


def test_mutating_a_check_contract_without_recomputing_its_digest_is_rejected():
    changed = deepcopy(contract())
    changed["checks"][0]["command"] = ["true"]
    changed["digest"] = digest_record({k: v for k, v in changed.items() if k != "digest"})
    with pytest.raises(ApprovalError, match="definition digest"):
        checks_object(changed)


def _random_value(rng, depth):
    choice = rng.randrange(6 if depth < 3 else 4)
    if choice == 0:
        return rng.choice([None, True, False])
    if choice == 1:
        return rng.randrange(3)  # 0/1 deliberately collide with false/true in Python
    if choice == 2:
        return rng.choice(["a", "b", ""])
    if choice == 3:
        return [rng.choice([0, 1, True, False]) for _ in range(rng.randrange(3))]
    return {rng.choice("xyz/~"): _random_value(rng, depth + 1)
            for _ in range(rng.randrange(4))}


def _mutate(rng, value, depth=0):
    value = deepcopy(value)
    if not isinstance(value, dict) or not value or rng.random() < 0.3:
        return _random_value(rng, depth) if rng.random() < 0.7 else value
    key = rng.choice(sorted(value))
    action = rng.randrange(3)
    if action == 0:
        del value[key]
    elif action == 1:
        value[key + "n"] = _random_value(rng, depth + 1)
    else:
        value[key] = _mutate(rng, value[key], depth + 1)
    return value


def test_property_objects_are_equal_exactly_when_the_difference_is_empty():
    rng = random.Random(20261128)
    for _ in range(3000):
        before = {"root": _random_value(rng, 0)}
        after = _mutate(rng, before) if rng.random() < 0.8 else deepcopy(before)
        rows = structural_diff(before, after, obj="policy")
        assert (digest_record(before) == digest_record(after)) == (not rows), (before, after)


def test_property_check_contracts_are_equal_exactly_when_the_difference_is_empty():
    rng = random.Random(159)
    fields = {"command": [["a"], ["b"], "c"], "timeout_seconds": [5, 9, 30],
              "capture": ["stdout", "none", "both"], "env": [{}, {"K": "v"}],
              "workdir": ["w", "x"]}
    for _ in range(300):
        def config():
            checks = []
            for name in rng.sample(["a", "b", "c"], rng.randrange(1, 4)):
                check = {"id": name, "command": ["python", "-c", name]}
                for field, options in fields.items():
                    if rng.random() < 0.3:
                        check[field] = rng.choice(options)
                if isinstance(check["command"], str):
                    check["shell"] = "sh"
                checks.append(check)
            return {"layers": {layer: {"enabled": rng.random() < 0.7} for layer in
                               ("baseline", "framework_adapter", "user_checks")},
                    "checks": checks}
        before = contract(config())
        after = contract(config()) if rng.random() < 0.8 else deepcopy(before)
        rows = obligation_differences({}, {}, before, after)
        assert (before["digest"] == after["digest"]) == (not rows)


@pytest.mark.parametrize(("old_scope", "new_scope", "relaxed"), [
    ("src/", "src/", False),
    ("src/", "src", False),
    ("src", "src/", True),
    ("src/secure/", "src/", False),
    ("src/", "src/secure/", True),
])
def test_scope_labels_preserve_the_directory_boundary(old_scope, new_scope, relaxed):
    old = v2_obligations(v2_raw("scope", scope=[old_scope], builtin="keepsail-baseline/v2"))
    new = v2_obligations(v2_raw("scope", scope=[new_scope], builtin="keepsail-baseline/v2"))
    rows = obligation_differences(old, new, contract(), contract())
    labels = semantic_labels(old, new, rows)
    assert any("relaxed" in label for label in labels) is relaxed
    assert (rows == []) is (old_scope == new_scope)
