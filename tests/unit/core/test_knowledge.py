"""Behavioral tests of the shared knowledge seam, using owner-authorized fixtures."""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from keepsail.cli import main
from keepsail.core.approval import digest_record, recognition_policy_digest
from keepsail.core.knowledge import (
    PROTOCOL,
    KnowledgeError,
    load_ledger,
    load_policy,
    policy_digest,
    report,
    validate_policy,
    version_record,
)
from keepsail.core.reducer import derive_state


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def policy() -> dict:
    result = {
        "version": "knowledge-recognition/v1",
        "enabled": True,
        "product_id": "test-product",
        "repository_id": "test-repo",
        "minimum_reader": PROTOCOL,
        "owner_activation": {
            "id": "fixture-only",
            "source": "test",
            "by": "owner",
            "decision": "activate",
        },
        "human_issuers": ["owner"],
        "observation_issuers": ["test-observer"],
        "processes": [
            {
                "id": "test-process",
                "version": "1",
                "issuers": ["owner", "reviewer"],
                "kinds": ["recognition", "applicability", "disposition"],
            }
        ],
    }
    result["policy_digest"] = policy_digest(result)
    return result


def version(
    *,
    body: str = "持久化统一 PostgreSQL",
    previous: str | None = None,
    selector: dict | None = None,
) -> dict:
    return {
        "schema_version": "knowledge-version/v1",
        "product_id": "test-product",
        "knowledge_id": "database-choice",
        "body": body,
        "rationale": "operations",
        "sources": [{"origin": "owner", "content": "Use PostgreSQL"}],
        "authority": "constraint",
        "previous_version": previous,
        "selector": {"global": True} if selector is None else selector,
    }


class Workspace:
    def __init__(self, root: Path):
        self.root = root
        self.runner = CliRunner()
        self.counter = 0
        (root / ".harness").mkdir()
        (root / ".harness/knowledge-recognition.yaml").write_text(
            yaml.safe_dump(policy()), encoding="utf-8"
        )
        review = {
            "version": "review-recognition/v1",
            "enabled": True,
            "process": {
                "id": "owner-review",
                "version": "1",
                "kinds": ["plan", "code"],
                "issuers": ["owner"],
                "evidence_forms": ["json"],
            },
        }
        review["process"]["policy_digest"] = recognition_policy_digest(review)
        self.review = review
        (root / ".harness/review-recognition.yaml").write_text(
            yaml.safe_dump(review), encoding="utf-8"
        )
        (root / "plan.md").write_text("# Persist with PostgreSQL\n", encoding="utf-8")
        (root / ".gitignore").write_text(
            ".harness/events.jsonl\n.harness/state.yaml\n.harness/.*.lock\ninput*.json\n",
            encoding="utf-8",
        )
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Test")
        git(root, "add", ".")
        git(root, "commit", "-qm", "owner activation fixture")
        git(root, "switch", "-qc", "candidate")
        self.cli("change", "start", "change-a", "--framework", "plain")
        self.cli(
            "plan",
            "ready",
            "change-a",
            "--plan",
            "plan.md",
            "--scope",
            "[plan.md, src/db]",
            "--commitment",
            "db=Use PostgreSQL",
        )
        state = derive_state(root / ".harness/events.jsonl")["change-a"]
        evidence = {
            "version": "review-evidence/v1",
            "evidence_id": "plan-1",
            "kind": "plan",
            "subject_id": state.pending_revision["subject"]["subject_id"],
            "decision": "approve",
            "process": {"id": "owner-review", "version": "1"},
            "issuer": "owner",
            "original_evidence": {"decision": "approve"},
            "provenance": {"policy_digest": review["process"]["policy_digest"]},
        }
        p = self.write(evidence)
        self.cli("review", "import", "change-a", "--evidence", str(p))
        self.deliver()
        self.cli("implementation", "start", "change-a")

    def write(self, data: dict) -> Path:
        self.counter += 1
        p = self.root / f"input{self.counter}.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return p

    def cli(self, *args: str, code: int = 0) -> dict:
        result = self.runner.invoke(main, ["--workspace", str(self.root), "--json", *args])
        assert result.exit_code == code, (result.output, result.exception)
        return json.loads(result.stdout) if result.stdout.startswith("{") else {}

    def revision(self) -> str:
        return load_ledger(self.root / ".harness/events.jsonl", load_policy(self.root))[1]

    def operation(self, **payload) -> dict:
        self.counter += 1
        return {
            "schema_version": PROTOCOL,
            "operation_id": f"op-{self.counter}",
            "expected_revision": self.revision(),
            "change_id": "change-a",
            **payload,
        }

    def submit(self, command: str, payload: dict, *, code: int = 0) -> dict:
        arg = "--evidence" if command == "import" else "--record"
        return self.cli("knowledge", command, arg, str(self.write(payload)), code=code)["data"]

    def deliver(self) -> dict:
        self.counter += 1
        return self.cli(
            "knowledge",
            "deliver",
            "change-a",
            "--operation-id",
            f"delivery-{self.counter}",
            "--expected-revision",
            self.revision(),
        )["data"]

    def recognize(self, v: dict, *, decision: str = "recognize") -> str:
        digest = self.submit("propose", self.operation(version=v))["version_digest"]
        self.submit(
            "import", self.operation(evidence=self.evidence("recognition", digest, decision))
        )
        return digest

    def evidence(self, kind: str, subject: str, decision: str, **extra) -> dict:
        self.counter += 1
        return {
            "schema_version": "knowledge-evidence/v1",
            "evidence_id": f"e-{self.counter}",
            "kind": kind,
            "subject_id": subject,
            "decision": decision,
            "process": {"id": "test-process", "version": "1"},
            "issuer": "owner",
            "authorization_effect": "unchanged",
            "original_evidence": {"decision": decision},
            "provenance": {"policy_digest": policy()["policy_digest"]},
            **extra,
        }


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path)


