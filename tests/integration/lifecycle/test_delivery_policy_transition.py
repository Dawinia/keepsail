"""Risk-boundary changes: plan declaration plus the owner's recorded acceptance.

Minimum regression entry for the delivery-policy transition (2026-11-10, kept by
2026-11-27-git-subprocess-cost C6).  One test walks the whole ordered path to the
verifier installed from the trusted base; the other stages build their own state
so they can run in parallel.
"""

import json
from copy import deepcopy

import pytest

from keepsail.core.approval import (
    ApprovalError,
    canonical_json,
    digest_record,
    recognition_policy_digest,
)
from keepsail.core.attestation_v3_verify import verify_v3_delivery, verify_v3_transition
from keepsail.core.paths import events_path
from keepsail.core.review_verdict import read_change_events
from keepsail.engineering.pr_metadata import build_metadata
from tests.integration.lifecycle.policy_repo import (
    OLD_PROCESS,
    OWNER_PROCESS,
    VERIFICATION,
    PolicyRepo,
    edited,
    git,
    policy_digest,
    v1_policy,
    v2_policy,
    verify_with_installed_base,
)

RISK = "Switch plan review to the owner's json conclusions and stop requiring code review"


def test_risk_boundary_change_sequence_reaches_the_installed_verifier(tmp_path):
    old = v1_policy()
    repo = PolicyRepo(tmp_path / "repo", old, copy_source=True)
    target = v2_policy(plan=OWNER_PROCESS, code_review="off")
    repo.approve("switch", OLD_PROCESS, old, risk_boundary=RISK)
    repo.write_policy(target)
    repo.commit("propose the owner-json policy")
    # The candidate is the committed HEAD: uncommitted policy edits are refused.
    (repo.harness / "review-recognition.yaml").write_text("dirty: true\n", encoding="utf-8")
    dirty = repo.cli("policy", "accept", "switch")
    assert dirty.exit_code == 2 and "uncommitted" in dirty.output
    repo.write_policy(target)
    accepted = repo.ok("--json", "policy", "accept", "switch")
    payload = json.loads(accepted.output)["data"]["acceptance"]
    assert payload["predecessor_policy_digest"] == policy_digest(old)
    assert payload["target_policy_digest"] == policy_digest(target)
    assert payload["target_policy_state"] == "enabled"
    assert {"object": "policy", "path": "/code_review/mode", "direction": "changed",
            "before": "full", "after": "off"} in payload["obligation_changes"]
    again = repo.ok("--json", "policy", "accept", "switch")
    assert json.loads(again.output)["data"]["idempotent"] is True
    repo.record("switch", [".harness/review-recognition.yaml"])
    repo.ok("done", "switch")
    # The Change making the change still delivers under the old (v1: full) obligations.
    assert repo.state("switch").current_state == "AWAITING_CODE_REVIEW"
    repo.code_review("switch", OLD_PROCESS, old)
    assert repo.state("switch").current_state == "READY_TO_MERGE"
    record = repo.attest("switch")
    event = next(e for e in read_change_events(events_path(repo.root), "switch")
                 if e.type == "policy_change_accepted")
    assert record["authorization"] == {
        "acceptance": event.payload, "event_id": event.event_id,
        "actor": {"type": event.actor.type, "identifier": event.actor.identifier},
        "ts": event.timestamp}
    assert event.actor.type == "human"
    verified = repo.verify(repo.base)
    assert verified.exit_code == 0, verified.output
    decision = json.loads(verified.output)["data"]["delivery_decisions"]["switch"]
    assert decision["risk_boundary"]["event_id"] == event.event_id
    assert decision["risk_boundary"]["actor"] == record["authorization"]["actor"]
    assert decision["risk_boundary"]["ts"] == event.timestamp
    assert decision["risk_boundary"]["obligation_changes"] == event.payload["obligation_changes"]
    # Visibility: status, report and PR metadata name the same record.
    status = json.loads(repo.ok("--json", "status", "switch").output)["data"]["changes"][0]
    assert status["risk_boundary"]["acceptance"] == {
        "event_id": event.event_id, "actor": record["authorization"]["actor"],
        "ts": event.timestamp, "matches": True}
    assert status["risk_boundary"]["obligation_changes"] == event.payload["obligation_changes"]
    assert "code review relaxed (full -> off)" in status["risk_boundary"]["labels"]
    report = json.loads(repo.ok("--json", "report").output)["data"]
    shown = next(item for item in report["current_risk_boundary_changes"]
                 if item["change_id"] == "switch")
    assert shown["acceptance"]["event_id"] == event.event_id
    metadata = build_metadata("switch", repo.root)
    assert f"event {event.event_id}" in metadata
    assert f"accepted by {event.actor.identifier} (human) at {event.timestamp}" in metadata
    assert "changed policy/code_review/mode" in metadata
    head = git(repo.root, "rev-parse", "HEAD")
    installed = verify_with_installed_base(repo.root, repo.base, head, label="installed-base")
    assert installed.returncode == 0, installed.stdout + installed.stderr
    # A hand-edited acceptance that no longer matches the recomputation is refused.
    tampered = deepcopy(record)
    tampered["authorization"]["acceptance"]["obligation_changes"] = []
    tampered["digest"] = digest_record({k: v for k, v in tampered.items() if k != "digest"})
    git(repo.root, "switch", "-qc", "tampered")
    path = repo.harness / "attestations/v3/switch.jsonl"
    path.write_bytes((canonical_json(tampered) + "\n").encode("utf-8"))
    repo.commit("tamper with the recorded acceptance")
    with pytest.raises(ApprovalError, match="does not match the recomputed change"):
        verify_v3_transition(repo.root, tampered, base=repo.base, head="HEAD")
    assert repo.verify(repo.base).exit_code == 2


