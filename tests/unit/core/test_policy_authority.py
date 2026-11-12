"""Trust and signature checks use real Ed25519 keys, not mocked verdicts."""

import base64
from copy import deepcopy
from hashlib import sha256

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.core.approval import ApprovalError, Recognition, canonical_json
from keepsail.core.policy_authority import (
    parse_authority,
    parse_authority_yaml,
    verify_policy_authorization,
    verify_signed_plan_decision,
    verify_v2_review_evidence,
)


def authority(key, purposes):
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return {
        "version": "policy-authority/v1",
        "repository_id": "owner/project",
        "target_ref": "refs/heads/main",
        "enabled": True,
        "keys": [{
            "key_id": sha256(public).hexdigest(),
            "algorithm": "ed25519",
            "public_key": base64.b64encode(public).decode("ascii"),
            "purposes": purposes,
        }],
    }


def sign(record, key):
    body = {k: v for k, v in record.items() if k != "signature"}
    record["signature"] = base64.b64encode(
        key.sign(canonical_json(body).encode("utf-8"))
    ).decode("ascii")
    return record


def authorization(key, old, *, kind="transition"):
    return sign({
        "version": "policy-authorization/v1",
        "repository_id": "owner/project",
        "target_ref": "refs/heads/main",
        "base_sha": "a" * 40,
        "predecessor_policy_digest": "b" * 64,
        "target_policy_digest": ("b" if kind == "rotate_key" else "c") * 64,
        "change_id": "delivery",
        "plan_subject_id": "plan:123",
        "kind": kind,
        "permitted_paths": ["docs/plans", ".harness/policy-authority.yaml"
                            if kind == "rotate_key" else ".harness/review-recognition.yaml"],
        "decision": "approve",
        "key_id": old.key_id,
    }, key)


def verify(record, old, **kwargs):
    inputs = {
        "repository_id": "owner/project",
        "target_ref": "refs/heads/main",
        "base_sha": "a" * 40,
        "predecessor_policy_digest": "b" * 64,
        "target_policy_digest": "c" * 64,
        "change_id": "delivery",
        "plan_subject_id": "plan:123",
        "actual_paths": ["docs/plans/delivery.md", ".harness/review-recognition.yaml"],
        "target_authority": old,
    }
    if record["kind"] == "rotate_key":
        inputs["target_policy_digest"] = "b" * 64
        inputs["actual_paths"] = ["docs/plans/delivery.md", ".harness/policy-authority.yaml"]
        inputs["frozen_plan_paths"] = ["docs/plans/delivery.md"]
    if record["kind"] == "recovery":
        inputs["frozen_plan_paths"] = ["docs/plans/delivery.md"]
    inputs.update(kwargs)
    return verify_policy_authorization(record, old, **inputs)


def test_authority_requires_strict_shape_unique_yaml_and_matching_key_id():
    key = Ed25519PrivateKey.generate()
    raw = authority(key, ["policy-transition"])
    assert parse_authority_yaml(yaml.safe_dump(raw)).key_id == raw["keys"][0]["key_id"]
    with pytest.raises(ApprovalError, match="duplicate"):
        parse_authority_yaml(yaml.safe_dump(raw) + "enabled: false\n")
    for change in (lambda x: x.update(extra=True),
                   lambda x: x["keys"][0].update(key_id="a" * 64),
                   lambda x: x["keys"][0].update(purposes=["policy-transition"] * 2),
                   lambda x: x["keys"][0].update(public_key="!!!!"),
                   lambda x: x.update(target_ref="main")):
        invalid = deepcopy(raw)
        change(invalid)
        with pytest.raises(ApprovalError):
            parse_authority(invalid)


def test_authorization_uses_trusted_identity_subject_and_scope():
    key = Ed25519PrivateKey.generate()
    old = parse_authority(authority(key, ["policy-transition"]))
    record = authorization(key, old)
    assert verify(record, old) == record
    for inputs in ({"repository_id": "owner/other"}, {"target_ref": "refs/heads/other"},
                   {"base_sha": "d" * 40}, {"change_id": "other"},
                   {"plan_subject_id": "plan:other"},
                   {"actual_paths": ["docs/plans-evil/file"]}):
        with pytest.raises(ApprovalError):
            verify(record, old, **inputs)
    tampered = deepcopy(record)
    tampered["permitted_paths"].append("src")
    with pytest.raises(ApprovalError, match="signature"):
        verify(tampered, old)
    tampered = deepcopy(record)
    tampered["unexpected"] = True
    with pytest.raises(ApprovalError, match="unknown"):
        verify(sign(tampered, key), old)


@pytest.mark.parametrize("same_key", [False, True])
@pytest.mark.parametrize("new_purpose", ["plan-decision", "policy-recovery"])
def test_rotation_cannot_grant_new_purpose_even_with_valid_old_signature(same_key, new_purpose):
    old_key = Ed25519PrivateKey.generate()
    new_key = old_key if same_key else Ed25519PrivateKey.generate()
    old = parse_authority(authority(old_key, ["policy-transition"]))
    new = parse_authority(authority(new_key, ["policy-transition", new_purpose]))
    record = authorization(old_key, old, kind="rotate_key")
    record.update(predecessor_authority_digest=old.digest, target_authority_digest=new.digest)
    sign(record, old_key)
    with pytest.raises(ApprovalError, match="cannot add purposes"):
        verify(record, old, target_authority=new)


