---
change: 2026-10-25-knowledge-policy-bootstrap
stage: plan
---
# First knowledge-policy delivery

The owner confirmed the diagnosis and implementation proposal in this chat with
“开始” on 2026-10-25. This authorizes implementation of this plan, subject to the
existing recognized plan/code review. It does not authorize merge or activation.
The normative source remains `docs/product-architecture.md`.

On 2026-10-25 the owner additionally answered “确认调整至 1200 秒并继续” to
the concrete proposal changing only the full pytest check's execution budget
from 600 to 1200 seconds. This revision adds P5; P1–P4 and all other restrictions
remain unchanged. It requires a new recognized plan conclusion before that edit.

## Problem and commitments

`load_policy` currently treats the presence of a first candidate as an error when
the trusted base has no policy. Both plan/code subject generation and lifecycle
preconditions call it, so delivering the first policy requires that policy to have
already been delivered. Explicit-base attestation ignores that candidate and thus
has different semantics. Current regression fixtures begin with activation in main.

- P1: Separate trusted effective policy from validated candidate configuration at
  the shared core seam. A valid first candidate may be delivered through the
  ordinary approved Change; it grants no knowledge authority. Malformed candidates,
  unavailable trusted Git, corrupt ledgers and unauthorized knowledge evidence
  fail explicitly. No bypass flags or replacement trusted base.
- P2: Read output for a valid first candidate retains `coverage=not_recorded` and
  discloses candidate status/digest, with exit 0. Knowledge writes still fail
  without effective trusted activation. No fabricated supply/acquisition/checkpoint.
- P3: Local subject/precondition/export and committed attestation validation agree
  for the same trusted base. CI validates candidate configuration from its target
  Git commit, not mutable worktree files. Candidate remains in the complete code
  manifest, actual coverage and exact reviewed subject. Preserve strict activated
  policy deletion/replacement rejection and checkpoint/basis checks.
- P4: Document first delivery, owner-controlled trusted-base activation, historical
  compatibility, repository-wide protocol impact and the limits of this repair.
- P5: Change only the pytest check's `timeout_seconds` from 600 to 1200 in
  `.harness/verification.yaml`, preserving the complete test command, `must_pass`
  and every other check. Re-run normal done under the new approved budget and
  bind verification, code review and attestation to the exact current subject.

## Boundaries

No real `.harness/knowledge-recognition.yaml` is installed. No merge, publication,
policy activation, ledger/state/approval/receipt edits, historical migration, or
ratified decision body edits. Do not reopen archived explicit-constraints.
Preserve pre-existing test_knowledge_delivery.py working-tree state, .superpowers/
and docs/research/. Use an independent bootstrap regression file.

The first candidate is validated but not authoritative. Owner/process labels and
ordinary plan/code approval do not independently confer knowledge authority.
Existing active-policy replacement/deactivation remains rejected; a general policy
evolution/cutover protocol needs separate design. Constraint selectors do not limit
repository activation: other Changes still require delivery even for an empty
constraint set. Do not add per-Change activation or skip empty-set delivery.

Historical subjects remain unchanged. A later trusted-base activation governs
subsequent actions, with new deliveries as required, rather than retroactively
inserting knowledge basis into the first policy's delivery subject.

## Implementation sequence and estimated files

1. Add failing regressions at the real CLI/subject/attestation seam for both first
   candidate timings (before plan submission and during approved implementation).
2. In core/knowledge.py reuse schema/digest validation while resolving effective
   authority only from the trusted base. Keep existing public callers working;
   add the smallest shared candidate resolver/status seam needed for committed
   validation and read output. Distinguish genuine absence from Git failure.
3. Adapt cli/knowledge.py read presentation and engineering/attestation.py committed
   candidate validation; leave approval.py callers unchanged if the core fix covers
   them. Pass the actual attestation target commit to candidate validation.
4. Update docs/knowledge.md. Record any within-approval file additions/adjustments
   and actual coverage via implementation record; no manual evidence construction.
5. After this revision's recognized approval, make the single P5 budget change.
   Retain the original failed 600-second run. Do not infer success from a longer
   deadline: actual complete execution and normal done must pass.

Estimated files: core/knowledge.py, cli/knowledge.py,
engineering/attestation.py, docs/knowledge.md,
tests/integration/lifecycle/test_knowledge_policy_bootstrap.py,
tests/unit/core/test_knowledge.py and relevant existing attestation tests only if
necessary. New plan and exact retained external review evidence are delivery files.
P5 additionally includes `.harness/verification.yaml`. Actual P3 fixture coverage
also includes tests/unit/core/test_approval.py, tests/unit/cli/test_attest.py,
tests/integration/cli/test_status.py and
tests/integration/lifecycle/test_plan_authority.py: these establish real inactive
trusted main commits while retaining their original behavioral assertions.

The full current-source diagnostic with CI=1 and the native project toolchain
completed 2365 passed, 22 skipped, 9 warnings in 740.05s. The unchanged 600-second
formal run timed out at 600395ms and emitted no implementation_complete. Timings
show real Git/process/lifecycle tests, including the two new first-delivery
scenarios at 14.55s and 14.34s; no tests were excluded to obtain the passing result.
The new budget provides execution headroom; it is not a product performance
acceptance result or permission to hide a stalled/failed check.

## Validation and delivery

Run each new regression red before implementation, then green. Isolated fixtures
may provide explicitly test-only review evidence; real Change reviews come from
the owner-recognized independent Codex subagent, retained with exact subject,
explicit decision, original conclusion and provenance, imported normally.

Required scenarios:

- Valid candidate before plan ready, and candidate added during approved work:
  plan/implementation/actual verify/done/code review/export/explicit-base Git
  validation complete without activating knowledge. Manifest includes the policy.
- Candidate reads show not_recorded; propose/import/deliver cannot gain authority.
- Invalid schema/digest/requirements, unreadable candidate, missing/invalid Git base
  fail without appending lifecycle evidence. Same base and candidate produce
  consistent local/CI results; worktree corruption cannot alter committed CI result.
- Forged knowledge events, basis or checkpoint under an inactive base are rejected.
- In a temporary fixture only, advance trusted main after normal delivery: new work
  must satisfy delivery; earlier subjects remain unchanged. Activated deletion,
  disablement/replacement and missing/corrupt ledger stay rejected.
- Run existing knowledge, approval and attestation regressions; normal `done`
  verification, decision check --changed, full decision check and doc check. Retain
  actual results and platform limits. No claims of CI success without a CI run.

Freeze each reviewed subject in a commit. Do not edit while review is pending.
Batch code findings through implementation reopen and re-review current subject.
Finish with exact code review and committed attestation; do not merge or activate.