def test_ordinary_delivery_under_an_adopted_policy_needs_no_acceptance(tmp_path):
    policy = v2_policy(plan=OWNER_PROCESS, code_review="off")
    repo = PolicyRepo(tmp_path / "repo", policy)
    repo.approve("ordinary", OWNER_PROCESS, policy)
    (repo.root / "ordinary.txt").write_text("ordinary\n", encoding="utf-8")
    repo.commit("ordinary change")
    repo.record("ordinary", ["ordinary.txt"])
    assert repo.cli("policy", "accept", "ordinary").exit_code == 2
    repo.ok("done", "ordinary")
    assert repo.state("ordinary").current_state == "READY_TO_MERGE"
    record = repo.attest("ordinary")
    assert record["authorization"] is None
    verified = repo.verify(repo.base)
    assert verified.exit_code == 0, verified.output
    decision = json.loads(verified.output)["data"]["delivery_decisions"]["ordinary"]
    assert decision["risk_boundary"] is None and decision["code_review_required"] is False
    assert verify_v3_delivery(repo.root, record, base=repo.base, head="HEAD")[
        "target_policy_digest"] == policy_digest(policy)


def test_next_change_from_v2_strengthens_review_and_keeps_the_old_obligations(tmp_path):
    policy = v2_policy(plan=OWNER_PROCESS, code_review="off")
    repo = PolicyRepo(tmp_path / "repo", policy)
    target = v2_policy(plan=OWNER_PROCESS, code_review="full")
    repo.approve("strengthen", OWNER_PROCESS, policy, risk_boundary="Require code review")
    repo.write_policy(target)
    repo.commit("require code review")
    repo.record("strengthen", [".harness/review-recognition.yaml"])
    refused = repo.cli("done", "strengthen")
    assert refused.exit_code == 2 and "policy accept" in refused.output
    repo.ok("policy", "accept", "strengthen")
    repo.ok("done", "strengthen")
    # Delivered under the base's `off`, not the candidate's `full`.
    assert repo.state("strengthen").current_state == "READY_TO_MERGE"
    repo.attest("strengthen")
    verified = repo.verify(repo.base)
    assert verified.exit_code == 0, verified.output
    labels = json.loads(verified.output)["data"]["delivery_decisions"]["strengthen"][
        "risk_boundary"]["labels"]
    assert "code review strengthened (off -> full)" in labels


