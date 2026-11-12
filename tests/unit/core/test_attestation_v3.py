import json
from copy import deepcopy

import pytest

from keepsail.core.approval import ApprovalError, canonical_json, digest_record
from keepsail.core.attestation_v3 import make_v3, parse_v3_line, validate_v3


def v3():
    snapshot = {"schema_version": "attestation/v2", "change_id": "delivery"}
    snapshot["digest"] = digest_record(snapshot)
    return make_v3(change_id="delivery", trusted_base="a" * 40, policy_digest="b" * 64,
                   recognition_basis={"plan": {"mode": "current", "policy_digest": "b" * 64},
                                      "code": {"mode": "current", "policy_digest": "b" * 64}},
                   authorization=None, snapshot=snapshot)


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