def test_candidate_has_no_authority_and_rejection_cannot_activate(workspace: Workspace):
    w = workspace
    digest = w.recognize(version(), decision="reject")
    view = report(w.root, "change-a")
    assert view["constraints"] == []
    assert w.cli("knowledge", "show")["data"]["versions"][0]["state"] == "candidate"
    assert digest


def test_v1_v2_retention_resume_and_recognized_continuation(workspace: Workspace):
    w = workspace
    first = w.recognize(version())
    delivery = w.deliver()
    assert delivery["constraints"][0]["version_digest"] == first
    assert delivery["supply_status"] == "prepared"
    assert "recipient-acquisition" in delivery["missing_observations"]
    second = w.recognize(version(body="PostgreSQL; isolated tests may use SQLite", previous=first))
    view = report(w.root, "change-a")
    assert view["supply_history"][-1]["body"] == "持久化统一 PostgreSQL"
    assert view["constraints"][0]["version_digest"] == second
    impact = view["impacts"][0]
    w.cli("knowledge", "check", "change-a", code=2)
    frozen = {
        k: v
        for k, v in impact.items()
        if k not in {"impact_id", "status", "disposition_id", "disposition"}
    }
    evidence = w.evidence(
        "disposition", impact["impact_id"], "continue", impact=frozen, use_version=first
    )
    w.submit("import", w.operation(evidence=evidence))
    w.deliver()
    continued = w.cli("knowledge", "check", "change-a")["data"]
    assert continued["constraints"][0]["version_digest"] == first
    resumed = w.cli("change", "resume", "change-a")["data"]["knowledge"]
    assert resumed["impacts"][0]["status"] == "resolved"
    assert resumed["effective_approval"]["approval_id"]


@pytest.mark.parametrize(
    "selector,match",
    [
        ({"change_ids": ["other"]}, "non_matching"),
        ({"paths": ["src/db"]}, "matched"),
        ({"paths": ["src/db2"]}, "non_matching"),
    ],
)
def test_explicit_matching_is_segment_aware(workspace: Workspace, selector: dict, match: str):
    w = workspace
    w.recognize(version(selector=selector))
    delivery = w.deliver()
    assert delivery["evaluated"][0]["match"] == match
    assert bool(delivery["constraints"]) == (match == "matched")


