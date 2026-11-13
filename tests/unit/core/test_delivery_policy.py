from copy import deepcopy

import pytest
import yaml

from keepsail.core.approval import ApprovalError, digest_record, evidence_is_recognized
from keepsail.core.delivery_policy import parse_delivery_policy, parse_delivery_policy_yaml


def policy(mode="scope"):
    plan = {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
            "issuers": ["maintainer"], "evidence_forms": ["signed-plan-decision"],
            "requirements": {}}
    code = {"id": "independent-review", "version": "v1", "issuers": ["reviewer"],
            "evidence_forms": ["json"], "requirements": {}}
    value = {
        "version": "review-recognition/v2", "enabled": True,
        "processes_by_kind": {"plan": plan, "code": code},
        "code_review": {"mode": mode, **({"scope": ["src/secure"]} if mode == "scope" else {})},
        "required_checks_digest": "a" * 64, "builtin_checks_version": "keepsail-baseline/v2",
        "activation": {"kind": "transition", "change": "delivery"},
    }
    value["policy_digest"] = digest_record(value)
    return value


def redigest(value):
    value["policy_digest"] = digest_record({k: v for k, v in value.items() if k != "policy_digest"})
    return value


def test_processes_are_selected_by_kind_and_scope_matches_both_sides_of_rename():
    value = policy()
    parsed = parse_delivery_policy_yaml(yaml.safe_dump(value))
    assert parsed.recognition_for("plan").process_id == "maintainer-plan-review"
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
    lambda p: p["processes_by_kind"].pop("code"),
    lambda p: p["processes_by_kind"]["plan"].update(issuers=["maintainer", "maintainer"]),
    lambda p: p["processes_by_kind"]["code"].update(evidence_forms=["signed-plan-decision"]),
    lambda p: p.update(activation={"kind": "transition"}),
    lambda p: p.update(activation={"kind": "transition", "change": "../elsewhere"}),
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


def test_reserved_plan_identity_cannot_be_impersonated_by_json_or_unverified_signature():
    value = policy()
    value["processes_by_kind"]["plan"]["evidence_forms"].append("json")
    recognition = parse_delivery_policy(redigest(value)).recognition_for("plan")
    evidence = {"kind": "plan", "process": {"id": "maintainer-plan-review",
                "version": "maintainer-plan-review/v1"}, "issuer": "maintainer"}
    assert not evidence_is_recognized(evidence, recognition)
    evidence["form"] = "signed-plan-decision"
    assert not evidence_is_recognized(evidence, recognition)
    assert evidence_is_recognized(evidence, recognition, signed_plan_verified=True)
