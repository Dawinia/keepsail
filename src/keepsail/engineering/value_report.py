"""Roll up the existing event stream into an honest value summary (Stage 1).

Zero new event types: this module READS events.jsonl (plus the Stage-2 gate-block
telemetry log, `.harness/gate-blocks.jsonl`, for the ``edits_blocked`` floor) and
reuses core primitives. Placed in ``engineering/`` (not ``core/``) because it
composes review + decision loaders; ``engineering`` may import ``core``, preserving
d-keepsail-core-is-base.

Observation semantics are documented in docs/reporting.md. This is not a total
value score: historical structured finding dispositions, gate telemetry and
recorded review observations have different coverage and evidence limits.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from keepsail.core.events import Event, EventSchemaError, effective_event_lines, parse_event_line
from keepsail.core.gate_blocks import GateBlockRecord, read_blocks
from keepsail.core.parse_ts import parse_ts
from keepsail.core.paths import gate_blocks_path

# A bare `YYYY-MM-DD` upper bound means "through the end of that day" — parse_ts
# gives midnight, which would silently drop the rest of the day (CODX-008).
_DATE_ONLY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class ValueReport:
    since: str | None
    until: str | None
    changes_touched: int
    # Band 1 - realized effect
    findings_resolved: int
    findings_open_undisposed: int
    undisclosed_bypasses: int
    edits_blocked: int
    # Band 2 - cost
    review_tokens: int | None
    review_runs_total: int
    review_runs_with_usage: int
    findings_wontfix: int
    rejected_rounds: int
    # footnote context
    armed_decisions: int
    # attribution — where the review tokens went (Step 1 of risk-tiered review)
    cost_breakdown: tuple[CostBreakdownRow, ...] = ()
    # Producer-stated cost. `None` means no run reported one — never 0.0, which would
    # read as "this was free". The harness never prices tokens itself.
    review_reported_cost_usd: float | None = None
    review_runs_with_reported_cost: int = 0
    # Distinct rounds the budget refused, NOT blocks: one refused round can be
    # re-attempted, and an agent that retries — the behaviour the block forbids and
    # cannot prevent, which is why the event exists at all — must not be able to
    # inflate the figure the cut adds to make cost trustworthy.
    # Surfaced whether or not the agent relayed the block — this repo's own research
    # concluded that specifications read into context and not followed is the actual
    # widespread failure, so the brake records itself.
    review_budget_hits: int = 0
    # Distinct recorded authorization events are history, not verified human acts.
    authorizations: tuple[AuthorizationRecord, ...] = ()
    authorizations_total: int = 0
    # Reopens, one record each, for the same reason authorizations are counted:
    # `implementation reopen` voids a code review the change already passed, nothing
    # verifies its `--reason`, and a count a human can falsify from memory is the only
    # check there is. Not deduped, for the reason `derive_authorizations` gives.
    reopens: tuple[ReopenRecord, ...] = ()
    reopens_total: int = 0
    # Coverage counts observable legacy run / external evidence records, not calls.
    review_records_total: int = 0
    review_records_with_usage: int = 0
    review_records_with_reported_cost: int = 0
    review_component_subtotals: int = 0
    review_attempts_started: int = 0
    review_execution_failures: int = 0
    review_results_imported: int = 0
    review_rounds_started: int = 0
    review_rounds_execution_failed: int = 0
    external_conclusions_imported: int = 0
    external_approvals: int = 0
    external_rejections: int = 0
    review_skips: int = 0
    # Neither historical issuance nor external evidence proves invocation count.
    review_invocations_total: int | None = None
    findings_scope: str = "historical structured code-review IDs/dispositions only"


@dataclass(frozen=True)
class CostBreakdownRow:
    """One observable legacy run or external evidence record in the window.

    External prose has no structured findings metric. None means usage unknown.
    """

    role: str
    source: str
    change_id: str
    round: int
    round_id: str
    tokens: int | None
    findings_raised: int
    outcome: str
    record_type: str = "legacy_run"
    record_id: str = ""
    started: bool = False
    failed: bool = False
    imported: bool = False
    reported_cost_usd: float | None = None
    component_subtotal: bool = False
    subject_id: str = ""
    issuer: str = ""
    process_version: str = ""
    historical_only: bool = False
    supersedes: str = ""


@dataclass(frozen=True)
class AuthorizationRecord:
    """One `review_round_authorized` event, as recorded.

    ``reason`` is ``None`` when the payload carried none — never ``""``, which would
    render as an approval with no comment rather than as an absent one. It is the
    human's own words and nothing validates them; the rendering must say so.
    """

    change_id: str
    reviewer: str
    reason: str | None
    timestamp: str
    actor: str


@dataclass(frozen=True)
class ReopenRecord:
    """One `implementation_invalidated` event, as recorded.

    Same shape and same contract as `AuthorizationRecord` minus the role, which a
    reopen does not have: it returns the whole change to editing, not one reviewer's
    round. `reason` is `None` when the payload carried none — `implementation reopen`
    requires the flag, so that only happens for a hand-written or imported event, and
    it must render as absent rather than as an empty explanation.
    """

    change_id: str
    reason: str | None
    timestamp: str
    actor: str


def _read_all_events(events_file: Path) -> list[Event]:
    """Parse every event tolerantly (skip malformed), across all changes, in
    append (file) order — order is load-bearing for bypass-disclosure causality."""
    if not events_file.exists():
        return []
    out: list[Event] = []
    seen: set[tuple[str, ...]] = set()
    for line in effective_event_lines(events_file.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            event = parse_event_line(line)
        except EventSchemaError:
            continue
        keys = [(event.change_id, "event", event.event_id)]
        payload = event.payload or {}
        identity = None
        if event.type in {"review_result_imported", "review_run_failed"}:
            receipt = payload.get("receipt")
            identity = payload.get("run_id") or (
                receipt.get("run_id") if isinstance(receipt, dict) else None
            )
        elif event.type == "review_evidence_imported":
            evidence = payload.get("evidence")
            identity = evidence.get("evidence_id") if isinstance(evidence, dict) else None
        elif event.type in {"review_round_started", "review_round_closed"}:
            identity = payload.get("round_id")
            if event.type == "review_round_closed" and isinstance(identity, str):
                identity += ":" + str(payload.get("outcome"))
        if isinstance(identity, str) and identity:
            keys.append((event.change_id, event.type, identity))
        if any(key in seen for key in keys):
            continue
        seen.update(keys)
        out.append(event)
    return out


def _in_window(ev: Event, lo: datetime | None, hi: datetime | None) -> bool:
    """True if the event's timestamp is within [lo, hi]. With no bounds, always
    true. With a bound set, an unparseable timestamp cannot be placed -> excluded.
    """
    if lo is None and hi is None:
        return True
    ts = parse_ts(ev.timestamp)
    if ts is None:
        return False
    if lo is not None and ts < lo:
        return False
    if hi is not None and ts > hi:
        return False
    return True


def _is_code_verdict(ev: Event) -> bool:
    payload = ev.payload or {}
    return ev.type == "code_review_failed" or (
        ev.type == "review_result_imported" and payload.get("reviewer") == "code-reviewer"
    )


def _dispositions(events: list[Event]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """((change_id, id) resolved, (change_id, id) wontfix) disposed by these events.

    Finding identity is (change_id, id), NOT the bare id: the same short id (e.g.
    legacy ``code_review_failed`` ids) recurs across changes, so a global id set
    would let one change's disposition clear another change's finding (CODX-007).
    ``verdict`` is guarded as a dict so a malformed event can never crash the
    report (mirrors ``_review_cost``'s receipt guard; the module never raises).
    """
    resolved: set[tuple[str, str]] = set()
    wontfix: set[tuple[str, str]] = set()
    for ev in events:
        if not _is_code_verdict(ev):
            continue
        verdict = (ev.payload or {}).get("verdict")
        if not isinstance(verdict, dict):
            continue
        for pf in verdict.get("prior_findings") or []:
            if not isinstance(pf, dict):
                continue
            pid, disp = pf.get("id"), pf.get("disposition")
            if not isinstance(pid, str):
                continue
            if disp == "resolved":
                resolved.add((ev.change_id, pid))
            elif disp == "wontfix":
                wontfix.add((ev.change_id, pid))
    return resolved, wontfix


def _raised_ids(events: list[Event]) -> set[tuple[str, str]]:
    """(change_id, id) pairs raised by these events (per-change identity)."""
    ids: set[tuple[str, str]] = set()
    for ev in events:
        if not _is_code_verdict(ev):
            continue
        verdict = (ev.payload or {}).get("verdict")
        if not isinstance(verdict, dict):
            continue
        for f in verdict.get("findings") or []:
            fid = f.get("id") if isinstance(f, dict) else None
            if isinstance(fid, str):
                ids.add((ev.change_id, fid))
    return ids


def _finding_counts(windowed: list[Event], all_events: list[Event]) -> tuple[int, int, int]:
    """(resolved, wontfix, open_undisposed).

    resolved/wontfix: disposed in the WINDOW. open_undisposed: raised in the
    window, never disposed anywhere in the FULL stream (no user-action claim, no
    window-boundary fabrication).
    """
    resolved_w, wontfix_w = _dispositions(windowed)
    if all_events:
        resolved_all, wontfix_all = _dispositions(all_events)
        disposed_all = resolved_all | wontfix_all
    else:
        disposed_all = set()
    raised_w = _raised_ids(windowed)
    open_undisposed = raised_w - disposed_all
    return len(resolved_w), len(wontfix_w), len(open_undisposed)


def _undisclosed_bypasses(windowed: list[Event], all_events: list[Event]) -> int:
    """Order-aware count: a `gate_bypassed` in the window is undisclosed when no
    `gate_bypass_disclosed` follows it on the same change (disclosure only covers
    bypasses BEFORE it)."""
    windowed_ids = {e.event_id for e in windowed}
    last_disclosure: dict[str, int] = {}
    for i, ev in enumerate(all_events):
        if ev.type == "gate_bypass_disclosed":
            last_disclosure[ev.change_id] = i
    count = 0
    for i, ev in enumerate(all_events):
        if ev.type != "gate_bypassed" or ev.event_id not in windowed_ids:
            continue
        if i > last_disclosure.get(ev.change_id, -1):  # no disclosure after this bypass
            count += 1
    return count


def _edits_blocked(
    records: list[GateBlockRecord], lo: datetime | None, hi: datetime | None
) -> int:
    """Distinct out-of-lifecycle edit targets the gate held in the window, deduped
    by ``(change_id, file, state)``.

    Raw block records are append-only and duplicate on agent retries; the honest
    count is DISTINCT edit targets, not raw block events — a deliberate
    conservative floor that UNDER-counts (retries collapse), never inflates (we
    record no edit content, so a retry cannot be told from a genuinely separate
    edit to the same file in the same state). A record whose ts can't be placed is
    excluded when a window bound is set (mirrors ``_in_window``).
    """
    seen: set[tuple[str, str | None, str]] = set()
    for r in records:
        if lo is not None or hi is not None:
            ts = parse_ts(r.ts)
            if ts is None or (lo is not None and ts < lo) or (hi is not None and ts > hi):
                continue
        seen.add((r.change_id, r.file, r.state))
    return len(seen)


def _honest_int(value: object) -> int | None:
    """An integer a producer actually reported, else None.

    `bool` is excluded deliberately: `isinstance(True, int)` holds in Python, so a
    JSON `true` landing in a numeric usage field would otherwise be counted as one
    token. A nonsense value must read as 'not captured', never as a small number.
    """
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


# Cache keys that are ADDITIONAL to `input_tokens`. Summed by name, never by
# pattern — the two shipped producers disagree and a "looks like cache" rule would
# be wrong for one of them:
#
#   claude  input_tokens: 63          cache_read_input_tokens: 2,629,763   -> additive
#   codex   input_tokens: 1,007,614   cached_input_tokens:       898,816   -> ALREADY INSIDE
#
# Adding codex's key would inflate its total by ~89%; leaving it alone is already
# correct. codex's `reasoning_output_tokens` also stays uncounted — a few thousand
# against a million is below the resolution this number serves.
_ADDITIVE_CACHE_KEYS = ("cache_read_input_tokens", "cache_creation_input_tokens")
_SUMMED_USAGE_KEYS = ("input_tokens", "output_tokens", *_ADDITIVE_CACHE_KEYS)


def usage_tokens(usage: object) -> int | None:
    """Best-effort token total from a producer-reported usage dict. None if absent.

    Prefer an explicit total; else sum the named keys; else None. NEVER guess from
    arbitrary keys — an unknown shape must read as 'not captured', never fabricate.
    """
    if not isinstance(usage, dict):
        return None
    total = _honest_int(usage.get("total_tokens"))
    if total is not None:
        return total
    known = [
        value
        for value in (_honest_int(usage.get(key)) for key in _SUMMED_USAGE_KEYS)
        if value is not None
    ]
    return sum(known) if known else None


def _reported_cost(receipt: object) -> float | None:
    """A cost the producer stated about itself, else None. Never derived."""
    if not isinstance(receipt, dict):
        return None
    value = receipt.get("reported_cost_usd")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        cost = float(value)
    except OverflowError:
        return None
    return cost if math.isfinite(cost) and cost >= 0 else None


def _review_cost(rows: tuple[CostBreakdownRow, ...]) -> tuple[int | None, float | None]:
    """Recorded subtotals only; absent data stays unknown."""
    tokens = [row.tokens for row in rows if row.tokens is not None]
    costs = [row.reported_cost_usd for row in rows if row.reported_cost_usd is not None]
    return sum(tokens) if tokens else None, sum(costs) if costs else None


def _cost_breakdown(events: list[Event]) -> tuple[CostBreakdownRow, ...]:
    """Join observations in the window, without importing usage from outside it.

    A run issued before the window and failing inside it is a failure observation,
    not a start in this window. External evidence is always its own record; opaque
    original_evidence is never parsed for usage, findings or guessed invocations.
    """
    from dataclasses import replace

    rows: dict[tuple[str, str, str], CostBreakdownRow] = {}
    ordinals: dict[tuple[str, str], dict[str, int]] = {}
    outcomes = {
        (ev.change_id, str(ev.payload.get("round_id"))): str(ev.payload.get("outcome"))
        for ev in events if ev.type == "review_round_closed"
    }

    def legacy(ev: Event, data: dict[str, Any], *, started: bool = False) -> None:
        payload = ev.payload
        receipt = data.get("receipt")
        receipt = receipt if isinstance(receipt, dict) else {}
        rid = str(payload.get("round_id") or "")
        role = str(payload.get("reviewer") or "unknown")
        identity = str(data.get("run_id") or receipt.get("run_id") or ev.event_id)
        key = (ev.change_id, "legacy_run", identity)
        ordinal = 0
        if rid:
            seen = ordinals.setdefault((ev.change_id, role), {})
            ordinal = seen.setdefault(rid, len(seen) + 1)
        row = rows.get(key, CostBreakdownRow(
            role=role, source=str(data.get("source") or "unknown"),
            change_id=ev.change_id, round=ordinal, round_id=rid,
            tokens=None, findings_raised=0, outcome=outcomes.get((ev.change_id, rid), "open"),
            record_id=identity,
        ))
        verdict = data.get("verdict")
        findings = verdict.get("findings") if isinstance(verdict, dict) else None
        usage = receipt.get("usage", data.get("usage"))
        tokens = usage_tokens(usage)
        cost = _reported_cost(receipt)
        if cost is None:
            cost = _reported_cost(data)
        imported = ev.type == "review_result_imported"
        rows[key] = replace(
            row,
            source=str(data.get("source") or receipt.get("source") or row.source),
            started=row.started or started,
            failed=row.failed or ev.type == "review_run_failed",
            imported=row.imported or imported,
            tokens=tokens if tokens is not None else row.tokens,
            reported_cost_usd=cost if cost is not None else row.reported_cost_usd,
            component_subtotal=(
                _honest_int(usage.get("total_tokens")) is None
                if tokens is not None and isinstance(usage, dict) else row.component_subtotal
            ),
            findings_raised=len(findings) if isinstance(findings, list) else row.findings_raised,
        )

    for ev in events:
        payload = ev.payload
        if ev.type == "review_round_started":
            runs = payload.get("runs")
            if isinstance(runs, list):
                for run in runs:
                    if isinstance(run, dict) and isinstance(run.get("run_id"), str):
                        legacy(ev, run, started=True)
        elif ev.type in {"review_run_failed", "review_result_imported"}:
            legacy(ev, payload)
        elif ev.type == "review_evidence_imported":
            evidence = payload.get("evidence")
            if not isinstance(evidence, dict):
                evidence = {}
            identity = str(evidence.get("evidence_id") or ev.event_id)
            process = evidence.get("process")
            process = process if isinstance(process, dict) else {}
            usage = evidence.get("usage")
            tokens = usage_tokens(usage)
            rows[(ev.change_id, "external_evidence", identity)] = CostBreakdownRow(
                role=str(evidence.get("kind") or "unknown"),
                source=str(process.get("id") or "unknown"), change_id=ev.change_id,
                round=0, round_id="", tokens=tokens, findings_raised=0,
                outcome=str(evidence.get("decision") or "unknown"),
                record_type="external_evidence", record_id=identity, imported=True,
                reported_cost_usd=_reported_cost(evidence),
                component_subtotal=(tokens is not None and isinstance(usage, dict)
                                    and _honest_int(usage.get("total_tokens")) is None),
                subject_id=str(evidence.get("subject_id") or ""),
                issuer=str(evidence.get("issuer") or "unknown"),
                process_version=str(process.get("version") or "unknown"),
                historical_only=payload.get("historical_only") is True,
                supersedes=str(evidence.get("supersedes") or ""),
            )
    return tuple(rows.values())


def _rejected_rounds(events: list[Event]) -> int:
    """Count ONLY `review_round_closed` closures the reviewer rejected. Excludes
    `execution_failed` — that outcome conflates infra-stale / incomplete-governance
    / the normal human-quorum-pending path, so counting it would fabricate rework.
    """
    return sum(
        1 for ev in events
        if ev.type == "review_round_closed"
        and (ev.payload or {}).get("outcome") == "rejected"
    )


def _budget_rounds_held(events: list[Event]) -> int:
    """Distinct (change_id, reviewer, attempted_round) triples the budget refused.

    Deduped on purpose: `review begin` emits one event per refused invocation, so a
    retrying agent would otherwise inflate a number the report and the merge
    attestation both present as rounds. An event missing `attempted_round` (older or
    malformed) falls back to its own id so it counts once and never merges with
    another round.

    ``change_id`` is part of the identity, like everywhere else in this module
    (``_edits_blocked`` keys on ``(change_id, file, state)``; ``_dispositions`` on
    ``(change_id, id)``). Without it the count collapses across changes: ``report`` is
    repo-wide and, at the shipped plan budget of 6, EVERY change's first block carries
    ``attempted_round=7``, so a global key would fold all of them into one and
    undercount exactly the thing this number exists to make visible.
    """
    seen: set[tuple[str, str, object]] = set()
    for ev in events:
        if ev.type != "review_budget_exceeded":
            continue
        payload = ev.payload if isinstance(ev.payload, dict) else {}
        reviewer = payload.get("reviewer")
        attempted = payload.get("attempted_round")
        key = attempted if isinstance(attempted, int) else f"event:{ev.event_id}"
        seen.add((ev.change_id, reviewer if isinstance(reviewer, str) else "", key))
    return len(seen)


def derive_authorizations(events: list[Event]) -> tuple[AuthorizationRecord, ...]:
    """Every `review_round_authorized` in these events, in append order.

    Deliberately NOT deduped, which is the opposite of `_budget_rounds_held` right
    above and worth stating plainly. The brake's block is emitted by the harness once
    per refused invocation, so a retrying agent inflates it and it has to collapse
    retries. An authorization is emitted once per deliberate act, so collapsing two
    identical ones would report `1` for a human who acted twice — understating in the
    exact direction that hides the abuse this count exists to expose.

    It also lives here rather than in `attestation.py`: nothing at the merge boundary
    consumes it, and the two modules read events through different parsers (strict
    `parse_event_line` vs the tolerant dict iterator), so a shared derivation would
    have to pick one contract and break the other's.

    Never raises. A malformed payload yields a record with `reviewer='unknown'` and
    `reason=None` rather than being dropped: the count is the mechanism, and silently
    losing an authorization is the one failure mode that cannot be tolerated here.
    """
    out: list[AuthorizationRecord] = []
    for ev in events:
        if ev.type != "review_round_authorized":
            continue
        payload = ev.payload if isinstance(ev.payload, dict) else {}
        reviewer = payload.get("reviewer")
        reason = payload.get("reason")
        out.append(AuthorizationRecord(
            change_id=ev.change_id,
            reviewer=reviewer if isinstance(reviewer, str) and reviewer else "unknown",
            reason=reason if isinstance(reason, str) and reason else None,
            timestamp=ev.timestamp,
            actor=ev.actor.identifier if ev.actor is not None else "unknown",
        ))
    return tuple(out)


def derive_reopens(events: list[Event]) -> tuple[ReopenRecord, ...]:
    """Every `implementation_invalidated` in these events, in append order.

    Not deduped, for the reason `derive_authorizations` gives just above: each event is
    one deliberate act, and collapsing two identical reopens would report `1` for
    someone who voided two reviews. Never raises — a malformed payload yields a record
    with `reason=None` rather than being dropped, because a lost reopen is the one
    failure this count cannot tolerate.
    """
    out: list[ReopenRecord] = []
    for ev in events:
        if ev.type != "implementation_invalidated":
            continue
        payload = ev.payload if isinstance(ev.payload, dict) else {}
        reason = payload.get("reason")
        out.append(ReopenRecord(
            change_id=ev.change_id,
            reason=reason if isinstance(reason, str) and reason else None,
            timestamp=ev.timestamp,
            actor=ev.actor.identifier if ev.actor is not None else "unknown",
        ))
    return tuple(out)


def _armed_decisions(workspace_root: Path) -> int:
    """Ratified decisions carrying an executable check (bite-test). Best-effort:
    any load error -> 0 (the footnote must never crash the report)."""
    try:
        from keepsail.core.decisions import load_decisions
        decisions, _errors = load_decisions(workspace_root)
    except Exception:
        return 0
    return sum(1 for d in decisions if d.status == "ratified" and d.check is not None)


def build_value_report(
    events_file: Path,
    *,
    since: str | None,
    until: str | None,
    workspace_root: Path,
) -> ValueReport:
    lo = parse_ts(since) if since else None
    hi = parse_ts(until) if until else None
    if hi is not None and until is not None and _DATE_ONLY_RE.fullmatch(until.strip()):
        # Date-only upper bound is inclusive of the whole day (the CLI/docs promise
        # events "on/before this ISO date"); extend midnight to end-of-day (CODX-008).
        hi = hi.replace(hour=23, minute=59, second=59, microsecond=999999)
    all_events = _read_all_events(events_file)          # full stream (causality)
    windowed = [e for e in all_events if _in_window(e, lo, hi)]
    block_records = read_blocks(gate_blocks_path(workspace_root))
    findings_resolved, findings_wontfix, findings_open_undisposed = _finding_counts(
        windowed, all_events
    )
    rows = _cost_breakdown(windowed)
    legacy = [row for row in rows if row.record_type == "legacy_run"]
    external = [row for row in rows if row.record_type == "external_evidence"]
    review_tokens, reported_cost = _review_cost(rows)
    authorizations = derive_authorizations(windowed)
    reopens = derive_reopens(windowed)
    return ValueReport(
        since=since,
        until=until,
        changes_touched=len({e.change_id for e in windowed}),
        findings_resolved=findings_resolved,
        findings_open_undisposed=findings_open_undisposed,
        undisclosed_bypasses=_undisclosed_bypasses(windowed, all_events),
        edits_blocked=_edits_blocked(block_records, lo, hi),
        review_tokens=review_tokens,
        review_runs_total=len(legacy),
        review_runs_with_usage=sum(row.tokens is not None for row in legacy),
        findings_wontfix=findings_wontfix,
        rejected_rounds=_rejected_rounds(windowed),
        armed_decisions=_armed_decisions(workspace_root),
        cost_breakdown=rows,
        review_reported_cost_usd=reported_cost,
        review_runs_with_reported_cost=sum(row.reported_cost_usd is not None for row in legacy),
        review_budget_hits=_budget_rounds_held(windowed),
        authorizations=authorizations,
        authorizations_total=len(authorizations),
        reopens=reopens,
        reopens_total=len(reopens),
        review_records_total=len(rows),
        review_records_with_usage=sum(row.tokens is not None for row in rows),
        review_records_with_reported_cost=sum(row.reported_cost_usd is not None for row in rows),
        review_component_subtotals=sum(row.component_subtotal for row in rows),
        review_attempts_started=sum(row.started for row in legacy),
        review_execution_failures=sum(row.failed for row in legacy),
        review_results_imported=sum(row.imported for row in legacy),
        review_rounds_started=sum(ev.type == "review_round_started" for ev in windowed),
        review_rounds_execution_failed=sum(
            ev.type == "review_round_closed" and ev.payload.get("outcome") == "execution_failed"
            for ev in windowed
        ),
        external_conclusions_imported=len(external),
        external_approvals=sum(row.outcome == "approve" for row in external),
        external_rejections=sum(row.outcome == "reject" for row in external),
        review_skips=sum(
            ev.type in {"plan_approved", "code_review_passed"}
            and ev.payload.get("skipped") is True for ev in windowed
        ),
    )
