import base64
import json
import subprocess
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.core.approval import (
    ApprovalError,
    canonical_json,
    digest_record,
    evidence_digest,
    recognition_policy_digest,
)
from keepsail.core.attestation_format import _validate_evidence_chain
from keepsail.core.attestation_v3 import make_v3, parse_v3_line, validate_v3
from keepsail.core.policy_authority import parse_authority, require_recovery_basis


def v3():
    snapshot = {"schema_version": "attestation/v2", "change_id": "delivery"}
    snapshot["digest"] = digest_record(snapshot)
    return make_v3(change_id="delivery", trusted_base="a" * 40, policy_digest="b" * 64,
                   recognition_basis={"plan": {"mode": "current", "policy_digest": "b" * 64},
                                      "code": {"mode": "current", "policy_digest": "b" * 64}},
                   authorization=None, snapshot=snapshot)


@pytest.mark.parametrize("case", ["valid", "bad-signature", "more-purposes", "policy", "checks"])
def test_v1_rotation_replay_checks_signed_authority_and_unchanged_obligations(
    tmp_path, monkeypatch, case,
):
    """Exercise real Git and signatures; lifecycle replay is tested separately."""
    from keepsail.core import attestation_v3_verify as replay

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    def authority(key, purposes):
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return {"version": "policy-authority/v1", "repository_id": "owner/project",
                "target_ref": "refs/heads/main", "enabled": True, "keys": [{
                    "key_id": sha256(public).hexdigest(), "algorithm": "ed25519",
                    "public_key": base64.b64encode(public).decode("ascii"), "purposes": purposes}]}

    old_key, new_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    old_raw = authority(old_key, ["policy-transition"])
    purposes = ["policy-transition", "plan-decision"] if case == "more-purposes" else [
        "policy-transition"]
    new_raw = authority(new_key, purposes)
    old, new = parse_authority(old_raw), parse_authority(new_raw)
    recognition = {"version": "review-recognition/v1", "enabled": True, "process": {
        "id": "old", "version": "v1", "kinds": ["plan", "code"],
        "issuers": ["owner"], "evidence_forms": ["json"]}}
    recognition["process"]["policy_digest"] = recognition_policy_digest(recognition)
    harness = tmp_path / ".harness"
    harness.mkdir()
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(recognition), encoding="utf-8")
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(old_raw), encoding="utf-8")
    checks = "checks:\n- id: fixture\n  command: [python, -c, pass]\n  must_pass: true\n"
    (harness / "verification.yaml").write_text(checks, encoding="utf-8")
    (tmp_path / "plan.md").write_text("# Rotation\n", encoding="utf-8")
    git("init", "-q", "-b", "main")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "fixture")
    git("add", ".")
    git("commit", "-qm", "trusted base")
    base = git("rev-parse", "HEAD")
    git("switch", "-qc", "candidate")
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(new_raw), encoding="utf-8")
    if case == "policy":
        changed = deepcopy(recognition)
        changed["process"]["id"] = "other"
        changed["process"]["policy_digest"] = recognition_policy_digest(changed)
        (harness / "review-recognition.yaml").write_text(yaml.safe_dump(changed), encoding="utf-8")
    if case == "checks":
        (harness / "verification.yaml").write_text(
            checks.replace("pass", "exit()"), encoding="utf-8")
    evidence = harness / "attestations/v3/delivery.jsonl"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "candidate rotation")
    head = git("rev-parse", "HEAD")
    policy_digest = recognition["process"]["policy_digest"]
    authorization = {"version": "policy-authorization/v1", "repository_id": "owner/project",
        "target_ref": "refs/heads/main", "base_sha": base,
        "predecessor_policy_digest": policy_digest, "target_policy_digest": policy_digest,
        "predecessor_authority_digest": old.digest, "target_authority_digest": new.digest,
        "change_id": "delivery", "plan_subject_id": "plan:test", "kind": "rotate_key",
        "permitted_paths": ["plan.md", ".harness/policy-authority.yaml"],
        "decision": "approve", "key_id": old.key_id}
    signer = new_key if case == "bad-signature" else old_key
    authorization["signature"] = base64.b64encode(
        signer.sign(canonical_json(authorization).encode("utf-8"))).decode("ascii")
    record = {"trusted_base": base, "policy_digest": policy_digest, "change_id": "delivery",
              "snapshot": {}, "authorization": authorization,
              "recognition_basis": {"plan": {"mode": "current"}, "code": {"mode": "current"}}}
    approval = {"subject_id": "plan:test", "subject": {"artifacts": [
        {"role": "plan", "path": "plan.md"}]}}
    code = {"subject_id": "code:test", "manifest": [{"path": ".harness/policy-authority.yaml"}]}
    state = SimpleNamespace(current_verification={}, coverage_manifest=code["manifest"])
    monkeypatch.setattr(replay, "validate_v3", lambda value: value)
    monkeypatch.setattr(replay, "validate_approval", lambda *args, **kwargs: approval)
    monkeypatch.setattr(replay, "validate_code_subject", lambda *args, **kwargs: code)
    monkeypatch.setattr(replay, "parse_v3_line", lambda raw: record)
    monkeypatch.setattr(replay, "expand_attestation", lambda *args, **kwargs: [])
    monkeypatch.setattr(replay, "wrap_derived_completion", lambda lines: lines)
    monkeypatch.setattr(replay, "check_recognized_attestation", lambda *args: [])
    monkeypatch.setattr(replay, "derive_state", lambda path: {"delivery": state})
    monkeypatch.setattr(replay, "_new_contract_blockers", lambda *args, **kwargs: [])
    monkeypatch.setattr(replay, "_knowledge_attestation", lambda *args, **kwargs: None)
    monkeypatch.setattr(replay, "events_from_stateful_attestation", lambda *args, **kwargs: [])
    monkeypatch.setattr(replay, "gate_bypass_disclosure", lambda events: {"undisclosed": False})
    monkeypatch.setattr(replay, "derive_independence", lambda events: {
        kind: {"skipped": False, "override": False} for kind in ("plan_review", "code_review")})
    monkeypatch.setattr(replay, "verify_check_evidence", lambda *args, **kwargs: {})

    if case == "valid":
        result = replay.verify_v3_transition(tmp_path, record, base=base, head=head,
            repository_id="owner/project", target_ref="refs/heads/main")
        assert result["target_policy_digest"] == policy_digest
        assert result["code_review_required"] is True
    else:
        expected = {"bad-signature": "signature verification failed",
                    "more-purposes": "cannot add purposes",
                    "policy": "cannot change the trusted v1 policy",
                    "checks": "cannot change required checks"}
        with pytest.raises(ApprovalError, match=expected[case]):
            replay.verify_v3_transition(tmp_path, record, base=base, head=head,
                repository_id="owner/project", target_ref="refs/heads/main")


