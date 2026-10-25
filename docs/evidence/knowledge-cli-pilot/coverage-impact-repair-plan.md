# Proposed repair: stable impact disposition across irrelevant coverage updates

Status: proposal only, awaiting explicit owner authorization. This is not an
approved source Change, knowledge recognition, or replacement impact disposition.
The current pilot authorizes documentation/evidence only. It stays
`IMPLEMENTATION_IN_PROGRESS`; no final verification/review/attestation is claimed.

## Actual problem and evidence

At HEAD `781d8a83fa6133f13bab096681ad8555cc7588fe`, the owner-selected continue
with v2 resolved impact
`8bfc3023b83ae44d1b52bae64e83e2f84992985c6cf39081bde748bd3d097d3b`.
Native actual-coverage recording then added documentation/evidence paths without
changing approval, commitments, effective versions, applicability or challenges.
Despite a fresh exact v2 delivery, native knowledge check now exits 2 with pending
impact `ebe2a74ab72f23bdf2fdc543e06e7d74cfb4ffa9630f11decbcbce3c51957959`.

`coverage-impact-diagnosis.json` retains a read-only differential using the same
validated ledger/policy and only the two different path sets. It reproduces the
resolved-to-pending change. `coverage-impact-repeat-check.json` retains the
repeated native failure. No isolated record was imported into the real ledger.

The [independent diagnostic review](coverage-impact-independent-review.md) confirms
the cause with a one-unrelated-path differential and identifies the checkpoint
compatibility constraint. It is a diagnostic review, not plan/code approval.

Root cause: `core/knowledge.py::_context` unions estimated scope, actual coverage
and current code manifest. `_view::impact_basis` hashes that entire mutable path
set; historic supplies are reprojected into new impact IDs on every read.
Disposition lookup uses the resulting exact ID. A within-approval addition can
therefore orphan a real owner conclusion even for this repository/Change selector,
which contains no path condition. An exact delivery refresh cannot repair it.

## Proposed bounded implementation contract

1. Establish one shared impact projection/validation model for the strict writer,
   ledger replay, current checks and pure-Git checkpoint validation. Preserve an
   exact immutable trigger subject and its contemporaneous approval context.
2. Separate that historical trigger identity from current delivery coverage and
   applicability/dependency evaluation. An irrelevant in-bound path addition must
   not recreate the same version-transition judgment. Delivery basis must still
   bind the actual current context and require fresh delivery when it changes.
3. Real knowledge/applicability changes and challenges must still expose new
   unresolved obligations. Path-selector matching changes, unknown context and
   global/unknown dependencies must remain fail-closed. No version-only or
   approval-only fallback may stand in for an exact recognized disposition.
4. Retain validated trigger context/subject for new triggers in the native event
   evidence and checkpoint representation. Scope/coverage history is not generally
   reconstructible from a knowledge-only checkpoint, so do not infer historical
   paths from today's state or simply select the latest delivery.
5. Preserve existing exact events, IDs, receipts, conclusions and original v1/v2
   text. Validate legacy identity against retained evidence, not a newly invented
   digest. For the initial bounded compatibility path, enumerate validated same-Change
   historical delivery contexts, recompute the complete legacy impact/basis, and
   require exact equality with the recognized impact object and subject ID. Require
   demonstrably path-insensitive relevant selectors/dependencies and preserve all
   current applicability/dependency checks. Never select only the latest delivery.
   Later knowledge/state/applicability/policy changes must break that exact proof.
   If no exact context is provable or relevance is path-sensitive/unknown, retain an explicit
   blocker and require a separately authorized native append-only context-recovery
   binding; do not auto-promote a guessed context or hand-edit old evidence.

The compatibility branch must be settled in the separately reviewed implementation
plan before source changes. The pilot's retained original context/impact evidence
is available, but this proposal does not assert that all historical ledgers have
sufficient context. Do not adopt a broad policy migration or change work commitments
as a side effect of this repair.

## Required regression and acceptance

- First reproduce the full sequence through native CLI in an isolated workspace:
  approved work, effective/supplied v1, recognized v2, exact owner disposition,
  unrelated actual-coverage addition, new exact delivery, then knowledge check.
  The current implementation must fail that regression before the repair.
- After the repair, the same recognized conclusion must remain traceable and
  resolved, while omitting refreshed delivery must still fail. Test both this
  non-path selector and global constraints; exercise multiple historical supplies.
- Independently test changed path applicability, genuine subsequent version or
  recognized applicability changes, global/path challenges, unknown dependencies,
  and subsequent approval epochs. They must not reuse an unrelated old conclusion.
- Test exact legacy evidence retention and unavailable-context rejection. Tampered,
  stale, conflicting, missing, failed, skipped and unknown-issuer inputs stay rejected.
- Verify the same behavior from committed Git attestations, with immutable trigger
  approval and exact subject verification, not merely mutable local replay.
- Run targeted knowledge core/lifecycle/attestation regressions, required decision
  and doc checks, then native full verification, recognized independent exact plan/
  code review and attestation validation. Recheck the real pilot after the governed
  repair is delivered through the appropriate trusted validation path.

## Authorization requested

Approve the bounded repair/test plan and one separate execution chat/Change for
this runtime defect. The new Change must receive its own exact recognized plan
approval before source edits. No new source work, additional chat, repeated owner
disposition, merge, policy bypass or retrospective evidence rewrite is authorized
by the existing pilot continuation alone. Return to the pilot to complete P9 only
after the blocker is actually resolved and its current obligations are satisfied.
