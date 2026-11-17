"""Activation replay caching cannot outlive the verification that owns it."""

from pathlib import Path

import pytest

from keepsail.core import attestation_v3_verify as verifier
from keepsail.core.approval import ApprovalError


def test_activation_cache_is_scoped_and_returns_independent_results(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(verifier, "resolve_commit", lambda _root, _ref: "a" * 40)

    def replay(_root, **_kwargs):
        calls.append(True)
        return {"nested": {"calls": len(calls)}}

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
        return {"ok": True}

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
