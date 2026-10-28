# Independent Codex candidate code review 01

Decision: **reject**.

Reviewer: independent Codex subagent `/root/codex_context_code_review`, invoked by the implementation agent outside Keepsail core under `codex-subagent-review/v1`.

Exact object: `code:35235a73ebf09c380d71495e47959a1b18643c5d843e76ee1fa81ae16346b90d`.
Change: `2026-10-27-harness-knowledge-context`.
Commit: `ff221d4dd8c7dee2abc5556ae085cf83b42bed2d`.
Base: `bb69097dffee4e782568da4ea688d06b5773cbf4`.
Effective approval: `approval:2026-10-28-harness-context-codex-revision-plan-01-84705107`.

This is an exact source-candidate preflight. It is not final code lifecycle authority, knowledge recognition, an impact disposition or real desktop acceptance.

## Blocking finding

**[P2] Make native acquisition complete within the registered callback budget.** At `src/keepsail/daemon/context_hook.py:331-332`, the last observed page synchronously calls `_record_acquisition` once for every supplied knowledge version. Each call reloads the ledger and uses the strict native transaction writer. The Codex registration still routes PostToolUse through `_hook_entry` (`src/keepsail/adapters/agent/_settings_merge.py:158-165`), whose timeout is 10 seconds (`:55-56`). On an isolated copy of this exact committed project and the current retained ledger, the real native final-page observation took **16.875 seconds** for the two actually applicable versions. This measurement excludes a fresh hook-process/PowerShell startup, so those costs cannot make it fit the configured limit. The preceding page observations took 0.187-4.203 seconds. After successful full observation, the selected edit gate took 6.703 seconds in a separate read-only probe; that particular gate call did not exceed the budget.

This is a current source/workload integration defect, not merely lack of evidence that the desktop supports the candidate callback shape. A host enforcing the installed 10-second limit can interrupt the acquisition work before all native observations commit, leaving complete outer page receipts but incomplete native per-version acquisition and a not-ready edit gate. The current reminder also suppresses itself on complete outer pages without testing those native acquisitions, so this failure can be quiet until an edit is attempted. The exact number of writes completed before a real host timeout is not asserted here; I did not run a desktop session or kill an actual host hook.

Correct the bounded acquisition path and its retry/reminder behavior before installing this candidate for actual A/B. Demonstrate the correction at the current ledger/constraint size and under the chosen explicit hook deadline, retaining separate page and native observation facts. Keep exact validation/CAS/append-only semantics. The frozen revision line 106 explicitly requires recording the 10-second hook budget and says not to enlarge a budget to hide failure. This review does not invent an absolute product rule forbidding every explicitly justified future timeout change, nor prescribe a new batching API/state machine; any selected deadline change must be honestly justified and measured rather than presented as the original budget passing. Add a meaningful bounded-process regression; the tiny-ledger callback fixtures currently miss this case.

## Review work

I validated the retained code subject, regenerated the native subject and compared all **52 manifest rows**, resolved base, approval and knowledge basis. They match this HEAD. I read the normative architecture, approved revision and retained prior-plan obligations, relevant ratified append-only/single-gate/path-allowance decisions, and the in-scope implementation changes across projection, lineage, entry/startup binding, return decoding/receipt validation, declaration recovery, native supply/acquisition, CLI/hook dispatch, pure gate, settings transactions/opt-out, Windows command quoting and writer cleanup. I examined the associated unit and isolated process tests and the dated documentation/evidence claims.

The main preserved boundaries are explicit Change binding, fresh entries after resume/compact, immutable original approvals/old receipts, separate Codex raw provenance, incomplete/unknown/failed returns remaining unobserved, all patch/move paths going through the same pure gate, local knowledge dependency checks, and no knowledge-derived work approval. The writer change only retries cleanup of this transaction's own staged file on selected Windows access/sharing errors before append; it does not replace/truncate the event log or bypass strict validation. Settings opt-in is structurally recognized, opt-out preserves unrelated current settings, and there is no automatic hook trust. I found no additional blocking defect in those inspected paths.

The implementation agent reported an affected run of 318 passed/4 skipped and historical recovery run of 37 passed. Those reports and the source/test fixtures are not actual desktop callback evidence. The full native verify was running independently; this review does not claim its outcome. Review reproduction artifacts are `review_codex_budget_probe_01.py`, `codex-review-budget-probe-01.json`, `codex-review-budget-gate-01.json` and isolated workspace `isolated-review-codex-budget-01`, all outside the governed checkout. The probe copied the committed project and retained log, then used supplied fixture callbacks and native operations only in that isolated workspace. No real user session was created, and the original checkout/ledger was not mutated by this review.

## Acceptance limits

Real desktop callback shape/completion, hook activation/trust and timeout behavior, root versus child attribution, user-operated A/B development and separately recognized v2/disposition remain explicitly pending. Their absence is not the reason for this source-candidate rejection. A successful process fixture cannot discharge H7. No conclusion here claims cryptographic producer identity, semantic understanding/compliance, all-tool interception or cross-repository authority.

Preserve this reject, fix under the effective approval if commitments/restrictions remain covered, then freeze and independently review the new exact candidate. Do not import this preflight as final code approval or mark the Change complete. No source, plan, policy, event/state/review records, hook installation or trust was changed during this review.
