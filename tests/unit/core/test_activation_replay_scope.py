"""Activation replay caching cannot outlive the verification that owns it."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from keepsail.core import attestation_v3_verify as verifier
from keepsail.core import effective_policy, initial_policy
from keepsail.core.approval import ApprovalError
from keepsail.core.policy_snapshot import PolicySnapshot


def test_activation_cache_is_scoped_and_returns_independent_results(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(verifier, "resolve_commit", lambda _root, _ref: "a" * 40)

    def replay(_root, **_kwargs):
        calls.append(True)
        return {"nested": {"calls": len(calls)}}, None

    monkeypatch.setattr(verifier, "_verify_v2_activation", replay)

    def run():
        return verifier.verify_v2_activation(
            Path(tmp_path), trusted_commit="main", repository_id="owner/repo",
            target_ref="refs/heads/main",
        )

    @verifier._with_activation_scope
    def same_verification():
        first = run()
        first["nested"]["calls"] = 999
        assert run()["nested"]["calls"] == 1

    same_verification()
    assert len(calls) == 1
    assert run()["nested"]["calls"] == 2
    assert len(calls) == 2


def test_activation_failure_does_not_become_a_cached_success(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(verifier, "resolve_commit", lambda _root, _ref: "a" * 40)

    def replay(_root, **_kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise ApprovalError("first attempt failed")
        return {"ok": True}, None

    monkeypatch.setattr(verifier, "_verify_v2_activation", replay)

    @verifier._with_activation_scope
    def same_verification():
        with pytest.raises(ApprovalError, match="first attempt"):
            verifier.verify_v2_activation(tmp_path, trusted_commit="main", repository_id="r",
                                          target_ref="refs/heads/main")
        assert verifier.verify_v2_activation(
            tmp_path, trusted_commit="main", repository_id="r", target_ref="refs/heads/main"
        ) == {"ok": True}

    same_verification()
    assert len(calls) == 2


def test_replayed_snapshots_are_independent_and_do_not_outlive_the_operation(tmp_path, monkeypatch):
    calls = []
    commit = "a" * 40
    monkeypatch.setattr(verifier, "resolve_commit", lambda *_args: commit)

    def replay(_root, **_kwargs):
        calls.append(True)
        snapshot = PolicySnapshot(commit, None, None, {"digest": "original"})
        return {"ok": True}, snapshot

    monkeypatch.setattr(verifier, "_verify_v2_activation", replay)

    def snapshot():
        return verifier._verified_v2_snapshot(
            tmp_path, trusted_commit="main", repository_id="owner/repo",
            target_ref="refs/heads/main",
        )

    with verifier.activation_replay_scope():
        first = snapshot()
        first.checks["digest"] = "mutated"
        assert snapshot().checks["digest"] == "original"
        assert len(calls) == 1
    assert snapshot().checks["digest"] == "original"
    assert len(calls) == 2


def test_replayed_snapshot_does_not_hide_a_moving_base(tmp_path, monkeypatch):
    current = ["a" * 40]
    calls = []
    monkeypatch.setattr(verifier, "resolve_commit", lambda *_args: current[0])

    def replay(_root, *, trusted_commit, **_kwargs):
        calls.append(trusted_commit)
        return {"ok": True}, PolicySnapshot(trusted_commit, None, None, {})

    monkeypatch.setattr(verifier, "_verify_v2_activation", replay)
    with verifier.activation_replay_scope():
        first = verifier._verified_v2_snapshot(
            tmp_path, trusted_commit="main", repository_id="owner/repo",
            target_ref="refs/heads/main",
        )
        current[0] = "b" * 40
        second = verifier._verified_v2_snapshot(
            tmp_path, trusted_commit="main", repository_id="owner/repo",
            target_ref="refs/heads/main",
        )
    assert first.commit != second.commit
    assert calls == ["a" * 40, "b" * 40]


def test_effective_policy_is_the_snapshot_that_was_actually_replayed(tmp_path, monkeypatch):
    commit = "a" * 40
    authority = SimpleNamespace(digest="authority", repository_id="owner/repo",
                                target_ref="refs/heads/main")
    verified = PolicySnapshot(commit, SimpleNamespace(
        activation={"kind": "initial"}, policy_digest="verified",
    ), authority, {"digest": "checks"})
    changed = PolicySnapshot(commit, SimpleNamespace(
        activation={"kind": "initial"}, policy_digest="changed-after-replay",
    ), authority, {"digest": "checks"})
    reads = []

    def read_snapshot(*_args, **_kwargs):
        reads.append(True)
        return verified if len(reads) == 1 else changed

    monkeypatch.setattr(verifier, "resolve_commit", lambda *_args: commit)
    monkeypatch.setattr(effective_policy, "resolve_commit", lambda *_args: commit)
    monkeypatch.setattr(effective_policy, "regular_blob_text", lambda *_args: "authority")
    monkeypatch.setattr(effective_policy, "parse_authority_yaml", lambda _text: authority)
    monkeypatch.setattr(verifier, "read_policy_snapshot", read_snapshot)
    monkeypatch.setattr(effective_policy, "read_policy_snapshot", read_snapshot, raising=False)
    monkeypatch.setattr(initial_policy, "verify_initial_policy", lambda *_args, **_kwargs: {
        "initial_authority_digest": "authority", "initial_commit": commit,
        "confirmation": {}, "confirmation_assurance": "test",
    })

    result = effective_policy.load_effective_v2(tmp_path, "main")
    assert result.policy.policy_digest == "verified"
    assert len(reads) == 1
