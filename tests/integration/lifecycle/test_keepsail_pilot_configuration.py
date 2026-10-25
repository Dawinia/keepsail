"""Concrete Keepsail candidate, ordinary delivery, and isolated observed CLI use."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import yaml

from keepsail.core.approval import make_code_subject
from keepsail.core.knowledge import validate_policy, version_record
from keepsail.core.reducer import derive_state
from keepsail.engineering.attestation import parse_name_status, verify_attestations
from tests.integration.lifecycle.test_knowledge_delivery import process
from tests.integration.lifecycle.test_knowledge_policy_bootstrap import BootstrapWorkspace
from tests.integration.lifecycle.test_trusted_verifier_workspace import projection_program
from tests.unit.core.test_knowledge import git

ROOT = Path(__file__).resolve().parents[3]
TARGET = "2026-10-25-knowledge-cli-pilot"


def test_concrete_candidate_delivery_and_observable_process_use(tmp_path):
    policy = validate_policy(
        yaml.safe_load((ROOT / ".harness/knowledge-recognition.yaml").read_text())
    )
    proposal = json.loads(
        (ROOT / "docs/knowledge-pilot/delivery-evidence-boundary-v1.json").read_text(
            encoding="utf-8"
        )
    )
    expected_version = version_record(proposal, policy)["version_digest"]
    owner = json.loads((ROOT / policy["owner_activation"]["source"]).read_text(encoding="utf-8"))
    assert owner["record_id"] == policy["owner_activation"]["id"]
    assert policy["human_issuers"] == ["keepsail-product-owner"]
    assert policy["processes"][0]["issuers"] == policy["human_issuers"]
    assert "merge and actual trusted-base activation" in owner["reserved"]
    assert proposal["selector"] == {"repository_ids": ["Dawinia/keepsail"], "change_ids": [TARGET]}
    w = BootstrapWorkspace(tmp_path)
    w.candidate(policy)
    w.plan()
    w.cli("implementation", "start", "change-a")
    git(tmp_path, "add", ".harness/knowledge-recognition.yaml")
    git(tmp_path, "commit", "-qm", "concrete candidate without activation")
    log = tmp_path / ".harness/events.jsonl"
    state = derive_state(log)["change-a"]
    subject = make_code_subject(
        tmp_path,
        change_id="change-a",
        approval_id=state.effective_approval["approval_id"],
        base="main",
    )
    assessment = {
        "assessment": {
            "approval_id": state.effective_approval["approval_id"],
            "affected_commitments": ["P1"],
            "conclusion": "within_approval",
            "reasons": ["Concrete first policy within fixture plan"],
            "references": [".harness/knowledge-recognition.yaml"],
        },
        "coverage": [{"path": row["path"]} for row in subject["manifest"]],
    }
    w.cli("implementation", "record", "change-a", "--assessment", str(w.write(assessment)))
    shown = w.cli("knowledge", "show")["data"]
    assert (
        shown["coverage"] == "not_recorded"
        and shown["policy_candidate"]["policy_digest"] == policy["policy_digest"]
    )
    w.submit("propose", w.operation(version=proposal), code=2)
    w.cli("done", "change-a")
    assert w.marker.read_text() == "validated candidate"
    state = derive_state(log)["change-a"]
    w.approve("change-a", "code", state.current_code_subject["subject_id"])
    w.cli("attest", "write", "change-a")
    git(tmp_path, "add", ".harness/attestations/change-a.jsonl")
    git(tmp_path, "commit", "-qm", "retain concrete candidate delivery fixture")
    verdict = verify_attestations(
        tmp_path,
        parse_name_status(git(tmp_path, "diff", "--name-status", "main...HEAD")),
        base="main",
        head="HEAD",
    )
    assert verdict.ok, verdict.blockers
    trusted = tmp_path / ".harness-trusted-base"
    base = git(tmp_path, "rev-parse", "main")
    head = git(tmp_path, "rev-parse", "HEAD")
    subprocess.run(["git", "clone", "-q", "--shared", str(tmp_path), str(trusted)], check=True)
    git(trusted, "checkout", "-q", "--detach", base)
    subprocess.run(
        [sys.executable, "-c", projection_program()],
        check=True,
        env={**os.environ, "GITHUB_WORKSPACE": str(tmp_path), "BASE_SHA": base, "HEAD_SHA": head},
    )
    diff = parse_name_status(git(tmp_path, "diff", "--name-status", f"{base}...{head}"))
    assert verify_attestations(trusted, diff, base=base, head=head).ok
    evidence = trusted / ".harness/attestations/change-a.jsonl"
    original = evidence.read_bytes()
    evidence.write_bytes(b"not an attestation\n")
    assert not verify_attestations(trusted, diff, base=base, head=head).ok
    evidence.write_bytes(original)
    evidence.unlink()
    assert not verify_attestations(trusted, diff, base=base, head=head).ok
    # Owner-controlled baseline advancement is simulated only in this isolated Git fixture.
    git(tmp_path, "branch", "-f", "main", "HEAD")
    w.cli("change", "start", TARGET, "--framework", "plain")
    w.plan(TARGET)

    def deliver(identifier):
        w.counter += 1
        result = process(
            w,
            "knowledge",
            "deliver",
            identifier,
            "--operation-id",
            f"concrete-delivery-{w.counter}",
            "--expected-revision",
            w.revision(),
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)["data"]

    deliver(TARGET)
    w.cli("implementation", "start", TARGET)

    def operation(**payload):
        return w.operation(change_id=TARGET, **payload)

    def recognize(version):
        digest = w.submit("propose", operation(version=version))["version_digest"]
        w.counter += 1
        evidence = {
            "schema_version": "knowledge-evidence/v1",
            "evidence_id": f"concrete-fixture-{w.counter}",
            "kind": "recognition",
            "subject_id": digest,
            "decision": "recognize",
            "process": {"id": "keepsail-owner-knowledge", "version": "1"},
            "issuer": "keepsail-product-owner",
            "authorization_effect": "unchanged",
            "original_evidence": {
                "source": "isolated fixture only, no real owner recognition",
                "decision": "recognize",
            },
            "provenance": {"policy_digest": policy["policy_digest"]},
        }
        w.submit("import", operation(evidence=evidence))
        return digest

    first = recognize(proposal)
    assert first == expected_version
    delivery = deliver(TARGET)
    assert delivery["constraints"][0]["version_digest"] == first
    assert delivery["constraints"][0]["body"] == proposal["body"]
    assert "recipient-acquisition" in delivery["missing_observations"]
    assert deliver("change-a")["constraints"] == []
    w.submit(
        "record",
        operation(
            record={
                "kind": "statement",
                "decision": "adopt",
                "delivery_id": delivery["delivery_id"],
                "version_digest": first,
                "reason": "isolated declaration, not compliance evidence",
            }
        ),
    )
    w.submit(
        "record",
        operation(
            record={
                "kind": "acquisition",
                "producer": "keepsail-cli-observer",
                "delivery_id": delivery["delivery_id"],
                "version_digest": first,
                "returned_content_digest": sha256(proposal["body"].encode()).hexdigest(),
                "original_receipt": {
                    "source": "captured real CLI subprocess stdout in isolated test",
                    "body": delivery["constraints"][0]["body"],
                },
            }
        ),
    )
    before = log.read_bytes()
    resumed = process(w, "change", "resume", TARGET)
    assert resumed.returncode == 0, resumed.stderr
    recovered = json.loads(resumed.stdout)["data"]["knowledge"]
    assert log.read_bytes() == before
    assert any(row["status"] == "observed" for row in recovered["acquisition_coverage"])
    assert "compliance" in recovered["missing_observations"]
    second = recognize(
        {
            **proposal,
            "body": proposal["body"] + " Receipt proves return, not understanding.",
            "previous_version": first,
        }
    )
    w.cli("knowledge", "check", TARGET, code=2)
    recovered = json.loads(process(w, "change", "resume", TARGET).stdout)["data"]["knowledge"]
    assert recovered["constraints"][0]["version_digest"] == second
    assert any(row["version_digest"] == first for row in recovered["supply_history"])
    assert recovered["impacts"][0]["status"] == "pending"
    impact = recovered["impacts"][0]
    subject = {
        k: v
        for k, v in impact.items()
        if k not in {"impact_id", "status", "disposition_id", "disposition"}
    }
    w.submit(
        "import",
        operation(
            evidence={
                "schema_version": "knowledge-evidence/v1",
                "evidence_id": "fixture-continue-v1",
                "kind": "disposition",
                "subject_id": impact["impact_id"],
                "decision": "continue",
                "impact": subject,
                "use_version": first,
                "process": {"id": "keepsail-owner-knowledge", "version": "1"},
                "issuer": "keepsail-product-owner",
                "authorization_effect": "unchanged",
                "original_evidence": {
                    "source": "isolated owner fixture only",
                    "decision": "continue",
                },
                "provenance": {"policy_digest": policy["policy_digest"]},
            }
        ),
    )
    deliver(TARGET)
    view = w.cli("knowledge", "check", TARGET)["data"]
    assert view["constraints"][0]["version_digest"] == first
    assert view["impacts"][0]["status"] == "resolved"