def test_envelope_round_trips_canonical_single_line():
    record = v3()
    data = (canonical_json(record) + "\n").encode()
    assert parse_v3_line(data) == record
    for partial in (data[:-1], data[:100], data + b"\n"):
        with pytest.raises(ApprovalError):
            parse_v3_line(partial)
    with pytest.raises(ApprovalError, match="duplicate"):
        parse_v3_line(b'{"schema_version":"attestation/v3","schema_version":"x"}\n')


def test_bases_and_snapshot_are_bound_to_the_envelope():
    record = v3()
    for mutate in (lambda x: x["snapshot"].update(change_id="other"),
                   lambda x: x["snapshot"].update(digest="0" * 64),
                   lambda x: x["recognition_basis"]["plan"].update(policy_digest="c" * 64),
                   lambda x: x["recognition_basis"]["code"].update(mode="continued_plan")):
        changed = deepcopy(record)
        mutate(changed)
        changed["digest"] = digest_record({k: v for k, v in changed.items() if k != "digest"})
        with pytest.raises(ApprovalError):
            validate_v3(changed)


def test_recovery_basis_requires_the_exact_signed_authorization():
    record = v3()
    authorization = {"version": "policy-authorization/v1", "signature": "fixture"}
    auth_digest = digest_record(authorization)
    recovery_digest = digest_record({"version": "recovery-recognition/v1",
                                     "base_policy_digest": record["policy_digest"],
                                     "authorization_digest": auth_digest})
    record["authorization"] = authorization
    record["recognition_basis"]["plan"] = {"mode": "recovery", "policy_digest": recovery_digest,
                                             "authorization_digest": auth_digest}
    record["digest"] = digest_record({k: v for k, v in record.items() if k != "digest"})
    assert validate_v3(record) == record
    record["authorization"]["signature"] = "different"
    record["digest"] = digest_record({k: v for k, v in record.items() if k != "digest"})
    with pytest.raises(ApprovalError, match="recovery basis"):
        validate_v3(record)
    with pytest.raises(ApprovalError, match="not canonical"):
        parse_v3_line((json.dumps(v3()) + "\n").encode())


def test_recovery_cannot_use_current_or_another_authorization():
    require_recovery_basis({"mode": "recovery", "authorization_digest": "signed"},
                           kind="plan", authorization_digest="signed")
    for basis in ({"mode": "current"}, {"mode": "recovery", "authorization_digest": "other"}):
        with pytest.raises(ApprovalError, match="selected recovery authorization"):
            require_recovery_basis(basis, kind="plan", authorization_digest="signed")


def test_v3_replays_retained_evidence_supersession_and_id_consistency():
    first = {"version": "review-evidence/v1", "evidence_id": "first", "kind": "plan",
             "subject_id": "plan:one", "decision": "reject", "issuer": "owner",
             "process": {"id": "review", "version": "v1"}, "form": "json",
             "original_evidence": {"decision": "reject"}, "provenance": {}}
    second = {**first, "evidence_id": "second", "decision": "approve", "supersedes": "first"}

    def row(evidence):
        return {"type": "review_evidence_imported", "payload": {
            "evidence": evidence, "evidence_digest": evidence_digest(evidence),
            "subject_id": evidence["subject_id"]}}

    _validate_evidence_chain([row(first), row(second)], "delivery")
    with pytest.raises(ApprovalError, match="supersedes"):
        _validate_evidence_chain([row(second)], "delivery")
    with pytest.raises(ApprovalError, match="reused"):
        _validate_evidence_chain([row(first), row({**first, "decision": "approve"})], "delivery")
