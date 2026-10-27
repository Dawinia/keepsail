---
change: 2026-10-27-historical-change-recovery
stage: plan
---

# Recover verified historical merged Changes

The owner confirmed the retained recovery plan in this independent chat on
2026-10-27. This authorizes the bounded repair and subsequent local recovery;
it does not authorize merge/publication, rewriting history or product redesign.

## Commitments

- R1: Add an explicit `change recover` dry-run/apply protocol for a historically
  merged Change. Bind an immutable Git attestation, repository, exact PR/merged
  object, historical recognition, effective approval, verification and complete
  code subject. Verify the merge through gh, including squash/single-parent
  commits. Do not accept arbitrary local JSONL as authorization. Missing proof
  fails closed. This first interface deliberately handles verified merged history
  only; it cannot grant authority for continuing unmerged implementation.
- R2: Preserve the complete original evidence and source order. Require the
  target Change's effective history to be an exact prefix of the source, with
  globally unique event IDs and exact-content deduplication; reject conflicts,
  malformed/unknown target events, divergent order, missing predecessors or
  unsupported knowledge dependencies. Other Changes and knowledge remain intact.
  Resolve original authority against immutable historical refs, never today's
  policy. Do not manufacture historical knowledge delivery or reapprove semantics.
- R3: Retain one versioned recovery event containing the original source bytes,
  immutable provenance, missing historical events, merge fact and recovery time.
  Replay its historical events in source order followed by the recorded merged
  event through the existing fixed transition matrix. This complete envelope is
  the log authority; no external cache is needed to recover its meaning. A full
  envelope becomes visible together, without exposing partial restored approvals.
  Preserve original event identities/timestamps/payloads; distinguish recovery
  time from actual mergedAt. Archived history never authorizes new implementation.
- R4: Shared writer validation must validate this protocol, not rely on a CLI
  bypass. Use the existing events lock and compare target revision under lock.
  Exact retries are no-ops; conflicting provenance/merge SHA rejects. A durable
  pending append journal supports completing only the exact unwritten suffix
  after process interruption, without rewriting/truncating previous bytes. Normal
  writers refuse pending recovery; malformed/changed prefixes fail closed. The
  journal is transport recovery, never state authority. No cross-worktree atomic
  transaction is claimed: finish each independently and report partial progress.
- R5: Keep ordinary on-merge/current knowledge checks intact and repair its
  misleading generic READY_TO_MERGE hint. Add failing regressions before fixes:
  old checkout/new trusted refs, prefix restore, exact subjects, unrelated record
  preservation, source/issuer/SHA/manifest tampering, unknown events, duplicates,
  conflicts/order/CAS, interruption/resume, concurrent applies, idempotence and
  main/recovery-worktree parity. Existing new-work knowledge gates still reject.
- R6: Back up both original ledgers/state/attestations and original review files
  outside the repositories before actual recovery. Preserve all unrelated files,
  unknown historical warnings and the original recovery worktree. Obtain real
  independent exact plan/code reviews, record actual scope/assessment, run native
  done and configured checks, and record explicit source/unmerged boundaries.
  Apply the verified protocol to both workspaces only after verification/review.
  Final states must be ARCHIVED at the actual merge SHA with original evidence
  traceable; repeat application must emit nothing. Never merge/publish automatically.

## Scope and sequence

Use existing approval/manifest/recognition/transition primitives. Add a small core
recovery module and CLI surface; change events/reducer/writer/validation only as
needed for the envelope and append recovery. Update relevant CLI/lifecycle docs
and native generated attestation. Reconcile affected ratified decision anchors
through CLI without editing their body. No dependency, policy, architecture,
old-plan or unrelated delivery change.

Estimated files: src/keepsail/core/{recovery,events,reducer,writer,emit_validation,
transitions}.py; src/keepsail/cli/{change,on_merge}.py; relevant tests and docs.
Within-approval additions use implementation record. Reuse engineering attestation
verification from orchestration if useful without importing upper layers in core.
Freeze this plan, obtain recognized independent review and import its exact
conclusion before source edits. Deliver this Change's real constraints and start
implementation. Then red regressions, implementation, targeted/full configured
verification, exact code review, backup, dry-run and sequential local recovery.

## Acceptance boundaries

Original baseline remains a four-document publication delivered by PR126. This
repair implements continuity/trace recovery without claiming all C1-C6 complete.
The first recovery version rejects streams requiring cross-Change knowledge
closure it cannot verify, rather than silently importing unrelated knowledge.
The historical PR's retained recognition must be supported and valid; missing
recognition is not grandfathered approval. Local recovery results do not prove
package publication, remote deployment or future compatibility with older readers.
