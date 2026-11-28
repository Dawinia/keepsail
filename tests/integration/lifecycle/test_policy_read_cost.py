"""Policy reads cost a constant number of git processes, independent of history (C1/C7).

The fixture records N earlier policy transitions on ``main`` (each a policy
change plus its retained v3 attestation).  Nothing replays them, so the git
process counts of ordinary commands must not depend on N.
"""

import pytest

from tests.git_counter import count_git
from tests.integration.lifecycle.policy_repo import (
    OWNER_PROCESS,
    PolicyRepo,
    edited,
    git,
    v2_policy,
)


def build(tmp_path, transitions):
    policy = v2_policy(plan=OWNER_PROCESS, code_review="off")
    repo = PolicyRepo(tmp_path / f"repo-{transitions}", policy)
    git(repo.root, "switch", "-q", "main")
    for index in range(transitions):
        policy = edited(policy, processes_by_kind={"plan": {
            **policy["processes_by_kind"]["plan"], "requirements": {"round": index}}})
        repo.write_policy(policy)
        attestation = repo.harness / f"attestations/v3/transition-{index}.jsonl"
        attestation.parent.mkdir(parents=True, exist_ok=True)
        attestation.write_bytes(b"{}\n")
        repo.commit(f"accepted transition {index}")
    base = git(repo.root, "rev-parse", "HEAD")
    git(repo.root, "switch", "-q", "candidate")
    git(repo.root, "reset", "-q", "--hard", base)
    return repo, policy, base


def measure(tmp_path, monkeypatch, transitions):
    repo, policy, base = build(tmp_path, transitions)
    counts = {}
    subject = repo.plan("ordinary")
    evidence = repo.evidence("ordinary", "plan", subject, OWNER_PROCESS, policy)
    with count_git(monkeypatch) as calls:
        repo.ok("review", "import", "ordinary", "--evidence", "-", data=evidence)
    counts["review import"] = calls.product
    repo.ok("implementation", "start", "ordinary")
    (repo.root / "ordinary.txt").write_bytes(b"ordinary\n")
    repo.commit("ordinary change")
    repo.record("ordinary", ["ordinary.txt"])
    with count_git(monkeypatch) as calls:
        repo.ok("status", "ordinary")
    counts["status"] = calls.product
    with count_git(monkeypatch) as calls:
        repo.ok("done", "ordinary")
    counts["done"] = calls.product
    with count_git(monkeypatch) as calls:
        repo.ok("report")
    counts["report"] = calls.product
    repo.attest("ordinary")
    with count_git(monkeypatch) as calls:
        verified = repo.verify(base)
    assert verified.exit_code == 0, verified.output
    counts["attest verify"] = calls.product
    return counts


@pytest.mark.parametrize("transitions", [3])
def test_command_git_cost_does_not_grow_with_policy_history(tmp_path, monkeypatch, transitions):
    one = measure(tmp_path, monkeypatch, 1)
    many = measure(tmp_path, monkeypatch, transitions)
    assert one == many, (one, many)
    # Acceptance target: done on the 3-transition fixture stays within 60 product git calls.
    assert many["done"] <= 60, many


def test_the_trusted_base_still_rejects_a_policy_that_disagrees_with_its_checks(tmp_path):
    repo, _policy, _base = build(tmp_path, 1)
    git(repo.root, "switch", "-q", "main")
    (repo.harness / "verification.yaml").write_bytes(b"checks: []\n")
    broken = repo.commit("checks changed without updating the policy digest")
    git(repo.root, "switch", "-q", "candidate")
    git(repo.root, "reset", "-q", "--hard", broken)
    result = repo.cli("change", "start", "after-break", "--framework", "plain")
    assert result.exit_code != 0 and "checks digest" in result.output
