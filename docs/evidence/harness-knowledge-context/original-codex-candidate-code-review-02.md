# Independent Codex candidate code review 02

Decision: **approve**, for this exact source candidate only.

Reviewer: independent Codex subagent `/root/codex_context_code_review`, invoked by the implementation agent outside Keepsail core under `codex-subagent-review/v1`.

Exact object: `code:f194cc81601610ff01db3b56bc0d5947df3a89facb8bc99105822430a52e4480`.
Change: `2026-10-27-harness-knowledge-context`.
Commit: `e85b320c2c7efe91c70761013c30e504d8046383`.
Base: `bb69097dffee4e782568da4ea688d06b5773cbf4`.
Effective approval: `approval:2026-10-28-harness-context-codex-revision-plan-01-84705107`.

This is a pre-acceptance source-candidate conclusion. It is not final code lifecycle authority, actual host acceptance, knowledge recognition, an impact disposition or completion of H7. Do not import it as final code approval while acceptance is incomplete.

## Finding resolution

No blocking source finding remains in this exact candidate.

The prior reject at `code:35235a73...` is preserved with its original meaning. Its measured final-page hook performed two synchronous native writes in 16.875 seconds against a 10-second deadline. The correction moves those writes out of the Codex PostToolUse hook: the hook validates and retains the actual immutable page returns, then supplies an exact CLI finalization command. The finalizer rechecks the selected Codex entry and current authority, requires every actual returned page, reconstructs the complete returned text, and calls the existing native per-version CAS/append-only operations. It checks entry and authority again after recording. Missing, replaced, wrong-Change or stale material cannot be accepted as current ready context. Old received facts remain retained even when a later authority change requires refresh.

Outer page completion remains distinct from native knowledge acquisition. Until the native writes succeed, the selected edit gate remains unready and the prompt includes the finalization command. Native operation identity makes retries idempotent; no background worker, hash-only acknowledgment, new approval source or lifecycle state was introduced. The original Claude path retains synchronous native recording behavior. The empty knowledge set retains outer receipt evidence and returns `not_applicable` rather than inventing a native knowledge version. The configured hook deadline remains 10 seconds, and the native verification timeout remains 1200 seconds.

## Exact review and validation

I validated the retained subject and regenerated its native equivalent, confirming the exact commit/base, effective approval, knowledge basis and all **55 manifest rows**. I reviewed the complete correction relative to the previously reviewed candidate, together with the new assessment, retained reject, changed guide and tests. The original architectural, frozen approval lineage, four-fact, current/root attribution, all-patch-path, local-dependency, settings preservation and append-only findings from review 01 remain applicable; none is promoted into a stronger runtime guarantee by this correction.

I independently ran the new public hook/CLI regression `tests/unit/daemon/test_codex_context_hook.py::test_cli_finalization_requires_actual_returns_and_prompt_reminds_pending_acquisition`: **1 passed in 12.15s**. This checks that supply alone cannot finalize, actual returned content is required, outer completion leaves native acquisition pending, prompts retain the command, native recording succeeds and retries do not duplicate observations. This is an isolated test, not a real session.

I inspected the implementation agent's bounded-process script `validate_codex_budget_fix_02.py`, its retained raw streams and `codex-budget-fix-process-02.json`. The script is bound to this exact source commit and an isolated copy of the current 8,453,479-byte ledger. It executes the real generated Windows PowerShell hook/CLI commands with supplied fixture callbacks and the registered deadlines. Seven observed-page hook processes completed in 0.890-1.000 seconds under 10 seconds. Before finalization, the edit callback denied in 6.657 seconds and the prompt retained the pending command in 3.828 seconds. Explicit native CLI finalization took 17.969 seconds outside the hook deadline and produced two native observations; the subsequent prompt was quiet in 3.922 seconds and the edit callback allowed in 6.516 seconds. These are retained local process measurements supplied by the implementation agent and inspected by this reviewer; I did not repeat that entire process run or describe it as actual desktop callbacks. The first retrieval also took 19.328 seconds, so the slower overall entry cost has not disappeared.

The full native verify was running independently against this candidate during review; I do not claim its outcome or replace it with the one regression. Earlier working-tree batches, historical Claude results, skips, cancelled attempts and this preflight have separate scopes. The structured evidence validates under the current recognition contract and retains this original review.

## Remaining acceptance boundaries

Actual desktop callback shape/completion, root versus child attribution, installation/trust and host timeout behavior, real user-operated A/B development, current-entry recovery, separately recognized v2/disposition, operating cost and final exact verification/review/attestation remain required. The implementation agent reports a read-only host refresh to desktop runtime 0.165.0-alpha.1.2 while the earlier audit observed 0.164.0-alpha.11.1. I did not independently verify that refresh; real acceptance must bind the actual then-current binary and callbacks. Neither the prior version's offline schema nor a new offline schema is actual host evidence.

This approval does not assert semantic understanding/compliance, cryptographic producer identity, all-tool interception, universal recall or shared cross-repository authority. It authorizes no trust bypass, global settings change, new user session creation, publication, merge or release. Preserve the source-candidate/full-verify/install/actual-host distinctions, and rebind evidence after any real-development implementation changes. I made no source, governed-plan, policy, ledger/state/review-record, hook installation or trust changes. The checkout remained frozen at the specified HEAD throughout this review.
