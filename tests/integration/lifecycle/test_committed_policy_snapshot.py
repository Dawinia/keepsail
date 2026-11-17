"""Policy inputs must all come from the selected Git object."""

import base64
import subprocess
from hashlib import sha256

import pytest
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.core.approval import ApprovalError, digest_record
from keepsail.engineering.delivery_policy import read_policy_snapshot
from keepsail.engineering.verification_config import (
    parse_verification_config,
    required_check_contract,
)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_snapshot_binds_policy_config_and_host_identity_to_committed_blobs(tmp_path):
    root = tmp_path
    harness = root / ".harness"
    harness.mkdir()
    config = "checks:\n  - id: test\n    command: [python, -m, pytest]\n"
    (harness / "verification.yaml").write_text(config, encoding="utf-8")
    key = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    authority = {"version": "policy-authority/v1", "repository_id": "owner/project",
                 "target_ref": "refs/heads/main", "enabled": True, "keys": [{
                     "key_id": sha256(key).hexdigest(), "algorithm": "ed25519",
                     "public_key": base64.b64encode(key).decode("ascii"),
                     "purposes": ["policy-transition", "plan-decision"],
                 }]}
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(authority), encoding="utf-8")
    policy = {"version": "review-recognition/v2", "enabled": True,
              "processes_by_kind": {"plan": {"id": "maintainer-plan-review",
                  "version": "maintainer-plan-review/v1", "issuers": ["maintainer"],
                  "evidence_forms": ["signed-plan-decision"], "requirements": {}}},
              "code_review": {"mode": "off"},
              "required_checks_digest": required_check_contract(
                  parse_verification_config(config, strict=True))["digest"],
              "builtin_checks_version": "keepsail-baseline/v2", "activation": {"kind": "initial"}}
    policy["policy_digest"] = digest_record(policy)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "add", ".")
    git(root, "commit", "-qm", "trusted snapshot")
    base = git(root, "rev-parse", "HEAD")
    (harness / "verification.yaml").write_text("checks: []\n", encoding="utf-8")
    (harness / "policy-authority.yaml").write_text("disabled: true\n", encoding="utf-8")
    snapshot = read_policy_snapshot(root, base, repository_id="owner/project",
                                    target_ref="refs/heads/main")
    assert snapshot.commit == base
    assert snapshot.checks["checks"][0]["id"] == "test"
    with pytest.raises(ApprovalError, match="supplied repository"):
        read_policy_snapshot(root, base, repository_id="other/project",
                             target_ref="refs/heads/main")
    git(root, "add", ".harness/verification.yaml")
    git(root, "commit", "-qm", "tamper with checks")
    with pytest.raises(ApprovalError, match="checks digest"):
        read_policy_snapshot(root, "HEAD", repository_id="owner/project",
                             target_ref="refs/heads/main")
