"""First trust is established on a trusted base, never by candidate evidence."""

import base64
import json
import subprocess
import sys

import pytest
import yaml
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.cli import main
from keepsail.core.approval import ApprovalError, canonical_json
from keepsail.core.attestation_v3_verify import verify_v2_activation
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_init_first_trust_and_light_delivery(tmp_path):
    root = tmp_path
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
    assert not json.loads(verified.output)["data"]["delivery_decisions"]["light"][
        "code_review_required"]
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
    assert "unsupported literal Git path" in refused.output
