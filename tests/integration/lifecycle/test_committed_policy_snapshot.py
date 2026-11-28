"""Policy inputs must all come from the selected Git object, read directly."""

import subprocess

import pytest
import yaml

from keepsail.core.approval import ApprovalError, digest_record
from keepsail.core.effective_policy import load_effective_v2
from keepsail.engineering.delivery_policy import read_policy_snapshot
from keepsail.engineering.verification_config import (
    parse_verification_config,
    required_check_contract,
)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_snapshot_binds_policy_and_config_to_committed_blobs(tmp_path):
    root = tmp_path
    harness = root / ".harness"
    harness.mkdir()
    config = "checks:\n  - id: test\n    command: [python, -m, pytest]\n"
    (harness / "verification.yaml").write_text(config, encoding="utf-8")
    policy = {"version": "review-recognition/v2", "enabled": True,
              "processes_by_kind": {"plan": {"id": "owner-plan-review",
                  "version": "owner-plan-review/v1", "issuers": ["owner"],
                  "evidence_forms": ["json"], "requirements": {}}},
              "code_review": {"mode": "off"},
              "required_checks_digest": required_check_contract(
                  parse_verification_config(config, strict=True))["digest"],
              "builtin_checks_version": "keepsail-baseline/v2"}
    policy["policy_digest"] = digest_record(policy)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "add", ".")
    git(root, "commit", "-qm", "trusted snapshot")
    base = git(root, "rev-parse", "HEAD")
    # Workspace edits never select the snapshot.
    (harness / "verification.yaml").write_text("checks: []\n", encoding="utf-8")
    snapshot = read_policy_snapshot(root, base)
    assert snapshot.commit == base
    assert snapshot.policy.policy_digest == policy["policy_digest"]
    assert snapshot.checks["checks"][0]["id"] == "test"
    assert load_effective_v2(root, base).policy.activation is None
    git(root, "add", ".harness/verification.yaml")
    git(root, "commit", "-qm", "change checks without updating the policy digest")
    with pytest.raises(ApprovalError, match="checks digest"):
        read_policy_snapshot(root, "HEAD")
    with pytest.raises(ApprovalError, match="checks digest"):
        load_effective_v2(root, "HEAD")


def test_trusted_signed_plan_policy_is_refused_with_migration_guidance(tmp_path):
    root = tmp_path
    harness = root / ".harness"
    harness.mkdir()
    config = "checks:\n  - id: test\n    command: [python, -m, pytest]\n"
    (harness / "verification.yaml").write_text(config, encoding="utf-8")
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
    git(root, "commit", "-qm", "deployed signed-plan policy")
    assert read_policy_snapshot(root, "HEAD").policy.activation == {"kind": "initial"}
    with pytest.raises(ApprovalError, match="previous keepsail version"):
        load_effective_v2(root, "HEAD")