def test_in_flight_change_needs_a_new_approval_after_the_policy_changes(tmp_path):
    old = v1_policy()
    repo = PolicyRepo(tmp_path / "repo", old)
    subject = repo.approve("inflight", OLD_PROCESS, old)
    (repo.root / "feature.txt").write_text("feature\n", encoding="utf-8")
    repo.commit("in-flight work")
    repo.record("inflight", ["feature.txt"])
    target = v2_policy(plan=OWNER_PROCESS, code_review="off")
    git(repo.root, "switch", "-q", "main")
    repo.write_policy(target)
    merged = repo.commit("a separate Change switched the policy and merged")
    git(repo.root, "switch", "-q", "candidate")
    git(repo.root, "merge", "-q", "--no-edit", "main")
    status = json.loads(repo.ok("--json", "status", "inflight").output)["data"]["changes"][0]
    assert status["approval_recognition"]["recognized"] is False
    assert "no longer in the effective policy" in status["approval_recognition"]["reason"]
    assert "plan approval not recognized" in repo.ok("status", "inflight").output
    refused = repo.cli("done", "inflight")
    assert refused.exit_code == 2 and "no longer in the effective policy" in refused.output
    revised = repo.revise("inflight")
    assert revised != subject  # a revision records its prior approval
    repo.ok("review", "import", "inflight", "--evidence", "-", data=repo.evidence(
        "inflight", "plan", revised, OWNER_PROCESS, target))
    repo.record("inflight", ["feature.txt"])
    repo.ok("done", "inflight")
    assert repo.state("inflight").current_state == "READY_TO_MERGE"
    repo.attest("inflight")
    assert repo.verify(merged).exit_code == 0


@pytest.mark.parametrize("case", ["v1-disabled", "v2-removed", "v2-to-disabled-v1"])
def test_deactivation_is_a_recorded_change_delivered_under_the_old_obligations(tmp_path, case):
    old = v1_policy() if case == "v1-disabled" else v2_policy(plan=OWNER_PROCESS,
                                                             code_review="full")
    process = OLD_PROCESS if case == "v1-disabled" else OWNER_PROCESS
    repo = PolicyRepo(tmp_path / "repo", old)
    repo.approve("deactivate", process, old, risk_boundary="Stop using keepsail recognition")
    repo.write_policy(None if case == "v2-removed" else v1_policy(enabled=False))
    repo.commit("deactivate the policy")
    repo.record("deactivate", [".harness/review-recognition.yaml"])
    refused = repo.cli("done", "deactivate")
    assert refused.exit_code == 2 and "policy accept" in refused.output
    accepted = json.loads(repo.ok("--json", "policy", "accept", "deactivate").output)["data"]
    payload = accepted["acceptance"]
    state = "removed" if case == "v2-removed" else "disabled"
    assert payload["target_policy_digest"] is None
    assert payload["target_policy_state"] == state
    rows = payload["obligation_changes"]
    assert {"object": "policy", "path": "/state", "direction": "changed",
            "before": "enabled", "after": state} in rows
    removed = {row["path"] for row in rows if row["direction"] == "removed"}
    assert {"/code_review/mode", "/processes_by_kind/plan/id"} <= removed
    repo.ok("done", "deactivate")
    # Old full review still applies to the deactivating Change itself.
    assert repo.state("deactivate").current_state == "AWAITING_CODE_REVIEW"
    repo.code_review("deactivate", process, old)
    record = repo.attest("deactivate")
    assert record["authorization"]["acceptance"]["target_policy_state"] == state
    verified = repo.verify(repo.base)
    assert verified.exit_code == 0, verified.output
    assert "missing" not in verified.output


def test_checks_only_change_under_a_v1_base_is_accepted_and_delivered_as_v3(tmp_path):
    old = v1_policy()
    repo = PolicyRepo(tmp_path / "repo", old)
    repo.approve("checks", OLD_PROCESS, old, risk_boundary="Add a required lint check")
    added = deepcopy(VERIFICATION)
    added["checks"].append({"id": "lint", "command": VERIFICATION["checks"][0]["command"]})
    repo.write_verification(added)
    repo.commit("add a required check")
    (repo.harness / "verification.yaml").write_text("checks: []\n", encoding="utf-8")
    dirty = repo.cli("policy", "accept", "checks")
    assert dirty.exit_code == 2 and "uncommitted" in dirty.output
    repo.write_verification(added)
    payload = json.loads(repo.ok("--json", "policy", "accept", "checks").output)["data"]
    assert "required check added: user/lint" in payload["labels"]
    assert payload["acceptance"]["target_policy_digest"] == policy_digest(old)
    repo.record("checks", [".harness/verification.yaml"])
    repo.ok("done", "checks")
    repo.code_review("checks", OLD_PROCESS, old)
    record = repo.attest("checks")
    assert record["schema_version"] == "attestation/v3"
    assert repo.verify(repo.base).exit_code == 0


