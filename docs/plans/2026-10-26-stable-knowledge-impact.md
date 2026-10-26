---
change: 2026-10-26-stable-knowledge-impact
stage: plan
---

# Stable knowledge impact subjects

Owner authorized the bounded repair and regression plan in source chat
01a17370-b6fa-7893-a319-7aaba9d8cb8e with “开始”. The awaiting-owner wording
in coverage-impact-repair-plan.md is an earlier snapshot. This plan implements
that scope; independent exact plan approval is required before source edits.

## Commitments

- R1: Repair the shared knowledge writer/replay/view/checkpoint model. Preserve
  immutable trigger subjects and contemporaneous approval independently of current
  coverage. Retain current paths in delivery and applicability/dependency checks.
  Within-bound unrelated additions preserve an exact recognized conclusion; missing
  fresh delivery remains a failure. No pilot-only exception.
- R2: New native import/record operations use a distinctly named v2 knowledge event
  recognized by the new reader and rejected by old readers as an unsupported
  knowledge event. Keep original v1 operation inputs, evidence and policy unchanged;
  the event envelope declares its operation kind and minimum reader/trigger schema.
  Retain strict trigger context snapshots and computed impact subjects, generated
  from actual reduced state under the writer lock and validated by shared replay.
  Checkpoints retain these envelopes. No trusted-policy activation is performed.
- R3: Separate the immutable trigger context/approval from current applicability.
  Preserve subjects only while relevant version/state/current, policy, recognized
  applicability and selector/dependency evaluation remain equivalent. Real version,
  state, applicability, challenge or unknown/path-boundary changes expose unresolved
  obligations. New triggers use their own approval epoch; later reapproval alone
  cannot rewrite an existing trigger. Shared validation must reject missing,
  malformed, inconsistent or tampered snapshots and results.
- R4: Legacy compatibility enumerates validated same-Change retained delivery
  contexts, recomputes the complete original legacy basis/impact, and requires exact
  equality to the recognized impact object and subject digest, including approval,
  policy, version states/current and applicability. Initially admit only provably
  path-insensitive relevant selectors and challenge dependencies. Do not guess the
  latest delivery, match only versions/approval, rewrite records, or manufacture a
  conclusion. Missing context/path-sensitive/unknown relevance fails closed. A new
  recovery operation is deferred and requires separate owner authorization.
- R5: First add and run a failing native CLI regression in isolated Git: approval,
  v1 supply, v2 recognition, exact disposition, unrelated actual coverage update,
  fresh delivery, check. Test global and repository/Change selectors, multiple
  supplies, fresh-delivery absence, path boundary/unknown/dependency changes,
  later versions/applicability/challenges and approval epochs. Exercise legacy
  exact retention, missing/tampered context, CAS/conflicts, issuer/failed/skip
  rejection and pure-Git attestation parity using the repository's existing seams.
- R6: Record actual coverage and within-approval assessment, run targeted suites,
  decision/doc checks and native done with the existing 1200-second pytest limit.
  Obtain genuine independent exact code review, import it, and write/verify Git
  attestation. Recheck the original pilot natively and advance only authorized P9
  stages. Report local source results separately from trusted-base/merge/publication.

## Implementation sequence and boundaries

1. Freeze this plan, obtain independent recognized Codex review and native import;
   deliver this Change's exact current constraints and start implementation.
2. Use existing Workspace/CLI lifecycle fixtures for the red regression. Preserve
   the actual live diagnosis and all original pilot inputs/events unchanged.
3. Implement the envelope and shared snapshot/legacy proof in core/knowledge.py,
   register the event in core/events.py and adapt cli/knowledge.py. Reuse existing
   selector/digest/evidence routines. Snapshot evidence must be sufficient in a
   knowledge-only checkpoint; deriving live paths without retaining them is invalid.
4. Regress and review the final exact code subject. Add tests/docs/evidence files
   through normal implementation assessments when discovered; scope is an estimate.

Expected files: src/keepsail/core/knowledge.py, src/keepsail/core/events.py,
src/keepsail/cli/knowledge.py, tests/unit/core/test_knowledge.py,
tests/integration/lifecycle/test_knowledge_delivery.py, docs/knowledge.md,
this plan and docs/evidence/stable-knowledge-impact/. Existing attestation/reducer
code may change only if needed for the same shared-model obligations.

No reset/restore/clean, source/policy activation, merge, publication, manual ledger/
state edits, repeated equivalent owner disposition, historical Change advancement,
acceptance reduction or verification timeout changes. Preserve .superpowers/,
docs/research/ and .harness/.events-7byibijm.tmp. Rollback of unactivated code is an
ordinary reviewed revert; appended evidence is retained. New event compatibility
is explicit, so old validators must reject rather than silently reinterpret it.
