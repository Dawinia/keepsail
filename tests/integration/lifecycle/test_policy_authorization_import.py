"""Exercise signed authorization import using a real isolated Git baseline."""

import base64
import json
import subprocess
from copy import deepcopy
from hashlib import sha256

import yaml
from click.testing import CliRunner
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from keepsail.cli import main
from keepsail.core.approval import canonical_json, recognition_policy_digest
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state
from keepsail.core.review_verdict import read_change_events


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_import_retains_signed_authorization_without_approving_plan(tmp_path):
    root = tmp_path
    harness = root / ".harness"
    harness.mkdir()
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    authority = {"version": "policy-authority/v1", "repository_id": "owner/project",
                 "target_ref": "refs/heads/main", "enabled": True, "keys": [{
                     "key_id": sha256(public).hexdigest(), "algorithm": "ed25519",
                     "public_key": base64.b64encode(public).decode("ascii"),
                     "purposes": ["policy-transition"],
                 }]}
    (harness / "policy-authority.yaml").write_text(yaml.safe_dump(authority), encoding="utf-8")
    recognition = {"version": "review-recognition/v1", "enabled": True, "process": {
        "id": "old-review", "version": "v1", "kinds": ["plan", "code"],
        "issuers": ["old-reviewer"], "evidence_forms": ["json"]}}
    recognition["process"]["policy_digest"] = recognition_policy_digest(recognition)
    (harness / "review-recognition.yaml").write_text(yaml.safe_dump(recognition), encoding="utf-8")
    (root / "plan.md").write_text("# Change the delivery policy\n", encoding="utf-8")
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "fixture")
    git(root, "add", ".")
    git(root, "commit", "-qm", "trusted old policy and authority")
    base = git(root, "rev-parse", "HEAD")
    git(root, "switch", "-qc", "candidate")
    runner = CliRunner()

    def cli(*args, data=None):
        return runner.invoke(main, ["--workspace", str(root), *args], input=data)

    started = cli("change", "start", "delivery", "--framework", "plain")
    assert started.exit_code == 0, started.output
    ready = cli("plan", "ready", "delivery", "--plan", "plan.md", "--scope", "[plan.md]",
                "--commitment", "goal=Change the delivery policy")
    assert ready.exit_code == 0, ready.output
    subject = derive_state(events_path(root))["delivery"].pending_revision["subject"]["subject_id"]
    record = {"version": "policy-authorization/v1", "repository_id": "owner/project",
              "target_ref": "refs/heads/main", "base_sha": base,
              "predecessor_policy_digest": recognition["process"]["policy_digest"],
              "target_policy_digest": "c" * 64, "change_id": "delivery",
              "plan_subject_id": subject, "kind": "transition", "permitted_paths": [
                  "plan.md", ".harness/review-recognition.yaml"],
              "decision": "approve", "key_id": authority["keys"][0]["key_id"]}
    record["signature"] = base64.b64encode(key.sign(canonical_json(record).encode())).decode()
    command = ("--json", "policy", "authorization", "import", "delivery", "--evidence", "-",
               "--repository-id", "owner/project", "--target-ref", "refs/heads/main")
    imported = cli(*command, data=json.dumps(record))
    assert imported.exit_code == 0, imported.output
    assert json.loads(imported.output)["data"]["authority_effect"] == "unchanged"
    assert derive_state(events_path(root))["delivery"].current_state == "AWAITING_PLAN_REVIEW"
    again = cli(*command, data=json.dumps(record))
    assert again.exit_code == 0 and json.loads(again.output)["data"]["idempotent"] is True
    changed = deepcopy(record)
    changed["target_policy_digest"] = "d" * 64
    rejected = cli(*command, data=json.dumps(changed))
    assert rejected.exit_code == 2
    assert len([e for e in read_change_events(events_path(root), "delivery")
                if e.type == "policy_authorization_imported"]) == 1