def test_acceptance_binds_the_effective_plan_and_the_recomputed_change(tmp_path):
    old = v2_policy(plan=OWNER_PROCESS, code_review="off")
    repo = PolicyRepo(tmp_path / "repo", old)
    # Without the RISK-BOUNDARY commitment neither accept nor done proceeds.
    repo.approve("bind", OWNER_PROCESS, old)
    target = v2_policy(plan=OWNER_PROCESS, code_review="full")
    repo.write_policy(target)
    repo.commit("require review")
    repo.record("bind", [".harness/review-recognition.yaml"])
    for args in (("policy", "accept", "bind"), ("done", "bind")):
        result = repo.cli(*args)
        assert result.exit_code == 2 and "RISK-BOUNDARY" in result.output
    # Plan A is approved with the declaration and accepted ...
    subject_a = repo.revise("bind", risk_boundary="Require code review")
    assert repo.cli("policy", "accept", "bind").exit_code == 2  # pending revision only
    prior = repo.state("bind").effective_approval["evidence_id"]
    repo.ok("review", "import", "bind", "--evidence", "-", data=repo.evidence(
        "bind", "plan", subject_a, OWNER_PROCESS, old, evidence_id="plan-a"))
    assert prior != "plan-a"
    repo.ok("policy", "accept", "bind")
    # ... then revised to plan B: the acceptance of A no longer counts.
    (repo.root / "plan.md").write_text("# Deliver the revised change\n", encoding="utf-8")
    repo.commit("revise the plan")
    subject_b = repo.revise("bind", risk_boundary="Require code review (revised)")
    assert subject_b != subject_a
    repo.ok("review", "import", "bind", "--evidence", "-", data=repo.evidence(
        "bind", "plan", subject_b, OWNER_PROCESS, old, evidence_id="plan-b"))
    repo.record("bind", [".harness/review-recognition.yaml", "plan.md"])
    stale = repo.cli("done", "bind")
    assert stale.exit_code == 2 and "does not match the recomputed change" in stale.output
    assert "STALE" in repo.ok("status", "bind").output
    repo.ok("policy", "accept", "bind")
    # A code fix and a rebase keep the acceptance valid ...
    (repo.root / "fix.txt").write_text("fix\n", encoding="utf-8")
    repo.commit("code fix")
    git(repo.root, "switch", "-q", "main")
    (repo.root / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
    moved = repo.commit("main moves on")
    git(repo.root, "switch", "-q", "candidate")
    git(repo.root, "rebase", "-q", "main")
    repo.record("bind", [".harness/review-recognition.yaml", "plan.md", "fix.txt"])
    repo.ok("done", "bind")
    assert repo.state("bind").current_state == "READY_TO_MERGE"
    repo.attest("bind")
    assert repo.verify(moved).exit_code == 0
    # ... while a further edit of the target policy or of a check invalidates it.
    repo.ok("implementation", "reopen", "bind", "--reason", "change the target again")
    repo.write_policy(edited(target, builtin_checks_version="keepsail-baseline/v2",
                             code_review={"mode": "scope", "scope": ["src"]}))
    repo.commit("narrow the target policy")
    repo.record("bind", [".harness/review-recognition.yaml", "plan.md", "fix.txt"])
    assert "does not match the recomputed change" in repo.cli("done", "bind").output
    repo.write_policy(target)
    longer = deepcopy(VERIFICATION)
    longer["checks"][0]["timeout_seconds"] = 77
    repo.write_verification(longer)
    repo.write_policy(edited(target, required_checks_digest=__import__(
        "tests.integration.lifecycle.policy_repo", fromlist=["checks_digest"]).checks_digest(
            longer)))
    repo.commit("change a check definition")
    repo.record("bind", [".harness/review-recognition.yaml", ".harness/verification.yaml",
                         "plan.md", "fix.txt"])
    assert "does not match the recomputed change" in repo.cli("done", "bind").output


def test_policy_accept_refuses_without_an_effective_approval(tmp_path):
    old = v1_policy()
    repo = PolicyRepo(tmp_path / "repo", old)
    repo.plan("pending", risk_boundary="Replace the process")
    repo.write_policy(v1_policy({"id": "new", "version": "v2", "issuer": "new"}))
    repo.commit("candidate policy")
    result = repo.cli("policy", "accept", "pending")
    assert result.exit_code == 2 and "pending or rejected" in result.output
    subject = repo.state("pending").pending_revision["subject"]["subject_id"]
    repo.ok("review", "import", "pending", "--evidence", "-", data=repo.evidence(
        "pending", "plan", subject, OLD_PROCESS, old, decision="reject"))
    rejected = repo.cli("policy", "accept", "pending")
    assert rejected.exit_code == 2 and "pending or rejected" in rejected.output
    assert repo.cli("policy", "accept", "missing").exit_code == 2


def test_removing_the_legacy_authority_file_needs_no_acceptance(tmp_path):
    policy = v2_policy(plan=OWNER_PROCESS, code_review="off")
    repo = PolicyRepo(tmp_path / "repo", policy,
                      extra={".harness/policy-authority.yaml": "version: policy-authority/v1\n"})
    status = repo.ok("status")
    assert "no longer used and can be deleted" in status.output
    repo.approve("cleanup", OWNER_PROCESS, policy)
    (repo.harness / "policy-authority.yaml").unlink()
    repo.commit("delete the legacy authority file")
    repo.record("cleanup", [".harness/policy-authority.yaml"])
    repo.ok("done", "cleanup")
    record = repo.attest("cleanup")
    assert record["authorization"] is None
    assert repo.verify(repo.base).exit_code == 0


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_trusted_signed_plan_policy_is_refused_everywhere_with_migration_guidance(
    tmp_path, version,
):
    old = v1_policy()
    repo = PolicyRepo(tmp_path / "repo", old)
    subject = repo.plan("signed")
    repo.approve("working", OLD_PROCESS, old)
    (repo.root / "working.txt").write_bytes(b"working\n")
    repo.commit("in-progress work")
    repo.record("working", ["working.txt"])
    if version == "v2":
        signed = v2_policy(plan=OWNER_PROCESS, code_review="off")
        signed["processes_by_kind"]["plan"] = {
            "id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
            "issuers": ["maintainer"], "evidence_forms": ["signed-plan-decision"],
            "requirements": {}}
        signed["activation"] = {"kind": "initial"}
        signed = edited(signed)
    else:
        # A v1 policy listing the form was never signature-verified; it is refused too.
        signed = v1_policy({"id": "maintainer-plan-review",
                            "version": "maintainer-plan-review/v1", "issuer": "maintainer"})
        signed["process"]["evidence_forms"] = ["json", "signed-plan-decision"]
        signed["process"].pop("policy_digest")
        signed["process"]["policy_digest"] = recognition_policy_digest(signed)
    git(repo.root, "switch", "-q", "main")
    repo.write_policy(signed)
    deployed = repo.commit("an already deployed signed-plan policy")
    git(repo.root, "switch", "-q", "candidate")
    git(repo.root, "merge", "-q", "--no-edit", "main")
    maintainer = {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1",
                  "issuer": "maintainer"}
    # Neither the signed form nor an unsigned json conclusion stands in for it.
    for process, form in ((maintainer, "signed-plan-decision"), (maintainer, "json"),
                          (OWNER_PROCESS, "json")):
        evidence = repo.evidence("signed", "plan", subject, process, signed,
                                 evidence_id=f"plan-{process['id']}-{form}")
        evidence["form"] = form
        refused = repo.cli("review", "import", "signed", "--evidence", "-", data=evidence)
        assert refused.exit_code == 2 and "previous keepsail version" in refused.output
    assert "previous keepsail version" in repo.cli("--json", "status", "signed").output
    assert "previous keepsail version" in repo.cli("policy", "accept", "signed").output
    assert "previous keepsail version" in repo.cli("change", "start", "other").output
    assert "previous keepsail version" in repo.cli("done", "working").output
    # The gate reads the trusted policy on the path of the evidence it verifies:
    # v3 under a v2 base, the flat attestation under a v1 base.
    folder = repo.harness / ("attestations/v3" if version == "v2" else "attestations")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "signed.jsonl").write_text("{}\n", encoding="utf-8")
    repo.commit("any delivery")
    verdict = repo.verify(deployed)
    assert verdict.exit_code == 2 and "previous keepsail version" in verdict.output
