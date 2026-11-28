from copy import deepcopy

import pytest
import yaml

from keepsail.core.approval import ApprovalError, digest_record, evidence_is_recognized
from keepsail.core.delivery_policy import (
    SIGNED_PLAN_MIGRATION,
    parse_delivery_policy,
    parse_delivery_policy_yaml,
    reject_signed_plan_policy,
    require_activatable_policy,
)


def policy(mode="scope", *, activation=None, signed_plan=False):
    plan = ({"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
             "issuers": ["maintainer"], "evidence_forms": ["signed-plan-decision"],
             "requirements": {}} if signed_plan else
            {"id": "owner-plan-review", "version": "owner-plan-review/v1",
             "issuers": ["owner"], "evidence_forms": ["json"], "requirements": {}})
    code = {"id": "independent-review", "version": "v1", "issuers": ["reviewer"],
            "evidence_forms": ["json"], "requirements": {}}
    value = {
        "version": "review-recognition/v2", "enabled": True,
        "processes_by_kind": {"plan": plan, "code": code},
        "code_review": {"mode": mode, **({"scope": ["src/secure"]} if mode == "scope" else {})},
        "required_checks_digest": "a" * 64, "builtin_checks_version": "keepsail-baseline/v2",
    }
    if activation is not None:
        value["activation"] = activation
    value["policy_digest"] = digest_record(value)
    return value


def redigest(value):
    value["policy_digest"] = digest_record({k: v for k, v in value.items() if k != "policy_digest"})
    return value


def test_processes_are_selected_by_kind_and_scope_matches_both_sides_of_rename():
    value = policy()
    parsed = parse_delivery_policy_yaml(yaml.safe_dump(value))
    assert parsed.recognition_for("plan").process_id == "owner-plan-review"
    assert parsed.recognition_for("code").process_id == "independent-review"
    assert not parsed.review_requirement([{"path": "src/securely/a.py"}])[0]
    assert parsed.review_requirement([{"path": "docs/a.py", "old_path": "src/secure/a.py"}])[0]
    assert parsed.review_requirement([{"path": "src/secure/a.py", "old_path": "docs/a.py"}])[0]
    code = {"kind": "code", "process": {"id": "independent-review", "version": "v1"},
            "issuer": "reviewer", "form": "json"}
    assert evidence_is_recognized(code, parsed.recognition_for("code"))
    assert not evidence_is_recognized(code, parsed.recognition_for("plan"))


def test_policy_rejects_digest_mismatch_and_duplicate_yaml_key():
    value = policy()
    value["code_review"]["scope"] = ["src"]
    with pytest.raises(ApprovalError, match="digest"):
        parse_delivery_policy(value)
    with pytest.raises(ApprovalError, match="duplicate"):
        parse_delivery_policy_yaml(yaml.safe_dump(policy()) + "enabled: true\n")


@pytest.mark.parametrize("change", [
    lambda p: p["code_review"].update(scope=[]),
    lambda p: p["code_review"].update(scope=["../src"]),
    lambda p: p.update(code_review={"mode": "off", "scope": ["src"]}),
    lambda p: p.update(code_review={"mode": "full", "scope": ["src"]}),
    lambda p: p["processes_by_kind"].pop("code"),
    lambda p: p["processes_by_kind"]["plan"].update(issuers=["maintainer", "maintainer"]),
    lambda p: p["processes_by_kind"]["code"].update(evidence_forms=["signed-plan-decision"]),
    lambda p: p.update(activation={"kind": "transition"}),
    lambda p: p.update(activation={"kind": "transition", "change": "../elsewhere"}),
    lambda p: p.update(activation=None),
    lambda p: p.update(activation="initial"),
    lambda p: p.update(builtin_checks_version="keepsail-baseline/v3"),
    lambda p: p.update(required_checks_digest="bad"),
    lambda p: p.update(enabled=False),
    lambda p: p.update(unexpected=True),
])
def test_invalid_policy_never_grants_authority(change):
    value = deepcopy(policy())
    change(value)
    with pytest.raises(ApprovalError):
        parse_delivery_policy(redigest(value))


def test_off_and_full_have_explicit_opposite_results():
    disabled = parse_delivery_policy(policy("off"))
    assert not disabled.review_requirement([{"path": "x"}])[0]
    assert disabled.recognition_for("code") is None
    assert parse_delivery_policy(policy("full")).review_requirement([{"path": "x"}])[0]


@pytest.mark.parametrize("path", ["docs/notes[1].md", "src/secure/what?.py"])
def test_literal_git_names_are_not_interpreted_as_scope_patterns(path):
    manifest = [{"path": path}]
    assert parse_delivery_policy(policy("full")).review_requirement(manifest)[0]
    assert not parse_delivery_policy(policy("off")).review_requirement(manifest)[0]
    required, _ = parse_delivery_policy(policy("scope")).review_requirement(manifest)
    assert required is path.startswith("src/secure/")


