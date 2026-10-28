# Independent Codex candidate code review 04

Decision: **approve**, for this exact source/test candidate only.

Reviewer: independent Codex subagent `/root/codex_context_code_review`, invoked by the implementation agent outside Keepsail core under `codex-subagent-review/v1`.

Exact object: `code:b8ab9e7f8d0d307ea50344c36be45cca2385df57ddf0ee2fb26b77cbfe1a42dd`.
Change: `2026-10-27-harness-knowledge-context`.
Commit: `4189c4d9122318caf55720892ddf1a3b3a6922fe`.
Base: `bb69097dffee4e782568da4ea688d06b5773cbf4`.
Effective approval: `approval:2026-10-28-harness-context-codex-revision-plan-01-84705107`.

This candidate approval is not successful full verification, final lifecycle code authority, actual host/H7 acceptance, knowledge recognition or an impact disposition. It must not be imported as final code approval while those obligations remain incomplete.

## Exact review and findings

No blocking source/test finding in this exact candidate. I validated the retained subject and regenerated its native equivalent, confirming the exact commit/base, effective approval, knowledge basis and all **63 manifest rows**. Git comparison confirms product source under `src/`, `.harness/verification.yaml`, and the dedicated knowledge-policy bootstrap integration suite are unchanged from the previously reviewed product correction at `e85b320`. The source-candidate findings and runtime limits from review 02 remain applicable. The 10-second hook and 1200-second verification limits remain unchanged.

The only new test change is module-local preparation for `tests/unit/core/test_knowledge.py`: one template is built through the unchanged native Workspace constructor, then each scenario receives copied files/Git/log state and a deep-copied helper with its root rebound. The fixture is module-scoped/function-scoped as appropriate, not autouse or shared mutable scenario state. Unlike the context fixture, this module retains the original default recognition policy and needs no policy-function monkeypatch. AST comparison against `d4ccfbe5` confirms every test body and decorator, including assertions and parametrizations, is identical; the Workspace class itself is also identical. All forty collected scenarios therefore retain their prior protocol operations and assertions. No skip, test-selection or product-check rule was changed.

I inspected the within-approval H8 assessment, the dated README failure disclosure and the retained review 03 originals. Both copied original text and structured record match the external originals as text. The change retains the previous failures and narrows the claimed result to fixture preparation, without reporting a whole-suite pass or installation.

## Independent fixture isolation check

A separate probe against this exact HEAD passed in **4.297 seconds**, retained in `codex-review-knowledge-fixture-isolation-04.json`, with isolated directories under `review-knowledge-fixture-isolation-04/` outside the governed checkout. It prepared the native module template and two copied workspaces, then submitted a native knowledge proposal only in the first copy. The second copy and template retained their original event-log bytes. Helper counters, review dictionaries and CliRunner objects were independent; Git identified each copied directory as its own checkout. Both copies' trusted policies matched the unchanged default policy with only `test-observer` in observation issuers; no fixture-policy function was replaced or leaked. The second copy retained its original empty applicable-constraint set. This probe changed only its isolated fixtures, not the actual project or any real user session. I did not repeat the forty-case module or full suite.

## Failed verification and diagnostic history

The implementation agent's prior attempt 03 failed with pytest INTERNALERROR when the external diagnostic logger called `Path.open` during a test's global disk-full fault injection. The earlier review's source inspection of that observer did not establish compatibility with fault-injection tests; the actual failed run corrects that assumption. The retained `codex-diagnostic-plugin-failure-03.json` reports pytest exit 1 at 827.748 seconds. This is a diagnostic-plugin failure, not actual disk exhaustion, and is not a passing product verification. The observer has been removed from formal reruns.

The subsequent original-environment attempt at `d4ccfbe5` also timed out at **1200.424 seconds**; it remains a failed verification. The new fixture change's reported forty-case pass in 151.98 seconds is a separate scoped result, not evidence that the entire project now fits its deadline. Native uninstrumented full verification of this exact `4189c4d` candidate was running independently during review; I do not claim its outcome. A current exact passing verification is still required before the plan's authorized local installation step. No installation or completion is justified by this candidate review alone.

## Remaining boundaries

Actual then-current desktop binary and callback shape/completion, root versus child attribution, hook installation/trust and timeout behavior, user-operated A/B development, current-entry recovery, separately recognized v2/disposition, daily operating cost and final exact review/import/attestation remain required. Source review, copied fixtures, older passing subsets and repeated failed full attempts cannot substitute for H7 or successful whole-candidate checks. Preserve the prior reject, original approvals and knowledge versions with their recorded meanings.

This approval authorizes no trust bypass, global configuration change, new user session creation, publication, merge or release. It asserts no semantic understanding/compliance, cryptographic producer identity, all-tool interception, universal recall or cross-repository authority. I made no actual-repository source, governed-plan, policy, ledger/state/review-record, hook installation or trust changes. The tracked checkout and HEAD remained frozen throughout review.
