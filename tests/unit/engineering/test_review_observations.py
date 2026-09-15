"""Mixed-contract reports count observations, never invent executions or costs."""

import json
from pathlib import Path

from super_harness.cli.report import _render_brief, _render_human
from super_harness.engineering.value_report import build_value_report


def event(eid, kind, payload, *, day="15", change="c"):
    return {
        "event_id": eid,
        "type": kind,
        "payload": payload,
        "change_id": change,
        "timestamp": f"2026-09-{day}T12:00:00Z",
        "framework": "plain",
        "actor": {"type": "agent", "identifier": "review"},
    }


def report(tmp_path: Path, events, **window):
    path = tmp_path / "events.jsonl"
    raw = "\n".join(json.dumps(e) for e in events).encode()
    path.write_bytes(raw)
    result = build_value_report(
        path, workspace_root=tmp_path, since=window.get("since"), until=window.get("until")
    )
    assert path.read_bytes() == raw
    return result


def external(eid="evidence-1", decision="approve", **extra):
    return {
        "evidence": {
            "evidence_id": eid,
            "kind": "code",
            "decision": decision,
            "subject_id": "code:exact",
            "issuer": "codex-subagent",
            "process": {"id": "codex-subagent-review", "version": "v1"},
            "original_evidence": {"findings": [{"id": "opaque"}], "usage": {"total_tokens": 999}},
            **extra,
        }
    }


def test_failed_issued_run_without_result_has_unknown_cost(tmp_path):
    r = report(
        tmp_path,
        [
            event(
                "start",
                "review_round_started",
                {"round_id": "r", "runs": [{"run_id": "run", "source": "claude"}]},
            ),
            event(
                "fail",
                "review_run_failed",
                {"round_id": "r", "run_id": "run", "source": "claude", "reason": "403"},
            ),
            event("close", "review_round_closed", {"round_id": "r", "outcome": "execution_failed"}),
        ],
    )
    assert (r.review_rounds_started, r.review_attempts_started, r.review_execution_failures) == (
        1,
        1,
        1,
    )
    assert r.review_rounds_execution_failed == 1
    assert r.review_results_imported == r.rejected_rounds == 0
    assert r.review_records_total == r.review_runs_total == 1
    assert r.review_tokens is r.review_reported_cost_usd is r.review_invocations_total is None
    assert "review tokens: unknown" in _render_human(r)
    assert "0/1 observable records" in _render_human(r)
    assert "unknown recorded review tokens" in _render_brief(r)


def test_external_only_conclusions_are_not_runs_or_structured_findings(tmp_path):
    evidence = external()
    r = report(
        tmp_path,
        [
            event("e", "review_evidence_imported", evidence),
            event("mirror", "code_review_passed", evidence),
        ],
    )
    assert r.external_conclusions_imported == r.external_approvals == 1
    assert r.review_runs_total == r.review_attempts_started == r.review_results_imported == 0
    assert r.review_tokens is None
    assert r.findings_open_undisposed == 0
    row = r.cost_breakdown[0]
    assert (row.source, row.issuer, row.subject_id) == (
        "codex-subagent-review",
        "codex-subagent",
        "code:exact",
    )
    assert "external conclusion:" in _render_human(r)
    assert "invocations: unknown" in _render_human(r)


def test_mixed_replay_imports_skips_and_usage_are_distinct(tmp_path):
    old = event(
        "old",
        "review_result_imported",
        {
            "run_id": "run",
            "source": "claude",
            "receipt": {"usage": {"input_tokens": 10}, "reported_cost_usd": 0},
        },
    )
    new = event("new", "review_evidence_imported", external(usage={"total_tokens": 20}))
    reject = event(
        "reject",
        "review_evidence_imported",
        external("evidence-2", "reject", supersedes="evidence-1"),
    )
    r = report(
        tmp_path,
        [
            event("start", "review_round_started", {"round_id": "r", "runs": [{"run_id": "run"}]}),
            event(
                "fail",
                "review_run_failed",
                {"run_id": "run", "receipt": {"usage": {"input_tokens": 10}}},
            ),
            old,
            old,
            {**old, "event_id": "repeat-old"},
            new,
            {**new, "event_id": "repeat-new"},
            reject,
            event("mirror", "code_review_failed", reject["payload"]),
            event("skip", "plan_approved", {"skipped": True}),
            event("auth1", "review_round_authorized", {"reason": "same"}),
            event("auth2", "review_round_authorized", {"reason": "same"}),
            event("auth2", "review_round_authorized", {"reason": "same"}),
            event("verify", "verification_failed", {"findings": ["not-an-independent-defect"]}),
        ],
    )
    assert r.review_records_total == 3
    assert r.cost_breakdown[0].source == "claude"
    assert (r.review_tokens, r.review_records_with_usage, r.review_component_subtotals) == (
        30,
        2,
        1,
    )
    assert r.review_reported_cost_usd == 0
    assert r.review_records_with_reported_cost == 1
    assert (
        r.external_approvals,
        r.external_rejections,
        r.review_skips,
        r.authorizations_total,
    ) == (1, 1, 1, 2)
    assert r.review_results_imported == r.review_execution_failures == r.review_runs_total == 1
    assert r.findings_resolved == r.findings_open_undisposed == 0


def test_window_counts_failures_and_imports_when_observed_not_replays(tmp_path):
    old = event(
        "old",
        "review_result_imported",
        {"run_id": "old", "receipt": {"usage": {"total_tokens": 100}}},
        day="10",
    )
    r = report(
        tmp_path,
        [
            old,
            {**old, "event_id": "replay", "timestamp": "2026-09-15T12:00:00Z"},
            event(
                "start",
                "review_round_started",
                {"round_id": "r", "runs": [{"run_id": "run"}]},
                day="10",
            ),
            event("fail", "review_run_failed", {"run_id": "run"}),
            event("new", "review_evidence_imported", external(usage={"total_tokens": 0})),
        ],
        since="2026-09-15",
    )
    assert r.review_attempts_started == r.review_results_imported == 0
    assert r.review_execution_failures == 1
    assert r.review_tokens == 0
    assert r.review_records_with_usage == 1
    assert r.review_records_total == 2


def test_invalid_usage_is_unknown_and_explicit_zero_is_known(tmp_path):
    r = report(
        tmp_path,
        [
            event(
                str(i),
                "review_evidence_imported",
                external(str(i), usage={"total_tokens": value}, reported_cost_usd=value),
            )
            for i, value in enumerate([-1, True, "0", float("nan"), float("inf"), 0])
        ],
    )
    assert r.review_tokens == r.review_reported_cost_usd == 0
    assert r.review_records_with_usage == r.review_records_with_reported_cost == 1
    assert r.review_records_total == 6
