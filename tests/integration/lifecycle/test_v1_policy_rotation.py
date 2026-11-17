"""A signed v1 authority rotation retains the existing delivery obligations."""

import base64
import json
import subprocess
import sys
from hashlib import sha256

import yaml
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.cli import main
from keepsail.core.approval import canonical_json, recognition_policy_digest
from keepsail.core.paths import events_path
from keepsail.core.policy_authority import parse_authority
from keepsail.core.reducer import derive_state


def test_v1_signed_rotation_delivers_v3_with_the_old_review_and_checks(tmp_path):
    root = tmp_path / "repo"
    harness = root / ".harness"
    harness.mkdir(parents=True)

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    def authority(key):
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return {"version": "policy-authority/v1", "repository_id": "owner/project",
                "target_ref": "refs/heads/main", "enabled": True, "keys": [{
                    "key_id": sha256(public).hexdigest(), "algorithm": "ed25519",
                    "public_key": base64.b64encode(public).decode("ascii"),
                    "purposes": ["policy-transition"]}]}

    old_key, new_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    old_raw, new_raw = authority(old_key), authority(new_key)
    old, new = parse_authority(old_raw), parse_authority(new_raw)
    policy = {"version": "review-recognition/v1", "enabled": True, "process": {
        "id": "old-review", "version": "v1", "kinds": ["plan", "code"],
        "issuers": ["old-reviewer"], "evidence_forms": ["json"]}}
    policy["process"]["policy_digest"] = recognition_policy_digest(policy)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(policy), encoding="utf-8")
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(old_raw), encoding="utf-8")
    checks = {"layers": {"baseline": {"enabled": False},
                         "framework_adapter": {"enabled": False}, "user_checks": {"enabled": True}},
              "checks": [{"id": "fixture", "command": [sys.executable, "-c", "print('ok')"]}]}
    (harness / "verification.yaml").write_text(yaml.safe_dump(checks), encoding="utf-8")
    (root / "plan.md").write_text("# Rotate the trusted key\n", encoding="utf-8")
    (root / ".gitignore").write_text(
        ".harness/events.jsonl\n.harness/state.yaml\n", encoding="utf-8")
    git("init", "-q", "-b", "main")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "fixture")
    git("add", ".")
    git("commit", "-qm", "trusted v1 base")
    base = git("rev-parse", "HEAD")
    git("switch", "-qc", "candidate")
    runner = CliRunner()

    def cli(*args, data=None):
        return runner.invoke(main, ["--workspace", str(root), *args], input=data)

    def accepted(*args, data=None):
        result = cli(*args, data=data)
        assert result.exit_code == 0, result.output
        return result

    accepted("change", "start", "rotation", "--framework", "plain")
    accepted("plan", "ready", "rotation", "--plan", "plan.md",
             "--scope", "[plan.md,.harness/policy-authority.yaml]",
             "--commitment", "goal=Rotate the trusted key")
    subject = derive_state(events_path(root))["rotation"].pending_revision["subject"]["subject_id"]
    digest = policy["process"]["policy_digest"]
    authorization = {"version": "policy-authorization/v1", "repository_id": "owner/project",
        "target_ref": "refs/heads/main", "base_sha": base,
        "predecessor_policy_digest": digest, "target_policy_digest": digest,
        "predecessor_authority_digest": old.digest, "target_authority_digest": new.digest,
        "change_id": "rotation", "plan_subject_id": subject, "kind": "rotate_key",
        "permitted_paths": ["plan.md", ".harness/policy-authority.yaml"],
        "decision": "approve", "key_id": old.key_id}
    authorization["signature"] = base64.b64encode(
        old_key.sign(canonical_json(authorization).encode("utf-8"))).decode("ascii")
    proposal = tmp_path / "target-authority.yaml"
    proposal.write_text(yaml.safe_dump(new_raw), encoding="utf-8")
    accepted("policy", "authorization", "import", "rotation", "--evidence", "-",
             "--repository-id", "owner/project", "--target-ref", "refs/heads/main",
             "--target-authority", str(proposal), data=json.dumps(authorization))

    def review(kind, subject_id):
        return {"version": "review-evidence/v1", "evidence_id": f"old-{kind}", "kind": kind,
                "subject_id": subject_id, "decision": "approve",
                "process": {"id": "old-review", "version": "v1"}, "issuer": "old-reviewer",
                "form": "json", "original_evidence": {"decision": "approve"},
                "provenance": {"policy_digest": digest}}

    accepted("review", "import", "rotation", "--evidence", "-",
             data=json.dumps(review("plan", subject)))
    accepted("implementation", "start", "rotation")
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(new_raw), encoding="utf-8")
    git("add", ".harness/policy-authority.yaml")
    git("commit", "-qm", "rotate key")
    assessment = {"affected_commitments": ["goal"], "conclusion": "within_approval",
                  "reasons": ["Rotate only the trusted authority."],
                  "references": [".harness/policy-authority.yaml"]}
    accepted("implementation", "record", "rotation", "--assessment", "-",
             data=json.dumps(assessment))
    accepted("done", "rotation")
    code = derive_state(events_path(root))["rotation"].current_code_subject
    accepted("review", "import", "rotation", "--evidence", "-",
             data=json.dumps(review("code", code["subject_id"])))
    accepted("attest", "write", "rotation")
    attestation = harness / "attestations/v3/rotation.jsonl"
    assert attestation.is_file()
    git("add", ".harness/attestations/v3/rotation.jsonl")
    git("commit", "-qm", "retain rotation evidence")
    accepted("attest", "verify", "--base", base, "--head", "HEAD",
             "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
