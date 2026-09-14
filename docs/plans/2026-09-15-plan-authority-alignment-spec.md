---
change: 2026-09-15-plan-authority-alignment
stage: design
---

# Post-cutover guidance and report alignment

## Authority and scope

This Change follows the enabled external-evidence contract on main
`86d2d842b99480e2e1ee02ac66510c90c55cdcda`. It adopts the confirmed obligations in
[product foundations](../product-foundations.md). The archived cutover's original
specification/plan are historical background, including their disclosed skips;
their first-cutover exception does not authorize this Change.

## Commitments

- C1: Current README, usage documentation and generated agent instructions explain
  recognized external plan/code evidence and approval-bound implementation coverage.
  Removed commands may appear as explicitly retired reference entries or historical
  records, never as recommended current steps. Regenerate managed AGENTS content.
- C2: Reports distinguish historical round starts/issued run records, recorded run
  failures, imported old results, imported external conclusions, explicit approve/
  reject decisions, historical skips and authorization events. A frozen/issued run
  is not proof of a process invocation; a failure can record intentional nonexecution.
  New evidence never implies a run count. Counts describe recorded events/objects,
  not current approval applicability or independent human actions.
- C3: Sum only recorded nonnegative finite usage/cost fields. Unknown totals are
  null/unknown, explicit zero remains zero, partial data is labelled partial with
  coverage numerator/denominator. Denominators count distinct observable legacy run
  or external evidence records, not invented external invocations. Coding-agent and
  unrecorded external costs remain unknown. Preserve the existing named token-key
  rules; partial component sums are recorded subtotals, not complete usage claims.
- C4: Deduplicate event replay by identity and repeated imports by Change plus run/
  evidence identity, before date filtering; separate starts/failures/results for the
  same run without adding usage twice. Distinct authorization IDs remain distinct.
  Keep original ledger bytes and historical meanings. Superseded/historical evidence
  stays visible as imported conclusions, not extra active approvals. Never interpret
  a historical skip, failed closure, empty evidence or lifecycle mirror as approval.
- C5: Findings metrics remain explicitly limited to structured historical code-review
  finding IDs and dispositions. Resolved is a recorded disposition, wontfix is not
  necessarily a false alarm. Opaque new review prose is not parsed into defects.
  Verification/CI failures are not independent defect counts; remove total-value
  judgments inferred from these partial metrics and add no score.
- C6: Exercise a new fixture within approved commitments in an isolated repository:
  record assessment/coverage, actually execute verification and complete with the
  same plan approval. Exercise failed/empty external review and retired commands
  without creating core rounds, retry authorizations or approvals. Preserve plan/
  code reviews, exact subjects, real verification/CI and attestation through merge.

## Non-goals and escalation boundary

No reviewer orchestration, budgets, persistent skips, cost platform or migration
framework. Keep historical readers unless a reachable obsolete execution path is
proven; only a minimal correction within these commitments is permitted. A material
authority-contract defect requires a minimal reproduction and impact assessment
before revising this plan. Do not edit ratified decision bodies, reopen archived
Changes, advance product-baseline, or touch unrelated untracked files.

## Acceptance evidence

1. Historical issued run + failed run/closure without imported result: visible
   failure/issued counts; unknown token and money coverage, including brief output.
2. Only external evidence: imported decision/process/issuer/subject visible, unknown
   invocation count, usage only if explicitly present; lifecycle mirrors add nothing.
3. Mixed historical and external records, repeated imports, replay, skips, missing/
   partial/zero/invalid usage and repeated authorization bodies with distinct IDs:
   correct identities, source attribution, coverage and window behavior.
4. Current instructions and generated surfaces agree with live CLI behavior;
   historical documents are retained without becoming current onboarding advice.
5. Isolated fixture addition completes real checks without another plan approval.
6. External failure/empty result and retired commands emit no automatic orchestration
   or approval events. These are behavioral tests, not mocked success markers.
