"""Layer-2 CI merge gate (HG-DF item C) — attestation write + verify logic.

Pure-function domain layer. The CLI (`cli/attest.py`) owns the git/filesystem
boundary and calls these. Reuses `find_ordering_violations` + `derive_state`
unchanged. See docs/plans/2026-06-03-layer2-merge-gate-design.md.

What this proves (per design §2): for every changed file in a PR, there EXISTS
a committed attestation declaring that file in scope, encoding a complete,
correctly-ordered lifecycle reaching READY_TO_MERGE incl. a genuine
`code_review_passed`. It does NOT prove the file was edited through the gated
path (an actor who bypasses the editor but also runs a trivial covering
lifecycle passes — deferred forgery-resistance, HG-12/B).
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    ApprovalError,
    Recognition,
    is_attestation_path,
    load_recognition,
    resolve_review_reference,
)
from keepsail.core.attestation_replay import (
    _knowledge_attestation,
    _new_contract_blockers,
    _review_reference_blockers,
    derive_independence,
    gate_bypass_disclosure,
)
from keepsail.core.attestation_replay import (
    events_from_stateful_attestation as events_from_stateful_attestation,
)
from keepsail.core.emit_validation import find_ordering_violations
from keepsail.core.events import Event, EventSchemaError, effective_event_lines, parse_event_line
from keepsail.core.git_diff import DiffEntry, parse_name_status_z
from keepsail.core.reducer import derive_state
from keepsail.core.scope_match import GitScopeError, resolve_commit, tracked_files_at_commit

ATTESTATIONS_DIRNAME = ".harness/attestations"
# Reader-only rollout keeps this at v1 until the decoder is in the trusted base.
# The subsequent producer release enables v2 without changing verifier selection.
ATTESTATION_FORMAT = "v2"
PLACEHOLDER_IDENTITY = "cli"
MILESTONE_EVENTS: frozenset[str] = frozenset(
    {"plan_approved", "implementation_complete", "code_review_passed"}
)
REQUIRED_STATE = "READY_TO_MERGE"


def canonical_path(raw: str) -> str:
    """Normalize to POSIX form: forward slashes, no leading './', collapsed
    intra-path '.'/'..' segments (via ``posixpath.normpath``).

    Applied to BOTH git-diff output and stored ``scope.files`` so set membership
    is spelling-independent (``./src/x`` == ``src/x``). Note: a leading ``..`` or
    an absolute path is preserved as-is (``normpath`` cannot resolve it without a
    base) — git never emits such paths for tracked files, and a non-canonical
    scope entry that fails to match simply fails closed (uncovered → FAIL).
    """
    p = raw.replace("\\", "/").strip()
    p = posixpath.normpath(p)
    return "" if p == "." else p


# --------------------------------------------------------------------------- #
# git --name-status parsing
# --------------------------------------------------------------------------- #


def parse_name_status(raw: str) -> list[DiffEntry]:
    """Parse ``git diff --name-status`` output into ``DiffEntry`` list.

    Each non-blank line is tab-separated: ``STATUS<TAB>PATH`` (A/M/D) or
    ``R<score><TAB>OLD<TAB>NEW`` (rename/copy — two path columns). Paths are
    canonicalized; blank lines and status-only lines are skipped.
    """
    if "\0" in raw:
        return parse_name_status_z(raw)
    entries: list[DiffEntry] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        paths = tuple(canonical_path(p) for p in parts[1:] if p.strip())
        if not status or not paths:
            continue
        entries.append(DiffEntry(status=status, paths=paths))
    return entries




# --------------------------------------------------------------------------- #
# Attestation extraction + write
# --------------------------------------------------------------------------- #
def extract_change_events(events_file: Path, slug: str) -> list[str]:
    """Return verbatim events.jsonl lines whose ``change_id == slug``, in append
    order.

    Raises ``ValueError`` if the file is missing or no line matches — a
    silent-empty attestation would be a useless / misleading artifact.
    """
    if not events_file.exists():
        raise ValueError(f"events file not found: {events_file}")
    out: list[str] = []
    for raw in events_file.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("change_id") == slug:
            out.append(raw)
    if not out:
        raise ValueError(f"no events for change {slug!r} in {events_file}")
    return out


def write_attestation(events_file: Path, attestations_dir: Path, slug: str, *,
                      format_version: str | None = None) -> Path:
    """Snapshot the per-change event slice to ``<attestations_dir>/<slug>.jsonl``
    (idempotent overwrite)."""
    from keepsail.core.knowledge import load_policy, read_inputs, retain_checkpoint
    selected = format_version or ATTESTATION_FORMAT
    if selected not in {"v1", "v2", "v3", "v1-bootstrap"}:
        raise ValueError("unsupported attestation output format")
    root = events_file.parent.parent
    if format_version != "v3":
        from keepsail.core.approval import (
            ApprovalError,
            recognition_contract_active,
            resolve_contract_base,
        )
        from keepsail.core.git_objects import optional_regular_blob_text
        from keepsail.core.policy_authority import parse_unique_yaml

        try:
            base = resolve_contract_base(root)
        except ApprovalError:
            if recognition_contract_active(root):
                raise
        else:
            trusted = optional_regular_blob_text(root, base, ".harness/review-recognition.yaml")
            raw = parse_unique_yaml(trusted) if trusted is not None else None
            if (isinstance(raw, dict) and raw.get("enabled") is True
                    and raw.get("version") == "review-recognition/v2"):
                from keepsail.core.effective_policy import load_effective_v2

                load_effective_v2(root, base)
                if format_version is not None:
                    raise ValueError("active delivery policy requires v3 attestation")
                selected = "v3"
    if ATTESTATION_FORMAT == "v1" and selected in {"v2", "v3"}:
        raise ValueError("reader-only release cannot produce v2/v3; upgrade the producer first")
    policy = load_policy(root)
    if selected == "v3":
        from keepsail.core.approval import canonical_json
        from keepsail.engineering.attestation_v3 import build_v3_attestation

        if policy is not None:
            retain_checkpoint(events_file, slug, compact=True)
        record = build_v3_attestation(root, events_file, slug)
        out_path = attestations_dir / "v3" / f"{slug}.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = canonical_json(record) + "\n"
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != content:
            out_path.write_text(content, encoding="utf-8", newline="\n")
        return out_path
    if format_version in {"v2", "v1-bootstrap"} and policy is None:
        raise ValueError(f"{format_version} requires an activated knowledge policy")
    retain_checkpoint(events_file, slug, compact=selected == "v2",
                       bootstrap=selected == "v1-bootstrap")
    if policy is not None and selected == "v2":
        from keepsail.core.approval import resolve_contract_base
        from keepsail.core.attestation_format import make_attestation
        from keepsail.core.context import _approval_lineage
        from keepsail.core.knowledge_checkpoint import make_checkpoint
        inputs = read_inputs(root, events_file=events_file)
        state = inputs.states[slug]
        record = make_attestation(slug, inputs, make_checkpoint(
            root, slug, inputs, resolve_contract_base(root)), _approval_lineage(
                root, slug, state.effective_approval, lines=inputs.effective_lines, effective=True))
        out_path = attestations_dir / "v2" / f"{slug}.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != content:
            out_path.write_text(content, encoding="utf-8")
        return out_path
    lines = extract_change_events(events_file, slug)
    if selected == "v1-bootstrap" and policy is not None:
        # Old readers require inline review conclusions. This explicit one-time
        # compatibility projection never changes the retained native originals.
        preceding: list[dict[str, Any]] = []
        projected = []
        for line in lines:
            event = parse_event_line(line)
            if event.payload.get("review_reference_version"):
                from keepsail.core.approval import digest_record
                from keepsail.core.events import Actor, serialize_event
                payload = dict(event.payload)
                kind = "plan" if event.type.startswith("plan_") else "code"
                decision = "approve" if event.type.endswith(("approved", "passed")) else "reject"
                subject = (payload.get("approval") or payload.get("code_subject") or {}).get(
                    "subject_id", payload.get("candidate_id"))
                if not isinstance(subject, str):
                    raise ValueError("bootstrap review reference lacks its exact subject")
                payload["evidence"] = resolve_review_reference(
                    payload, preceding, change_id=slug, kind=kind, decision=decision,
                    subject_id=subject)
                payload.pop("review_reference_version")
                event = Event(
                    event_id="derived-" + digest_record([event.event_id, payload]),
                    type=event.type, change_id=event.change_id, timestamp=event.timestamp,
                    actor=Actor(event.actor.type, event.actor.identifier),
                    framework=event.framework,
                    payload=payload, framework_state={
                        "representation": "legacy-bootstrap-derived-not-original-event-bytes",
                        "source_event_id": event.event_id,
                    })
                line = serialize_event(event)
            projected.append(line)
            if event.type == "review_evidence_imported":
                preceding.append(event.payload["evidence"])
        lines = projected
    attestations_dir.mkdir(parents=True, exist_ok=True)
    out_path = attestations_dir / f"{slug}.jsonl"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
def check_attestation(
    attestation_path: Path, slug: str, *, recognition: Recognition | None = None
) -> list[str]:
    """Return blocker strings for one attestation file (empty list = OK).

    The filename↔content binding is checked FIRST (and short-circuits) so a slug
    mismatch FAILs cleanly rather than ``KeyError``-ing on the state lookup.
    Reuses ``derive_state`` + ``find_ordering_violations`` unchanged.
    A trusted recognition contract delegates review authority checks to
    ``verify_attestations``' mandatory new-contract validation. Without that
    context, direct callers retain legacy receipt enforcement.
    """
    blockers: list[str] = []
    try:
        states = derive_state(attestation_path)
    except (ApprovalError, EventSchemaError) as exc:
        return [f"attestation {slug}: invalid lifecycle evidence: {exc}"]
    if set(states.keys()) != {slug}:
        blockers.append(
            f"attestation {attestation_path.name}: filename slug {slug!r} does "
            f"not match contained change_id(s) {sorted(states.keys())}"
        )
        return blockers
    violations = find_ordering_violations(attestation_path, slug)
    if violations:
        blockers.append(
            f"attestation {slug}: lifecycle ordering invalid "
            f"({len(violations)} violation(s); first: {violations[0].reason})"
        )
    cs = states[slug]
    if cs.current_state != REQUIRED_STATE:
        blockers.append(f"attestation {slug}: state is {cs.current_state}, not {REQUIRED_STATE}")
    missing = sorted(MILESTONE_EVENTS - set(cs.event_counts.keys()))
    if missing:
        blockers.append(f"attestation {slug}: missing milestone event(s) {missing}")
    events: list[Event] = []
    for raw in effective_event_lines(
        attestation_path.read_bytes().decode("utf-8").splitlines(keepends=True)
    ):
        try:
            event = parse_event_line(raw)
        except EventSchemaError:
            continue
        if event.change_id == slug:
            events.append(event)
    if recognition is None:
        blockers.extend(_review_receipt_blockers(events, slug))
        blockers.extend(_review_reference_blockers(events, slug))
    return blockers




def _review_receipt_blockers(events: list[Event], slug: str) -> list[str]:
    """Require imported receipts once a stream opts into the new run protocol."""

    if not any(event.type == "review_round_started" for event in events):
        return []  # Historical lifecycle events remain readable and verifiable.
    milestone = next(
        (event for event in reversed(events) if event.type == "code_review_passed"),
        None,
    )
    if milestone is None or milestone.payload.get("skipped") is True:
        return []
    receipt_ids = milestone.payload.get("receipt_ids")
    if (
        not isinstance(receipt_ids, list)
        or not receipt_ids
        or any(not isinstance(receipt_id, str) or not receipt_id for receipt_id in receipt_ids)
    ):
        return [f"attestation {slug}: protocol code review approval has no imported receipt_ids"]
    imported: dict[str, str] = {}
    for event in events:
        if event.type != "review_result_imported":
            continue
        receipt = event.payload.get("receipt")
        if not isinstance(receipt, dict):
            continue
        receipt_id = receipt.get("receipt_id")
        source = receipt.get("source")
        if isinstance(receipt_id, str) and isinstance(source, str):
            imported[receipt_id] = source
    missing_receipts = [receipt_id for receipt_id in receipt_ids if receipt_id not in imported]
    if missing_receipts:
        return [
            f"attestation {slug}: code review references missing imported receipt(s) "
            f"{missing_receipts}"
        ]
    expected_sources = milestone.payload.get("independent_sources")
    if isinstance(expected_sources, list) and set(expected_sources) != {
        imported[receipt_id] for receipt_id in receipt_ids
    }:
        return [f"attestation {slug}: imported receipt sources do not match independent_sources"]
    return []


def _trusted_recognition(root: Path, *, base: str | None) -> Recognition | None:
    """Load the trusted-base contract, or identify the legacy first-cutover case."""
    if base is not None:
        # The CLI has already failed closed if Git cannot resolve the merge
        # base.  Keep the pure verifier's legacy/unit-test path tolerant of a
        # synthetic base ref while preserving strict policy parsing whenever
        # the trusted commit is reachable.
        try:
            commit = resolve_commit(root, base)
        except GitScopeError:
            return None
        try:
            tracked = tracked_files_at_commit(root, commit)
        except GitScopeError:
            return None
        if ".harness/review-recognition.yaml" not in tracked:
            return None
    try:
        return load_recognition(root, ref=base) if base is not None else load_recognition(root)
    except ApprovalError as exc:
        if str(exc) in {
            "review recognition policy is not configured",
            "no review process is enabled by user recognition",
        }:
            return None
        raise


@dataclass
class AttestationVerdict:
    ok: bool
    blockers: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    covered: list[str] = field(default_factory=list)
    attestations: list[str] = field(default_factory=list)
    attestation_paths: dict[str, str] = field(default_factory=dict)
    independence: dict[str, dict[str, Any]] = field(default_factory=dict)
    gate_bypasses: dict[str, dict[str, Any]] = field(default_factory=dict)
    policy_basis: dict[str, Any] = field(default_factory=dict)
    delivery_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)


def _is_attestation_path(canonical: str) -> bool:
    # Only actual attestation EVIDENCE (.jsonl) is exempt from the subject set.
    # A non-.jsonl file committed under the dir (e.g. .harness/attestations/x.py)
    # must stay a subject requiring coverage — otherwise it would be neither
    # subject nor evidence and escape the gate entirely (fail-OPEN, B1 / §5).
    return is_attestation_path(canonical)


def verify_attestations(
    root: Path,
    diff_entries: list[DiffEntry],
    *,
    base: str | None = None,
    head: str | None = None,
    repository_id: str | None = None,
    target_ref: str | None = None,
) -> AttestationVerdict:
    """Core merge-gate verdict (design §4.2). Fail-closed: any blocker → not ok.

    A subject file (every changed path that is NOT under the attestations dir)
    passes only if it is in the validated actual coverage (legacy: ``scope.files``)
    of a complete, ordered,
    READY_TO_MERGE attestation that is newly ADDED in this diff and covers at
    least one subject of this diff.
    """
    blockers: list[str] = []
    subjects: set[str] = set()
    attestation_entries: list[DiffEntry] = []

    for e in diff_entries:
        if any(_is_attestation_path(p) for p in e.paths):
            attestation_entries.append(e)
        for p in e.paths:
            if not _is_attestation_path(p):
                subjects.add(p)

    # Attestation files must be ADD-only (closes the "edit a trusted attestation
    # to fabricate" vector). Collect the slugs of newly-added attestations.
    added_attestations: list[tuple[str, str]] = []
    for e in attestation_entries:
        if e.status != "A":
            blockers.append(
                f"attestation file changed with status {e.status!r} (only "
                f"newly-ADDED attestations are allowed): {list(e.paths)}"
            )
            continue
        for p in e.paths:
            if _is_attestation_path(p) and p.endswith(".jsonl"):
                added_attestations.append((posixpath.basename(p)[: -len(".jsonl")], p))

    covered: set[str] = set()
    validated: list[str] = []
    validated_paths: dict[str, str] = {}
    v3_independence: dict[str, dict[str, Any]] = {}
    v3_gate_bypasses: dict[str, dict[str, Any]] = {}
    delivery_decisions: dict[str, dict[str, Any]] = {}
    policy_basis: dict[str, Any] = {}
    active_v2 = False
    if base and head:
        from keepsail.core.git_objects import optional_regular_blob_text
        from keepsail.core.policy_authority import parse_unique_yaml

        try:
            trusted_text = optional_regular_blob_text(
                root, base, ".harness/review-recognition.yaml"
            )
            trusted = parse_unique_yaml(trusted_text) if trusted_text is not None else None
            if (isinstance(trusted, dict) and trusted.get("enabled") is True
                    and trusted.get("version") == "review-recognition/v2"):
                active_v2 = True
                if not repository_id or not target_ref:
                    blockers.append("active v2 policy requires trusted repository identity and "
                                    "target ref")
                else:
                    from keepsail.core.attestation_v3_verify import verify_v2_activation

                    policy_basis = verify_v2_activation(
                        root, trusted_commit=base, repository_id=repository_id,
                        target_ref=target_ref,
                    )
                for slug, path in added_attestations:
                    if path != f"{ATTESTATIONS_DIRNAME}/v3/{slug}.jsonl":
                        blockers.append(f"attestation {slug}: active policy requires v3 evidence")
        except (ApprovalError, GitScopeError, ValueError, TypeError) as exc:
            blockers.append(f"trusted review policy cannot be read: {exc}")
    for slug, relative in added_attestations:
        if sum(s == slug for s, _ in added_attestations) != 1:
            blockers.append(f"attestation {slug}: ambiguous duplicate slug in the diff")
            continue
        if relative == f"{ATTESTATIONS_DIRNAME}/v3/{slug}.jsonl":
            if not all((base, head, repository_id, target_ref)):
                blockers.append(f"attestation {slug}: v3 requires trusted base, head, repository "
                                "identity and target ref")
                continue
            from keepsail.core.attestation_v3 import parse_v3_line
            from keepsail.core.attestation_v3_verify import verify_v3_delivery, verify_v3_transition
            from keepsail.core.git_objects import regular_blob_bytes

            try:
                assert base is not None and head is not None
                assert repository_id is not None and target_ref is not None
                record = parse_v3_line(regular_blob_bytes(root, head, relative))
                if record["change_id"] != slug:
                    raise ApprovalError("v3 filename and Change differ")
                verifier = verify_v3_delivery if active_v2 else verify_v3_transition
                result = verifier(root, record, base=base, head=head,
                                  repository_id=repository_id, target_ref=target_ref)
            except (ApprovalError, GitScopeError, ValueError, KeyError, TypeError) as exc:
                blockers.append(f"attestation {slug}: v3 transition invalid: {exc}")
                continue
            this_covered = set(result["coverage"])
            if not (this_covered & subjects):
                blockers.append(f"attestation {slug}: its scope covers no file in this diff")
                continue
            covered |= this_covered
            validated.append(slug)
            validated_paths[slug] = relative
            v3_independence[slug] = result["independence"]
            v3_gate_bypasses[slug] = result["gate_bypass"]
            if "code_review_required" in result:
                delivery_decisions[slug] = {
                    "trusted_base": result["trusted_base"],
                    "policy_digest": result["policy_digest"],
                    "code_review_required": result["code_review_required"],
                    "reason": result["code_review_reason"],
                }
            continue
        att_path = root / relative
        if not att_path.exists():
            blockers.append(f"attestation file for {slug!r} not found at head")
            continue
        try:
            recognition = _trusted_recognition(root, base=base)
        except ApprovalError as exc:
            blockers.append(f"attestation {slug}: review recognition is not usable: {exc}")
            continue
        # Historical rounds do not select the current review contract. When a
        # trusted contract is active, its full authority checks below replace
        # legacy receipt checks; an evidence marker alone grants no exemption.
        att_blockers = check_attestation(att_path, slug, recognition=recognition)
        if att_blockers:
            blockers.extend(att_blockers)
            continue
        cs = derive_state(att_path)[slug]
        try:
            _knowledge_attestation(root, att_path, cs, base=base, head=head)
        except (ApprovalError, ValueError, KeyError, TypeError) as exc:
            blockers.append(f"attestation {slug}: knowledge evidence invalid: {exc}")
            continue
        if recognition is not None and cs.effective_approval is None:
            blockers.append(
                f"attestation {slug}: active review recognition requires an effective plan approval"
            )
            continue
        elif recognition is not None:
            att_blockers = _new_contract_blockers(
                root,
                cs,
                slug,
                diff_entries,
                recognition=recognition,
                base=base,
                head=head,
                attestation_path=att_path,
            )
            blockers.extend(att_blockers)
            if att_blockers:
                continue
        # Recognized approvals validate actual coverage above. Initial scope is
        # only an estimate in that contract; historical lifecycles retain it.
        this_covered = (
            {item["path"] for item in cs.coverage_manifest
             if isinstance(item, dict) and isinstance(item.get("path"), str)}
            if recognition is not None
            else {canonical_path(f) for f in cs.scope.get("files", [])}
        )
        if not (this_covered & subjects):
            blockers.append(
                f"attestation {slug}: its scope covers no file in this diff "
                "(stale or forward-planted)"
            )
            continue
        covered |= this_covered
        validated.append(slug)
        validated_paths[slug] = relative
        disclosure = independence_for_attestation(att_path)
        # Both roles, same bar. Plan review joined on the cut that made a plan-reviewer
        # skip reachable after a rejection; leaving it off would have shipped the escape
        # hatch and the missing signal together.
        for role, label in (("code_review", "code review"), ("plan_review", "plan review")):
            row = disclosure[role]
            if row["skipped"] and not row["override"]:
                blockers.append(
                    f"attestation {slug}: {label} was skipped without --override "
                    "(a deliberate `review skip --override --reason ...` is required to merge)"
                )
        gb = gate_bypass_for_attestation(att_path)
        if gb["undisclosed"] > 0:
            blockers.append(
                f"attestation {slug}: the gate was bypassed {gb['undisclosed']} time(s) "
                f"during this change without disclosure (a deliberate "
                f'`attest write {slug} --disclose-gate-bypass "<reason>"` is required to merge)'
            )

    if base and head:
        from keepsail.core.transition_guard import committed_transition_required

        try:
            if (committed_transition_required(root, base=base, head=head, changed_paths=subjects)
                    and not v3_independence):
                blockers.append("delivery obligation changes require a verified v3 transition")
        except (ApprovalError, GitScopeError, ValueError, KeyError, TypeError) as exc:
            blockers.append(f"delivery obligations are invalid: {exc}")
    for f in sorted(subjects - covered):
        blockers.append(f"changed file not covered by any complete lifecycle: {f}")

    return AttestationVerdict(
        ok=not blockers,
        blockers=blockers,
        subjects=sorted(subjects),
        covered=sorted(covered),
        attestations=validated,
        attestation_paths=validated_paths,
        independence=v3_independence,
        gate_bypasses=v3_gate_bypasses,
        policy_basis=policy_basis,
        delivery_decisions=delivery_decisions,
    )




# --------------------------------------------------------------------------- #
# HG-12 cut 1: review-independence disclosure (substrate, NOT enforcement)
# --------------------------------------------------------------------------- #


def independence_for_attestation(att_path: Path) -> dict[str, Any]:
    """Read an attestation file tolerantly and derive independence.

    Tolerant parse (warn-equivalent skip of malformed lines, never raise) so the
    non-failing disclosure path can never crash an otherwise-passing
    ``attest verify`` — mirrors the reducer / ``check_attestation`` policy.
    """
    events: list[Event] = []
    lines = att_path.read_bytes().decode("utf-8").splitlines(keepends=True)
    for raw in effective_event_lines(lines):
        s = raw.strip()
        if not s:
            continue
        try:
            events.append(parse_event_line(s))
        except EventSchemaError:
            continue
    return derive_independence(events)


# --------------------------------------------------------------------------- #
# Gate-bypass disclosure (escape-hatch hardening, Part C) — merge blocker
# --------------------------------------------------------------------------- #


def gate_bypass_for_attestation(att_path: Path) -> dict[str, Any]:
    """Read an attestation file tolerantly and derive gate-bypass disclosure.

    Mirrors ``independence_for_attestation``'s tolerant parse: malformed lines
    are skipped (never raise) so the merge-gate blocker can never crash on a
    partially-corrupt attestation.
    """
    events: list[Event] = []
    lines = att_path.read_bytes().decode("utf-8").splitlines(keepends=True)
    for raw in effective_event_lines(lines):
        s = raw.strip()
        if not s:
            continue
        try:
            events.append(parse_event_line(s))
        except EventSchemaError:
            continue
    return gate_bypass_disclosure(events)