def test_challenge_does_not_release_constraint_and_independent_action_can_continue(workspace):
    w = workspace
    v = w.recognize(version(selector={"paths": ["src/db"]}))
    d = w.deliver()
    w.submit(
        "record",
        w.operation(
            record={
                "kind": "challenge",
                "decision": "challenge",
                "delivery_id": d["delivery_id"],
                "version_digest": v,
                "reason": "counterevidence",
                "dependent_paths": ["src/db"],
            }
        ),
    )
    assert report(w.root, "change-a")["constraints"][0]["version_digest"] == v
    w.cli("knowledge", "check", "change-a", code=2)
    w.cli("knowledge", "check", "change-a", "--paths", "src/db/model.py", code=2)
    w.cli("knowledge", "check", "change-a", "--paths", "docs/usage.md")


@pytest.mark.parametrize("mutation", ["empty", "failure", "issuer", "policy", "subject"])
def test_invalid_conclusions_leave_log_unchanged(workspace, mutation):
    w = workspace
    v = w.submit("propose", w.operation(version=version()))["version_digest"]
    e = w.evidence("recognition", v, "recognize")
    if mutation == "empty":
        e["original_evidence"] = None
    elif mutation == "failure":
        e["decision"] = "failed"
    elif mutation == "issuer":
        e["issuer"] = "not-owner"
    elif mutation == "policy":
        e["provenance"]["policy_digest"] = "wrong"
    else:
        e["subject_id"] = "missing"
    data = w.operation(evidence=e)
    before = (w.root / ".harness/events.jsonl").read_bytes()
    w.submit("import", data, code=2)
    assert before == (w.root / ".harness/events.jsonl").read_bytes()


def test_operation_replay_and_conflicts(workspace):
    w = workspace
    data = w.operation(version=version())
    path = w.write(data)
    first = w.cli("knowledge", "propose", "--record", str(path))["data"]
    before = (w.root / ".harness/events.jsonl").read_bytes()
    second = w.cli("knowledge", "propose", "--record", str(path))["data"]
    assert first["version_digest"] == second["version_digest"]
    assert second["idempotent_replay"] is True
    assert before == (w.root / ".harness/events.jsonl").read_bytes()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    same = w.cli("knowledge", "propose", "--record", str(path))["data"]
    assert same["idempotent_replay"] is True
    assert before == (w.root / ".harness/events.jsonl").read_bytes()
    data["version"]["body"] = "modified"
    w.submit("propose", data, code=5)
    stale = w.operation(version=version(body="other"))
    stale["expected_revision"] = "stale"
    w.submit("propose", stale, code=5)


def test_corruption_is_not_empty_knowledge(workspace):
    w = workspace
    w.recognize(version())
    log = w.root / ".harness/events.jsonl"
    with log.open("ab") as handle:
        handle.write(b'{"type":"knowledge_imported"')
    w.cli("knowledge", "show", code=2)

    w.cli("change", "resume", "change-a", code=2)


def test_policy_cannot_be_deleted_or_replaced_by_candidate(workspace):
    w = workspace
    p = w.root / ".harness/knowledge-recognition.yaml"
    old = p.read_bytes()
    p.unlink()
    w.cli("knowledge", "show", code=3)
    p.write_bytes(old)
    new = deepcopy(policy())
    new["human_issuers"].append("agent")
    new["policy_digest"] = policy_digest(new)
    p.write_text(yaml.safe_dump(new), encoding="utf-8")
    w.cli("knowledge", "show", code=2)
    p.write_text(yaml.safe_dump({"enabled": True}), encoding="utf-8")
    w.cli("knowledge", "show", code=3)
    w.cli("change", "resume", "change-a", code=3)


def test_version_digest_binds_authority_and_scope():
    p = policy()
    first = version_record(version(), p)
    guidance = version()
    guidance["authority"] = "guidance"
    assert first["version_digest"] != version_record(guidance, p)["version_digest"]
    assert first["version_digest"] == digest_record(version())
    with pytest.raises(KnowledgeError):
        version_record(version(selector={}), p)