def test_rotation_can_reduce_purposes_but_must_satisfy_the_active_policy():
    old_key = Ed25519PrivateKey.generate()
    new_key = Ed25519PrivateKey.generate()
    old = parse_authority(authority(old_key, ["policy-transition", "plan-decision"]))
    new = parse_authority(authority(new_key, ["policy-transition"]))
    record = authorization(old_key, old, kind="rotate_key")
    record.update(predecessor_authority_digest=old.digest, target_authority_digest=new.digest)
    sign(record, old_key)
    assert verify(record, old, target_authority=new) == record
    with pytest.raises(ApprovalError, match="lacks purposes"):
        verify(record, old, target_authority=new, required_purposes=frozenset({"plan-decision"}))
    with pytest.raises(ApprovalError, match="signature"):
        verify(sign(deepcopy(record), new_key), old, target_authority=new)


def test_recovery_requires_its_own_purpose_explicit_reason_and_processes():
    key = Ed25519PrivateKey.generate()
    trusted = parse_authority(authority(key, ["policy-transition", "policy-recovery"]))
    record = authorization(key, trusted, kind="recovery")
    record.update(reason="The trusted reviewer is unavailable", review_processes=[{
        "kind": "plan", "id": "recovery-review", "version": "v1", "issuer": "owner",
        "evidence_form": "json",
    }])
    sign(record, key)
    assert verify(record, trusted) == record
    no_recovery = parse_authority(authority(key, ["policy-transition"]))
    with pytest.raises(ApprovalError, match="policy-recovery"):
        verify(record, no_recovery)
    invalid = deepcopy(record)
    invalid["review_processes"] = []
    with pytest.raises(ApprovalError, match="review processes"):
        verify(sign(invalid, key), trusted)
    invalid = deepcopy(record)
    invalid["reason"] = ""
    with pytest.raises(ApprovalError, match="reason"):
        verify(sign(invalid, key), trusted)
    with pytest.raises(ApprovalError, match="cannot rotate"):
        verify(record, trusted, target_authority=None)
    broad = deepcopy(record)
    broad["permitted_paths"].append("src")
    with pytest.raises(ApprovalError, match="exact allowed scope"):
        verify(sign(broad, key), trusted, actual_paths=["src/business.py"])


def test_signed_plan_binds_exact_envelope_and_key_purpose():
    key = Ed25519PrivateKey.generate()
    trusted = parse_authority(authority(key, ["policy-transition", "plan-decision"]))
    record = sign({
        "version": "signed-plan-decision/v1",
        "repository_id": "owner/project", "target_ref": "refs/heads/main",
        "policy_digest": "b" * 64, "change_id": "delivery", "subject_id": "plan:123",
        "decision": "approve", "evidence_id": "e1", "supersedes": None,
        "key_id": trusted.key_id,
    }, key)
    inputs = dict(repository_id="owner/project", target_ref="refs/heads/main",
                  policy_digest="b" * 64, change_id="delivery", subject_id="plan:123",
                  evidence_id="e1", decision="approve", supersedes=None)
    assert verify_signed_plan_decision(record, trusted, **inputs) == record
    for field, value in (("decision", "reject"), ("supersedes", "older"),
                         ("subject_id", "plan:other"), ("evidence_id", "e2")):
        with pytest.raises(ApprovalError, match="envelope"):
            verify_signed_plan_decision(record, trusted, **{**inputs, field: value})
    no_plan_purpose = parse_authority(authority(key, ["policy-transition"]))
    with pytest.raises(ApprovalError, match="plan-decision"):
        verify_signed_plan_decision(record, no_plan_purpose, **inputs)


def test_v2_maintainer_evidence_checks_both_signature_and_outer_envelope():
    key = Ed25519PrivateKey.generate()
    trusted = parse_authority(authority(key, ["policy-transition", "plan-decision"]))
    recognition = Recognition("review-recognition/v2", "maintainer-plan-review",
                              "maintainer-plan-review/v1", frozenset({"plan"}),
                              frozenset({"maintainer"}),
                              frozenset({"signed-plan-decision", "json"}), {}, "b" * 64)
    original = sign({"version": "signed-plan-decision/v1", "repository_id": "owner/project",
                     "target_ref": "refs/heads/main", "policy_digest": "b" * 64,
                     "change_id": "delivery", "subject_id": "plan:123", "decision": "approve",
                     "evidence_id": "e1", "supersedes": None, "key_id": trusted.key_id}, key)
    evidence = {"version": "review-evidence/v1", "evidence_id": "e1", "kind": "plan",
                "subject_id": "plan:123", "decision": "approve", "issuer": "maintainer",
                "process": {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1"},
                "form": "signed-plan-decision", "provenance": {"policy_digest": "b" * 64},
                "original_evidence": original}
    inputs = dict(repository_id="owner/project", target_ref="refs/heads/main", change_id="delivery")
    assert verify_v2_review_evidence(evidence, recognition, trusted, **inputs) == evidence
    for key_name, wrong in (("decision", "reject"), ("subject_id", "plan:other"),
                            ("supersedes", "earlier"), ("form", "json")):
        changed = deepcopy(evidence)
        changed[key_name] = wrong
        with pytest.raises(ApprovalError):
            verify_v2_review_evidence(changed, recognition, trusted, **inputs)
