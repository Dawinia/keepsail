---
change: 2026-11-09-done-verification-preflight
stage: plan
---

# Completion preflight and verification progress

## Objective

Avoid running expensive checks when completion's current knowledge prerequisites
already fail, and expose actual check start and finish to a waiting operator.
Preserve the product architecture's C3, C5 and C6 boundaries and exact evidence.

## Commitments

1. After state, approval, actual coverage and verification configuration checks,
   and before dispatch, `done` checks the read-only knowledge prerequisites for
   `implementation_complete` using the same effective scope and predicate as the
   strict writer. Reuse the existing validator or extract a minimal shared function.
   Preserve inactive policy, empty delivery, applicability, unresolved impact and
   valid executing-adjustment semantics. On failure give an actionable next step;
   do not run checks or emit verification/completion events, deliver knowledge, or
   claim acquisition. Do not preflight the verification prerequisite itself.
2. Keep the strict completion writer's full, fresh validation after verification;
   changes to delivery, coverage, authority or subject during a run must still fail
   closed under the existing rules. Preserve legacy `--skip-verify` semantics.
3. In human-readable `done`, report each actual check start and finish on stderr,
   including its ID, known timeout where appropriate, real status and elapsed time.
   Add optional notifications at the existing execution seam; queued tasks must not
   appear started. Preserve parallel scheduling, result order, fail-fast, captured
   I/O, archive, exit status, quiet behavior and JSON stdout/envelope. This change
   does not change `verify` CLI presentation.
4. Add fast targeted regression tests through the real `done` entry for absent or
   stale delivery, no dispatch or events, valid delivery, and a changed basis during
   execution; cover inactive policy and the valid adjustment exception. Test actual
   start/finish notifications with controlled short tasks, parallel queueing, failure
   and timeout, and quiet/JSON compatibility.

## Boundaries and validation

Use the existing runner, task model and execution loop. Primary expected files are
`src/keepsail/cli/done.py`, `src/keepsail/core/knowledge.py`,
`src/keepsail/sensors/verification_runner.py`, related tests and this plan; record
actual coverage and within-approval adjustments. No verification cache, test selection,
quick/full modes, review-policy changes, reviewer orchestration, streaming subprocess
logs, or DSH harness waiting changes. Do not modify governance by hand.

Run targeted tests, lint/types and decision/document checks while developing. Freeze
and commit the complete implementation, record actual assessment and coverage, then
run the configured full verification on the final subject via `done`. Obtain and
import independently produced recognized reviews for exact frozen plan and code
subjects. No merge is authorized by this plan.
