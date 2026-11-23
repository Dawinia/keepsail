"""First trust is established on a trusted base, never by candidate evidence."""

import base64
import json
import subprocess
import sys
from dataclasses import replace
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.cli import main
from keepsail.core.approval import ApprovalError, canonical_json, digest_record
from keepsail.core.attestation_v3_verify import verify_v2_activation
from keepsail.core.effective_policy import load_effective_v2
from keepsail.core.emit_validation import (
    find_mixed_policy_ordering_violations,
    find_ordering_violations,
)
from keepsail.core.events import Actor, Event, serialize_event
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_init_first_trust_and_light_delivery(tmp_path, knowledge_workspace):
    root = tmp_path / "activated"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "owner@example.invalid")
    git(root, "config", "user.name", "fixture owner")
    runner = CliRunner()

    def cli(*args, data=None):
        return runner.invoke(main, ["--workspace", str(root), *args], input=data)

    initialized = cli("init")
    assert initialized.exit_code == 0, initialized.output
    harness = root / ".harness"
    config = {"layers": {"baseline": {"enabled": False},
                         "framework_adapter": {"enabled": False},
                         "user_checks": {"enabled": True}},
              "checks": [{"id": "fixture", "command": [sys.executable, "-c", "print('ok')"]}]}
    (harness / "verification.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (root / "plan.md").write_text("# Deliver the approved change\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "disabled initial skeleton")
    disabled_base = git(root, "rev-parse", "HEAD")

    key = Ed25519PrivateKey.generate()
    public = base64.b64encode(
        key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode()
    prepared = cli("--json", "policy", "initial", "prepare", "--repository-id", "owner/project",
                   "--target-ref", "refs/heads/main", "--public-key", public)
    assert prepared.exit_code == 0, prepared.output
    proposal = json.loads(prepared.output)["data"]
    assert proposal["authority_effect"] == "unchanged"
    assert proposal["policy"]["code_review"] == {"mode": "off"}
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(proposal["policy"]),
                                                       encoding="utf-8")
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(proposal["authority"]),
                                                     encoding="utf-8")
    git(root, "add", ".harness/review-recognition.yaml", ".harness/policy-authority.yaml")
    git(root, "commit", "-qm", "propose first policy and public key")
    initial = git(root, "rev-parse", "HEAD")
    with pytest.raises(ApprovalError, match="missing"):
        verify_v2_activation(root, trusted_commit=initial, repository_id="owner/project",
                             target_ref="refs/heads/main")

    owner_evidence = {"owner": "fixture owner", "statement": "Confirm this first policy",
                      "evidence_reference": "fixture-owner-approval",
                      "original_evidence": "fixture owner confirmed the exact first commit"}
    confirmed = cli("--json", "policy", "initial", "confirmation", "--initial-commit", initial,
                    "--repository-id", "owner/project", "--target-ref", "refs/heads/main",
                    "--evidence", "-", data=json.dumps(owner_evidence))
    assert confirmed.exit_code == 0, confirmed.output
    confirmation = json.loads(confirmed.output)["data"]
    assert confirmation["authority_effect"] == "unchanged"
    (harness / "policy-initial-trust.json").write_text(
        json.dumps(confirmation["confirmation"]), encoding="utf-8"
    )
    git(root, "add", ".harness/policy-initial-trust.json")
    git(root, "commit", "-qm", "retain fixture owner confirmation")
    trusted = git(root, "rev-parse", "HEAD")
    basis = verify_v2_activation(root, trusted_commit=trusted, repository_id="owner/project",
                                 target_ref="refs/heads/main")
    assert basis["activation_commit"] == initial
    assert basis["confirmation_assurance"] == "retained-owner-claim"
    assert basis["initial_confirmation"] == owner_evidence

    # A candidate may propose these files, but the disabled old base cannot
    # treat the proposal and its self-supplied confirmation as an authorization.
    blocked = cli("--json", "attest", "verify", "--base", disabled_base, "--head", trusted,
                  "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert blocked.exit_code == 2, blocked.output
    assert "initial v2 trust needs separate owner establishment" in blocked.output

    git(root, "switch", "-qc", "tampered-confirmation")
    altered = confirmation["confirmation"].copy()
    altered["owner_confirmation"] = {**owner_evidence, "statement": "Changed after confirmation"}
    (harness / "policy-initial-trust.json").write_text(json.dumps(altered), encoding="utf-8")
    git(root, "add", ".harness/policy-initial-trust.json")
    git(root, "commit", "-qm", "tamper with retained confirmation")
    with pytest.raises(ApprovalError, match="confirmation changed"):
        verify_v2_activation(root, trusted_commit="HEAD", repository_id="owner/project",
                             target_ref="refs/heads/main")
    git(root, "switch", "-qc", "prior-enabled", disabled_base)
    (harness / "review-recognition.yaml").write_text(
        "version: review-recognition/v1\nenabled: true\n", encoding="utf-8"
    )
    git(root, "add", ".harness/review-recognition.yaml")
    git(root, "commit", "-qm", "previously enabled policy")
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(proposal["policy"]),
                                                       encoding="utf-8")
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(proposal["authority"]),
                                                     encoding="utf-8")
    git(root, "add", ".harness/review-recognition.yaml", ".harness/policy-authority.yaml")
    git(root, "commit", "-qm", "attempt to replace old policy as initial")
    fake_initial = git(root, "rev-parse", "HEAD")
    rejected = cli("policy", "initial", "confirmation", "--initial-commit", fake_initial,
                   "--repository-id", "owner/project", "--target-ref", "refs/heads/main",
                   "--evidence", "-", data=json.dumps(owner_evidence))
    assert rejected.exit_code == 2, rejected.output
    assert "previously enabled policy" in rejected.output
    git(root, "switch", "-q", "main")
    git(root, "switch", "-qc", "candidate")
    started = cli("change", "start", "light", "--framework", "plain")
    assert started.exit_code == 0, started.output
    ready = cli("plan", "ready", "light", "--plan", "plan.md", "--scope", "[hello.txt]",
                "--commitment", "goal=Deliver the approved change")
    assert ready.exit_code == 0, ready.output
    subject = derive_state(events_path(root))["light"].pending_revision["subject"]["subject_id"]
    body = {"version": "signed-plan-decision/v1", "repository_id": "owner/project",
            "target_ref": "refs/heads/main", "policy_digest": proposal["policy"]["policy_digest"],
            "change_id": "light", "subject_id": subject, "decision": "approve",
            "evidence_id": "owner-light", "supersedes": None,
            "key_id": proposal["authority"]["keys"][0]["key_id"]}
    body["signature"] = base64.b64encode(key.sign(canonical_json(body).encode())).decode()
    evidence = {"version": "review-evidence/v1", "evidence_id": "owner-light", "kind": "plan",
                "subject_id": subject, "decision": "approve",
                "process": {"id": "maintainer-plan-review", "version": "maintainer-plan-review/v1"},
                "issuer": "maintainer", "form": "signed-plan-decision", "original_evidence": body,
                "provenance": {"policy_digest": proposal["policy"]["policy_digest"]}}
    assert cli("implementation", "start", "light").exit_code == 2
    imported = cli("review", "import", "light", "--evidence", "-", data=json.dumps(evidence))
    assert imported.exit_code == 0, imported.output
    assert cli("implementation", "start", "light").exit_code == 0
    (root / "hello.txt").write_text("hello\n", encoding="utf-8")
    git(root, "add", "hello.txt")
    git(root, "commit", "-qm", "deliver light change")
    assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                  "reasons": ["Implement the approved change"], "references": ["hello.txt"]}
    recorded = cli("implementation", "record", "light", "--assessment", "-",
                   data=json.dumps(assessment))
    assert recorded.exit_code == 0, recorded.output
    done = cli("done", "light")
    assert done.exit_code == 0, done.output
    assert derive_state(events_path(root))["light"].current_state == "READY_TO_MERGE"
    status = cli("--json", "status", "light")
    assert status.exit_code == 0, status.output
    delivery = json.loads(status.output)["data"]["changes"][0]["delivery_policy"]
    assert delivery["trusted_base"] == trusted
    assert delivery["policy_digest"] == proposal["policy"]["policy_digest"]
    assert delivery["code_review_required"] is False
    assert delivery["subject_matches"] is True
    assert delivery["required_checks"] == [{"source": "user", "id": "fixture"}]
    assert delivery["required_project_checks"] == 1
    status_text = cli("status", "light")
    assert "required checks: user/fixture" in status_text.output
    assert "required project checks: 1" in status_text.output
    snapshot = load_effective_v2(root, trusted)
    adapter_only = replace(snapshot, checks={**snapshot.checks, "checks": [
        {"source": "adapter:framework", "id": "adapter-check"}
    ]})
    with patch("keepsail.engineering.delivery_policy.load_effective_v2",
               return_value=adapter_only):
        zero = cli("--json", "status", "light")
        zero_policy = json.loads(zero.output)["data"]["changes"][0]["delivery_policy"]
        assert zero_policy["required_project_checks"] == 0
        assert zero_policy["required_checks"] == [
            {"source": "adapter:framework", "id": "adapter-check"}
        ]
        assert "required project checks: 0" in cli("status", "light").output
        assert "required project checks: 0" in cli("report").output
    report = cli("--json", "report")
    assert report.exit_code == 0, report.output
    policies = json.loads(report.output)["data"]["current_delivery_policies"]
    reported = next(item for item in policies if item["change_id"] == "light")
    assert reported["trusted_base"] == trusted
    assert reported["policy_digest"] == proposal["policy"]["policy_digest"]
    assert reported["required_checks"] == [{"source": "user", "id": "fixture"}]
    assert reported["required_project_checks"] == 1
    assert reported["code_review_required"] is False
    report_text = cli("report")
    assert "required checks: user/fixture" in report_text.output
    assert "required project checks: 1" in report_text.output
    assert "code review required: False" in report_text.output
    body = ("<!-- keepsail:metadata -->\nChange: light\nTier: Normal\n"
            "Verification: passed\nkeepsail version: 0.1.0\n<!-- /keepsail:metadata -->\n")
    with patch("keepsail.cli.pr.gh.view_pr", return_value={"body": body}):
        validated = cli("--json", "pr", "validate", "7")
    assert validated.exit_code == 0, validated.output
    old_violations = find_ordering_violations(events_path(root), "light")
    assert any("built-in v1 does not permit" in item.reason for item in old_violations)
    historical = harness / "historical-events-test.jsonl"
    reopened = Event(event_id="fixture-reopen", type="implementation_invalidated",
                     change_id="light", timestamp="2026-11-15T00:00:00Z",
                     actor=Actor(type="human", identifier="fixture"), framework="plain",
                     payload={"reason": "new implementation epoch"})
    historical.write_bytes(events_path(root).read_bytes()
                           + (serialize_event(reopened) + "\n").encode())
    assert any("built-in v1 does not permit" in item.reason for item in
               find_ordering_violations(historical, "light", repository_root=root))
    assert not find_mixed_policy_ordering_violations(historical, "light", repository_root=root)
    with (patch("keepsail.cli.pr.gh.view_pr", return_value={"body": body}),
          patch("keepsail.cli.pr.load_effective_v2", side_effect=ApprovalError("unavailable"))):
        unavailable = cli("--json", "pr", "validate", "7")
    assert unavailable.exit_code == 2
    assert "trusted delivery policy unavailable" in unavailable.output
    legacy = cli("attest", "write", "light", "--format", "v2")
    assert legacy.exit_code != 0, legacy.output
    assert "requires v3 attestation" in legacy.output
    exported = cli("attest", "write", "light")
    assert exported.exit_code == 0, exported.output
    git(root, "add", ".harness/attestations/v3/light.jsonl")
    git(root, "commit", "-qm", "retain light delivery evidence")
    verified = cli("--json", "attest", "verify", "--base", trusted, "--head", "HEAD",
                   "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert verified.exit_code == 0, verified.output
    decision = json.loads(verified.output)["data"]["delivery_decisions"]["light"]
    assert not decision["code_review_required"]
    assert decision["required_checks"] == [{"source": "user", "id": "fixture"}]
    assert decision["required_project_checks"] == 1
    assert decision["builtin_checks_version"] == "keepsail-baseline/v2"
    verified_text = cli("attest", "verify", "--base", trusted, "--head", "HEAD",
                        "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert verified_text.exit_code == 0, verified_text.output
    assert "required checks: user/fixture" in verified_text.output
    assert "required project checks: 1" in verified_text.output
    assert "code review required: False" in verified_text.output
    # Supply actual v1/v2 records to the real activated-policy verifier.
    from keepsail.core.attestation_format import expand_attestation
    from keepsail.engineering.attestation import write_attestation

    old = knowledge_workspace
    old.deliver()
    (old.root / "legacy-product.txt").write_text("old delivery\n", encoding="utf-8")
    git(old.root, "add", "legacy-product.txt")
    git(old.root, "commit", "-qm", "implement old-policy delivery")
    old_assessment = {"affected_commitments": ["db"], "conclusion": "within_approval",
                      "reasons": ["Exercise the previously approved delivery."],
                      "references": ["legacy-product.txt"]}
    old.cli("implementation", "record", "change-a", "--assessment",
            str(old.write(old_assessment)))
    old.deliver()
    old.cli("done", "change-a")
    old_state = derive_state(old.root / ".harness/events.jsonl")["change-a"]
    old_code = {"version": "review-evidence/v1", "evidence_id": "old-code-review",
                "kind": "code", "subject_id": old_state.current_code_subject["subject_id"],
                "decision": "approve", "process": {"id": "owner-review", "version": "1"},
                "issuer": "owner", "original_evidence": {"decision": "approve"},
                "provenance": {"policy_digest": old.review["process"]["policy_digest"]}}
    old.cli("review", "import", "change-a", "--evidence", str(old.write(old_code)))
    old_log = old.root / ".harness/events.jsonl"
    old_dir = old.root / ".harness/attestations"
    old_v1 = write_attestation(old_log, old_dir, "change-a", format_version="v1-bootstrap")
    old_v2 = write_attestation(old_log, old_dir, "change-a", format_version="v2")
    assert derive_state(old_v1)["change-a"].current_state == "READY_TO_MERGE"
    assert expand_attestation(json.loads(old_v2.read_text(encoding="utf-8")))
    assert derive_state(old_v2)["change-a"].current_state == "READY_TO_MERGE"
    delivery_head = git(root, "rev-parse", "HEAD")
    git(root, "switch", "-qc", "mixed-old-formats")
    legacy = harness / "attestations/change-a.jsonl"
    compact = harness / "attestations/v2/change-a.jsonl"
    compact.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(old_v1.read_bytes())
    compact.write_bytes(old_v2.read_bytes())
    git(root, "add", str(legacy.relative_to(root)), str(compact.relative_to(root)))
    git(root, "commit", "-qm", "attempt mixed old-format attestations")
    mixed = cli("--json", "attest", "verify", "--base", trusted, "--head", "HEAD",
                "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert mixed.exit_code == 2, mixed.output
    mixed_blockers = json.loads(mixed.output)["data"]["blockers"]
    assert sum("active policy requires v3 evidence" in item for item in mixed_blockers) == 2
    assert not any("trusted review policy cannot be read" in item for item in mixed_blockers)
    git(root, "switch", "-q", "candidate")

    # A signed candidate cannot replace an active policy using initial activation.
    from keepsail.core.attestation_v3 import parse_v3_line

    git(root, "switch", "-qc", "initial-replacement", delivery_head)
    changed_policy = json.loads(json.dumps(proposal["policy"]))
    changed_policy["processes_by_kind"]["plan"]["issuers"].append("another-owner")
    changed_policy["policy_digest"] = digest_record({
        k: v for k, v in changed_policy.items() if k != "policy_digest"})
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(changed_policy),
                                                       encoding="utf-8")
    light_path = harness / "attestations/v3/light.jsonl"
    record = parse_v3_line(light_path.read_bytes())
    authorization = {"version": "policy-authorization/v1", "repository_id": "owner/project",
                     "target_ref": "refs/heads/main", "base_sha": trusted,
                     "predecessor_policy_digest": proposal["policy"]["policy_digest"],
                     "target_policy_digest": changed_policy["policy_digest"],
                     "change_id": "light", "plan_subject_id": record["snapshot"]["approval"][
                         "subject_id"], "kind": "transition", "decision": "approve",
                     "permitted_paths": ["plan.md", "hello.txt",
                                         ".harness/review-recognition.yaml"],
                     "key_id": proposal["authority"]["keys"][0]["key_id"],
                     "obligation_changes": []}
    authorization["signature"] = base64.b64encode(
        key.sign(canonical_json(authorization).encode())).decode()
    record["authorization"] = authorization
    record["digest"] = digest_record({k: v for k, v in record.items() if k != "digest"})
    light_path.write_text(canonical_json(record) + "\n", encoding="utf-8")
    git(root, "add", ".harness/review-recognition.yaml", str(light_path.relative_to(root)))
    git(root, "commit", "-qm", "attempt initial replacement of active policy")
    initial_rejected = cli("--json", "attest", "verify", "--base", trusted, "--head", "HEAD",
                           "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert initial_rejected.exit_code == 2, initial_rejected.output
    assert "target policy does not identify this signed transition" in initial_rejected.output
    git(root, "switch", "-q", "candidate")
    blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], cwd=root,
                                   input=b"unsupported path\n").decode().strip()
    tree = subprocess.check_output(["git", "ls-tree", "-z", "HEAD"], cwd=root)
    tree += f"100644 blob {blob}\tsecure\\name.txt\0".encode()
    tree_id = subprocess.check_output(
        ["git", "mktree", "-z"], cwd=root, input=tree
    ).decode().strip()
    head = git(root, "rev-parse", "HEAD")
    weird = subprocess.check_output(["git", "commit-tree", tree_id, "-p", head], cwd=root,
                                    input=b"unsupported path\n").decode().strip()
    refused = cli("--json", "attest", "verify", "--base", trusted, "--head", weird,
                  "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    assert refused.exit_code == 2, refused.output
    blockers = json.loads(refused.output)["data"]["blockers"]
    assert any("secure\\name.txt" in message and "not covered" in message
               for message in blockers), blockers

    # A valid light delivery cannot turn off or damage its already trusted key.
    for damage in ("removed", "disabled", "malformed"):
        git(root, "switch", "-q", "--detach", head)
        authority_path = harness / "policy-authority.yaml"
        if damage == "removed":
            git(root, "rm", "-q", ".harness/policy-authority.yaml")
        else:
            content = (yaml.safe_dump({**proposal["authority"], "enabled": False, "keys": []})
                       if damage == "disabled" else "invalid: [yaml\n")
            authority_path.write_text(content, encoding="utf-8")
            git(root, "add", ".harness/policy-authority.yaml")
        git(root, "commit", "-qm", f"{damage} candidate authority")
        rejected = cli("--json", "attest", "verify", "--base", trusted, "--head", "HEAD",
                       "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
        assert rejected.exit_code == 2, rejected.output
        blockers = json.loads(rejected.output)["data"]["blockers"]
        assert any("authority" in message.lower() or "yaml" in message.lower()
                   for message in blockers), blockers
