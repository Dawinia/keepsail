"""policy-acceptance/v1: risk-boundary detection, complete difference, record shape.

Also run against the installed wheel in CI (``delivery-policy-wheel``) to show
the new mechanism needs no ``cryptography``.
"""

import importlib.metadata
import subprocess
import sys
from copy import deepcopy

import pytest
import yaml

from keepsail.core.approval import ApprovalError, recognition_policy_digest
from keepsail.core.risk_boundary import (
    compare_risk_boundary,
    require_matching_acceptance,
    validate_acceptance_payload,
    validate_authorization_record,
)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def v1(process_id="old", *, enabled=True):
    raw = {"version": "review-recognition/v1", "enabled": enabled, "process": {
        "id": process_id, "version": "v1", "kinds": ["plan", "code"], "issuers": ["owner"],
        "evidence_forms": ["json"]}}
    if enabled:
        raw["process"]["policy_digest"] = recognition_policy_digest(raw)
    return raw


@pytest.fixture
def repo(tmp_path):
    harness = tmp_path / ".harness"
    harness.mkdir()
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(v1()), encoding="utf-8")
    (harness / "verification.yaml").write_text(
        "checks:\n- id: fixture\n  command: [python, -c, pass]\n", encoding="utf-8")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "fixture")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def commit_policy(root, raw):
    path = root / ".harness/review-recognition.yaml"
    if raw is None:
        path.unlink()
    else:
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "candidate")
    return git(root, "rev-parse", "HEAD")


def test_unchanged_policy_is_not_a_risk_boundary(repo):
    head = git(repo, "rev-parse", "HEAD")
    boundary = compare_risk_boundary(repo, base=head, head=head)
    assert boundary is not None and not boundary.changed and boundary.differences == []


def test_no_enabled_base_means_adoption_not_a_risk_boundary(repo):
    disabled = commit_policy(repo, v1(enabled=False))
    head = commit_policy(repo, v1("new"))
    assert compare_risk_boundary(repo, base=disabled, head=head) is None


@pytest.mark.parametrize(("target", "state"), [
    (v1("new"), "enabled"), (v1(enabled=False), "disabled"), (None, "removed")])
def test_acceptance_payload_is_recomputed_and_compared_exactly(repo, target, state):
    base = git(repo, "rev-parse", "HEAD")
    head = commit_policy(repo, target)
    boundary = compare_risk_boundary(repo, base=base, head=head)
    assert boundary is not None and boundary.changed
    payload = boundary.acceptance(change_id="delivery", plan_subject_id="plan:one")
    assert validate_acceptance_payload(deepcopy(payload)) == payload
    assert payload["target_policy_state"] == state
    assert (payload["target_policy_digest"] is None) == (state != "enabled")
    require_matching_acceptance(boundary, payload, change_id="delivery",
                                plan_subject_id="plan:one")
    for key, value in (("plan_subject_id", "plan:other"), ("obligation_changes", []),
                       ("target_checks_digest", "0" * 64)):
        with pytest.raises(ApprovalError, match="does not match the recomputed change"):
            require_matching_acceptance(boundary, {**payload, key: value},
                                        change_id="delivery", plan_subject_id="plan:one")


@pytest.mark.parametrize("mutate", [
    lambda p: p.pop("obligation_changes"),
    lambda p: p.update(version="policy-acceptance/v0"),
    lambda p: p.update(extra=True),
    lambda p: p.update(target_policy_state="paused"),
    lambda p: p.update(target_policy_state="enabled", target_policy_digest=None),
    lambda p: p.update(target_policy_state="disabled", target_policy_digest="a" * 64),
    lambda p: p.update(change_id=""),
    lambda p: p.update(obligation_changes=[{"object": "policy", "path": "/x",
                                            "direction": "added"}]),
    lambda p: p.update(obligation_changes=[{"object": "other", "path": "/x",
                                            "direction": "changed", "before": 1, "after": 2}]),
])
def test_acceptance_payload_shape_is_strict(mutate):
    payload = {"version": "policy-acceptance/v1", "change_id": "delivery",
               "plan_subject_id": "plan:one", "predecessor_policy_digest": "a" * 64,
               "target_policy_digest": "b" * 64, "target_policy_state": "enabled",
               "predecessor_checks_digest": "c" * 64, "target_checks_digest": "c" * 64,
               "obligation_changes": [{"object": "policy", "path": "/version",
                                       "direction": "changed", "before": 1, "after": 2}]}
    assert validate_acceptance_payload(deepcopy(payload)) == payload
    mutate(payload)
    with pytest.raises(ApprovalError):
        validate_acceptance_payload(payload)


def test_v3_authorization_holds_the_event_envelope_and_refuses_signed_records():
    acceptance = {"version": "policy-acceptance/v1", "change_id": "delivery",
                  "plan_subject_id": "plan:one", "predecessor_policy_digest": "a" * 64,
                  "target_policy_digest": None, "target_policy_state": "removed",
                  "predecessor_checks_digest": "c" * 64, "target_checks_digest": "c" * 64,
                  "obligation_changes": []}
    record = {"acceptance": acceptance, "event_id": "ev_1",
              "actor": {"type": "human", "identifier": "owner"}, "ts": "2026-11-28T00:00:00Z"}
    assert validate_authorization_record(record) == record
    for broken in ({**record, "actor": {"type": "human"}}, {**record, "ts": ""},
                   {k: v for k, v in record.items() if k != "event_id"}):
        with pytest.raises(ApprovalError):
            validate_authorization_record(broken)
    for legacy in ({"version": "policy-authorization/v1", "kind": "transition"},
                   {"kind": "recovery"}, {"kind": "rotate_key"}):
        with pytest.raises(ApprovalError, match="policy accept"):
            validate_authorization_record(legacy)


def test_keepsail_runs_without_cryptography():
    """The shipped product neither declares nor imports cryptography."""
    requirements = importlib.metadata.requires("keepsail") or []
    runtime = [item for item in requirements if "extra ==" not in item]
    assert not any(item.lower().startswith("cryptography") for item in runtime)
    program = (
        "import sys, importlib, pkgutil\n"
        "sys.modules['cryptography'] = None\n"
        "import keepsail\n"
        "skipped = {'keepsail.daemon.server', 'keepsail.daemon.supervisor'}\n"
        "for module in pkgutil.walk_packages(keepsail.__path__, 'keepsail.'):\n"
        "    if module.name not in skipped:\n"
        "        importlib.import_module(module.name)\n"
        "from keepsail.cli import main\n"
        "sys.argv = ['keepsail', 'policy', 'accept', '--help']\n"
        "main()\n"
    )
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "owner's acceptance" in result.stdout