def test_backslash_name_is_permitted_for_full_and_off_but_rejected_for_scope():
    manifest = [{"path": "src/secure\\name.py"}]
    assert parse_delivery_policy(policy("full")).review_requirement(manifest)[0]
    assert not parse_delivery_policy(policy("off")).review_requirement(manifest)[0]
    with pytest.raises(ApprovalError, match="unsupported literal Git path"):
        parse_delivery_policy(policy("scope")).review_requirement(manifest)


def test_off_requires_a_baseline_that_supports_no_review_completion():
    value = policy("off")
    value["builtin_checks_version"] = "keepsail-baseline/v1"
    with pytest.raises(ApprovalError, match="require built-in contract v2"):
        parse_delivery_policy(redigest(value))
    assert parse_delivery_policy(policy("off")).builtin_checks_version == "keepsail-baseline/v2"


def test_existing_scoped_v1_policy_remains_readable():
    value = policy("scope")
    value["builtin_checks_version"] = "keepsail-baseline/v1"
    parsed = parse_delivery_policy(redigest(value))
    assert parsed.review_requirement([{"path": "src/secure/a.py"}])[0]
    required, reason = parsed.review_requirement([{"path": "docs/a.md"}])
    assert required and "v1 requires code review" in reason
    with pytest.raises(ApprovalError, match="require built-in contract v2"):
        require_activatable_policy(parsed)
    require_activatable_policy(parse_delivery_policy(policy("scope")))


def test_full_review_can_preserve_the_v1_baseline():
    value = policy("full")
    value["builtin_checks_version"] = "keepsail-baseline/v1"
    assert parse_delivery_policy(redigest(value)).builtin_checks_version == "keepsail-baseline/v1"


@pytest.mark.parametrize("path", ["C:/src", "C:src", "~/src", "~", "~user/src", "~user"])
def test_new_scope_rejects_ambiguous_nonportable_path_without_breaking_historical_parse(path):
    value = policy("scope")
    value["code_review"]["scope"] = [path]
    parsed = parse_delivery_policy(redigest(value))
    with pytest.raises(ApprovalError, match="repository-relative"):
        require_activatable_policy(parsed)


def test_reserved_plan_identity_and_signed_form_are_never_recognized():
    value = policy(signed_plan=True)
    value["processes_by_kind"]["plan"]["evidence_forms"].append("json")
    recognition = parse_delivery_policy(redigest(value)).recognition_for("plan")
    evidence = {"kind": "plan", "process": {"id": "maintainer-plan-review",
                "version": "maintainer-plan-review/v1"}, "issuer": "maintainer"}
    assert not evidence_is_recognized(evidence, recognition)
    evidence["form"] = "signed-plan-decision"
    assert not evidence_is_recognized(evidence, recognition)


def test_activation_is_optional_and_only_descriptive():
    absent = policy()
    assert "activation" not in absent
    parsed = parse_delivery_policy(absent)
    assert parsed.activation is None
    assert parsed.policy_digest == digest_record(
        {k: v for k, v in absent.items() if k != "policy_digest"})
    for activation in ({"kind": "initial"}, {"kind": "transition", "change": "delivery"}):
        legacy = parse_delivery_policy(policy(activation=activation))
        assert legacy.activation == activation
        assert legacy.policy_digest != parsed.policy_digest


def test_signed_plan_policy_parses_but_is_refused_with_migration_guidance():
    parsed = parse_delivery_policy(policy(signed_plan=True))
    with pytest.raises(ApprovalError) as error:
        reject_signed_plan_policy(parsed)
    assert str(error.value) == SIGNED_PLAN_MIGRATION
    assert "previous keepsail version" in SIGNED_PLAN_MIGRATION
    with pytest.raises(ApprovalError, match="previous keepsail version"):
        require_activatable_policy(parsed)
    reject_signed_plan_policy(parse_delivery_policy(policy()))


def test_v1_policy_listing_signed_plan_is_refused_and_its_form_never_recognized():
    from keepsail.core.approval import (
        SIGNED_PLAN_MIGRATION,
        Recognition,
        _recognition_from_mapping,
        recognition_policy_digest,
    )

    raw = {"version": "review-recognition/v1", "enabled": True, "process": {
        "id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
        "kinds": ["plan", "code"], "issuers": ["maintainer"],
        "evidence_forms": ["json", "signed-plan-decision"]}}
    raw["process"]["policy_digest"] = recognition_policy_digest(raw)
    with pytest.raises(ApprovalError) as error:
        _recognition_from_mapping(raw)
    assert str(error.value) == SIGNED_PLAN_MIGRATION
    historical = _recognition_from_mapping(raw, historical=True)
    evidence = {"kind": "plan", "issuer": "maintainer", "form": "signed-plan-decision",
                "process": {"id": "maintainer-plan-review",
                            "version": "maintainer-plan-review/v1"}}
    assert not evidence_is_recognized(evidence, historical)
    assert evidence_is_recognized({**evidence, "form": "json"}, historical)
    v1 = Recognition("review-recognition/v1", "p", "v1", frozenset({"plan"}),
                     frozenset({"i"}), frozenset({"signed-plan-decision"}), {}, "d" * 64)
    assert not evidence_is_recognized({"kind": "plan", "issuer": "i", "form":
                                       "signed-plan-decision",
                                       "process": {"id": "p", "version": "v1"}}, v1)