def test_acquisition_statement_and_candidate_are_separate_facts(workspace):
    from hashlib import sha256

    w = workspace
    v = w.recognize(version())
    d = w.deliver()
    original = report(w.root, "change-a")["basis_digest"]
    w.submit("record", w.operation(record={"kind": "emitted", "delivery_id": d["delivery_id"]}))
    output = report(w.root, "change-a")
    assert output["statements"][-1]["category"] == "self-reported-output"
    assert output["observations"] == []
    w.submit(
        "record",
        w.operation(
            record={
                "kind": "statement",
                "decision": "adopt",
                "delivery_id": d["delivery_id"],
                "version_digest": v,
                "reason": "will follow it",
            }
        ),
    )
    assert "recipient-acquisition" in report(w.root, "change-a")["missing_observations"]
    w.submit(
        "record",
        w.operation(
            record={
                "kind": "acquisition",
                "producer": "test-observer",
                "delivery_id": d["delivery_id"],
                "version_digest": v,
                "returned_content_digest": sha256(version()["body"].encode()).hexdigest(),
                "original_receipt": {"returned": version()["body"]},
            }
        ),
    )
    view = report(w.root, "change-a")
    assert view["acquisition_coverage"][-1]["status"] == "observed"
    assert "compliance" in view["missing_observations"]
    w.submit("propose", w.operation(version=version(body="unrecognized change", previous=v)))
    assert report(w.root, "change-a")["basis_digest"] == original


def test_disposition_cannot_promote_a_candidate_or_claim_verified_execution(workspace):
    w = workspace
    v1 = w.recognize(version())
    w.deliver()
    v2 = w.recognize(version(body="PostgreSQL 17+", previous=v1))
    v3 = w.submit("propose", w.operation(version=version(body="SQLite", previous=v2)))[
        "version_digest"
    ]
    impact = report(w.root, "change-a")["impacts"][0]
    raw = {
        k: v
        for k, v in impact.items()
        if k not in {"impact_id", "status", "disposition_id", "disposition"}
    }
    bad = w.evidence("disposition", impact["impact_id"], "continue", impact=raw, use_version=v3)
    w.submit("import", w.operation(evidence=bad), code=2)
    e = w.evidence(
        "disposition",
        impact["impact_id"],
        "adjust",
        impact=raw,
        use_version=v2,
        obligations=["adjust database"],
    )
    w.submit("import", w.operation(evidence=e))
    w.submit(
        "record",
        w.operation(
            record={
                "kind": "execution",
                "outcome": "verified",
                "disposition_id": e["evidence_id"],
                "evidence": "agent says done",
                "fulfilled_obligations": ["adjust database"],
                "subject_id": "unverified-code",
            }
        ),
        code=2,
    )


def test_delivery_replay_is_retained_but_staleness_is_visible(workspace):
    w = workspace
    v1 = w.recognize(version())
    revision = w.revision()
    first = w.cli(
        "knowledge",
        "deliver",
        "change-a",
        "--operation-id",
        "fixed-delivery",
        "--expected-revision",
        revision,
    )["data"]
    w.recognize(version(body="PostgreSQL 17+", previous=v1))
    replay = w.cli(
        "knowledge",
        "deliver",
        "change-a",
        "--operation-id",
        "fixed-delivery",
        "--expected-revision",
        revision,
    )["data"]
    assert replay["stale"] is True
    assert replay["constraints"] == first["constraints"]


def test_normal_writer_cannot_skip_knowledge_validation(workspace):
    from keepsail.core.events import Actor, Event
    from keepsail.core.writer import EmitPreconditionError, EventWriter

    w = workspace
    with pytest.raises(EmitPreconditionError, match="skip_validation"):
        EventWriter(w.root / ".harness/events.jsonl").emit(
            Event(
                event_id="skip-test",
                type="knowledge_imported",
                change_id="change-a",
                timestamp="",
                actor=Actor(type="agent", identifier="test"),
                framework="plain",
                payload={},
            ),
            skip_validation=True,
        )


def test_unknown_policy_requirements_cannot_be_silently_ignored():
    p = policy()
    p["require_human_confirmation_every_time"] = True
    p["policy_digest"] = policy_digest(p)
    with pytest.raises(KnowledgeError, match="unsupported knowledge policy requirement"):
        validate_policy(p)


def test_unknown_guidance_does_not_block_independent_work(workspace):
    w = workspace
    v = version(selector={"paths": ["src/another"]})
    v["authority"] = "guidance"
    w.recognize(v)
    w.cli("change", "start", "change-b", "--framework", "plain")
    w.cli("knowledge", "check", "change-b", "--paths", "docs/example.md")


