---
change: 2026-09-20-rejected-code-resubmission
stage: plan
---

# Re-submit code after a rejected review

## Evidence and cause

TapScribe Change 2026-08-17-agent-automation-contract at f67bbc2 has a
CODE_REVIEW_REJECTED lifecycle, a frozen code subject from bef9f866, and a
passed verification for code:c3fbfa391553df1c964e8fad6cfa1937982e19a69a5f3e3d42f1dd384e34aa27.
Event replay agrees with state.yaml. Verification is informational and must not
silently replace the review subject. The CLI blocks both done and reopen in the
rejected state, despite the existing implementation_invalidated transition.

## Commitments

- C1: Allow implementation reopen with a recorded reason from CODE_REVIEW_REJECTED,
  using the existing strict implementation_invalidated event and transition.
  Preserve effective plan approval and historical evidence; invalidate the prior
  code and verification projections through the existing reducer. Keep all other
  CLI state restrictions and approval checks, especially PLAN_REJECTED.
- C2: Keep done as the explicit verification and code-freezing boundary. Preserve
  exact-subject review import and append-only history. Never promote verification
  to review approval or edit persisted events/state manually.
- C3: Add CLI and real-Git lifecycle regressions for reject A, commit B, verify B
  while A remains frozen, reopen, failed verification, successful done, reject
  stale A evidence, and import exact B approval to READY_TO_MERGE. Preserve the
  prior event prefix and approval. Update actionable recovery guidance/docs.
- C4: Run focused tests and full verification, then exercise the supported recovery
  on the matching TapScribe worktree, using retained genuine review evidence only
  if its exact subject still matches. Report remaining evidence or validation
  limitations without skips or fabricated approvals.

## Scope and contract impact

Expected files: cli/implementation.py, cli/done.py, gates/decisions.py,
tests/unit/cli/test_implementation.py, tests/integration/lifecycle/test_plan_authority.py,
docs/state-machine.md, and this plan. Adjust supporting tests/docs as needed within
these commitments. No new events, no transition-matrix or reducer migration, no
new dependencies, no TapScribe product edits, no deployment/merge.

The CLI admission contract expands to an already supported core transition.
Rejected code may still be edited immediately, but must explicitly reopen and
run done before importing evidence for a changed subject. Existing historical
same-subject rejection/re-review remains readable and supported.

## Validation

First reproduce the new CLI regression failing on the old code. Run lifecycle,
implementation, done, review and gate tests; then ruff, mypy, full pytest,
decision check, doc check and harness verify. Retain exact external plan and code
review conclusions according to .harness/review-recognition.yaml before their
respective lifecycle transitions.