@pytest.mark.parametrize(
    "authority,authorized,code",
    [("constraint", False, 2), ("constraint", True, 0), ("guidance", False, 0)],
)
def test_constraint_retirement_requires_owner_authorization(workspace, authority, authorized, code):
    w = workspace
    v = version()
    v["authority"] = authority
    digest = w.recognize(v)
    e = w.evidence("recognition", digest, "retire", issuer="reviewer")
    if authorized:
        e.update(
            issuer="owner",
            authorization_effect="requires-human-authorization",
            human_authorization={"source": "owner decision to retire this constraint"},
        )
    before = (w.root / ".harness/events.jsonl").read_bytes()
    w.submit("import", w.operation(evidence=e), code=code)
    if code:
        assert (w.root / ".harness/events.jsonl").read_bytes() == before
    else:
        assert w.cli("knowledge", "show")["data"]["versions"][0]["state"] == "retired"


def test_impact_approval_epoch_ignores_preapproval_delivery_and_tracks_later_triggers(workspace):
    from keepsail.core.events import Actor, Event
    from keepsail.core.knowledge import validate_event

    w = workspace
    log = w.root / ".harness/events.jsonl"
    w.cli("change", "start", "change-b", "--framework", "plain")

    def deliver_b(op):
        w.cli(
            "knowledge",
            "deliver",
            "change-b",
            "--operation-id",
            op,
            "--expected-revision",
            w.revision(),
        )

    def approve_b(eid):
        subject = derive_state(log)["change-b"].pending_revision["subject"]["subject_id"]
        e = {
            "version": "review-evidence/v1",
            "evidence_id": eid,
            "kind": "plan",
            "subject_id": subject,
            "decision": "approve",
            "issuer": "owner",
            "process": {"id": "owner-review", "version": "1"},
            "original_evidence": {"decision": "approve", "source": "test fixture"},
            "provenance": {"policy_digest": w.review["process"]["policy_digest"]},
        }
        w.cli("review", "import", "change-b", "--evidence", str(w.write(e)))
        return derive_state(log)["change-b"].effective_approval["approval_id"]

    deliver_b("empty-before-approval")
    w.cli(
        "plan",
        "ready",
        "change-b",
        "--plan",
        "plan.md",
        "--scope",
        "[plan.md]",
        "--commitment",
        "db=Use PostgreSQL",
    )
    initial = approve_b("plan-b-initial")
    first = w.recognize(version())
    deliver_b("v1-b")
    w.cli("implementation", "start", "change-b")
    previous = first
    current_approval = initial
    for epoch in (2, 3):
        new = w.recognize(version(body=f"PostgreSQL rule {epoch}", previous=previous))
        impact = next(
            i for i in report(w.root, "change-b")["impacts"] if i["old_version"] == previous
        )
        assert impact["approval_id"] == current_approval
        for linked in report(w.root, "change-b")["impacts"]:
            raw = {
                k: v
                for k, v in linked.items()
                if k not in {"impact_id", "status", "disposition_id", "disposition"}
            }
            e = w.evidence(
                "disposition",
                linked["impact_id"],
                "reapprove",
                impact=raw,
                use_version=new,
                obligations=["approve revised database constraint"],
            )
            w.submit("import", w.operation(evidence=e))
        deliver_b(f"pending-epoch-{epoch}")
        event = Event(
            event_id=f"complete-{epoch}",
            type="implementation_complete",
            change_id="change-b",
            timestamp="",
            actor=Actor(type="agent", identifier="test"),
            framework="plain",
            payload={},
        )
        with pytest.raises(KnowledgeError, match="unresolved impact"):
            validate_event(log, event)
        w.cli(
            "plan",
            "redeclare",
            "change-b",
            "--plan",
            "plan.md",
            "--commitment",
            f"db=Use database rule {epoch}",
        )
        current_approval = approve_b(f"plan-b-epoch-{epoch}")
        retained = next(
            i for i in report(w.root, "change-b")["impacts"] if i["old_version"] == previous
        )
        assert retained["impact_id"] == impact["impact_id"]
        assert retained["approval_id"] != current_approval
        deliver_b(f"new-approval-{epoch}")
        validate_event(log, event)
        previous = new
