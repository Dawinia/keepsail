# Independent final-candidate code review 02 (2026-10-29)

Decision: **reject**.

Reviewer: independent Codex subagent `/root/final_codex_context_review`, invoked by the implementation agent outside Keepsail core under `codex-subagent-review/v1`, issuer `codex-subagent`. No further reviewer was started. This is an explicit substantive conclusion, not a skip or pending approval.

- Change: `2026-10-27-harness-knowledge-context`.
- Exact subject: `code:799477163f44c219a0d59122150628089b0f2ea0e7a32a0021dc9c8d90a05b71`.
- Commit: `6dab09ed933ee0cf975d7de555850db6fb1e6816`.
- Base: `bb69097dffee4e782568da4ea688d06b5773cbf4`.
- Effective approval: `approval:2026-10-28-harness-context-codex-revision-plan-01-84705107`.
- Knowledge basis: `4aa78d0198d6d55ec3394fad96849a5050642dfd66b3dafc1fda81052ddb0871`.
- Complete retained subject: `final-code-subject-20261029-02.json`, 152 manifest rows.

The earlier `a88fe1...` original rejection remains unchanged and applies to its different exact object. This review independently targets the new complete subject, with the prior implementation as supporting context.

## Blocking finding

**[P1] Do not convert a failed trusted-ref query into inactive review recognition.** At `src/keepsail/core/approval.py:439-440`, `_contract_base_candidates` catches `GitScopeError` from `for-each-ref` and returns an empty tuple. The shared `_contract_base_refs` feeds that empty tuple into `recognition_contract_active`. When a candidate deletes or disables its recognition policy, the latter can consequently return False without checking a reachable trusted main branch's enabled policy. This regresses the anti-downgrade boundary, even though `resolve_contract_base` separately raises `ApprovalError` on the same empty candidate list.

I reproduced this using actual Git in the isolated external fixture `review-base-errors-02/`, without changing any actual project refs, policy, ledger or source:

1. A committed, valid enabled recognition policy exists on both local main and origin/main. The working-copy policy says `enabled: false`. With healthy refs, `recognition_contract_active` returns True as intended.
2. A non-symbolic origin/HEAD points to a missing 40-hex object in the synthetic fixture. This HEAD is deliberately not a trusted default, and the valid origin/main commit remains independently resolvable.
3. Git's batched query exits 128 with `fatal: missing object 1111111111111111111111111111111111111111 for refs/remotes/origin/HEAD`. The new recognition check now returns **False**. The old lookup ignores the non-symbolic HEAD and obtains the enabled policy through origin/main, returning **True**.

Thus an error in a ref that should be ignored can suppress the valid trusted policy and select legacy contract behavior. The predicate controls plan-ready requirements, implementation/done contract selection and event-authority validation (`core/emit_validation.py:200`). This violates H2's retained authority boundary and the recognition predicate's own fail-closed anti-downgrade contract. An ordinary Git error must remain distinguishable from a genuinely empty candidate set: fail closed or safely inspect the valid trusted fallback, rather than treating enumeration failure as absence of active authority. Add a real-Git regression with a disabled/deleted candidate policy, an enabled reachable trusted branch and a failed batched lookup. Preserve the bounded common path and existing precedence rules while fixing the error path.

An initial reviewer comparison helper incorrectly accessed a nonexistent `Recognition.enabled` attribute; that helper result was discarded and corrected. The corrected independent comparison explicitly loaded the validated enabled policy and returned old=True through origin/main, current=False. No product change was involved in either probe.

## Other source and specification observations

I examined the full new delta from b1446c8, both consumers of the new candidate helper, the original/current trusted-base resolution and recognition behavior, all new regression steps, the approval-bound assessment and the repair evidence. Native `make_code_subject` and `validate_code_subject` reproduce the supplied object exactly; every old/new blob in all 152 rows matches the respective Git tree. I also verified the eight new provenance files against their original bytes, recorded SHA256/length, working copies and committed blobs. The live recognition contract remains unchanged.

The ordinary path is appropriately bounded to one fresh Git query and uses full ref identities, avoiding same-named tag ambiguity and cross-call caching. Explicit output ordering retains symbolic-default, remote-main, local-main priority. Commit OIDs come from the current query; annotated-tag targets still use the existing commit-peeling resolver, and tree/blob targets fall through instead of becoming authority. The new real-Git regression covers ref movement, direct versus symbolic HEAD, shadow tags, annotated tags, invalid-type fallback and absent baselines. It does not cover the batched-Git-failure/recognition interaction identified above. I found no second independent blocker in the narrow source delta.

A concurrent ref update after a query can affect a later invocation, and an annotated-tag path is resolved again through the live ref. This is not a cross-call immutable snapshot or a guarantee of atomicity against concurrent ref updates; none should be claimed. No actual repository ref or policy was changed by the repair or this review.

## Verification, real-session and evidence boundaries

The retained focused run reports 23 passing cases in 62.49s, with source Ruff/mypy and decision/doc checks reported clean. I inspected its retained output and did not repeat expensive subsets or the full suite. The original full verification command was running independently against this new subject when the source blocker was established; I do not assert its eventual result. This rejection is for the reproduced authority regression, not an invented test failure or a presumed timeout of the new candidate. A successful full run would not remove this finding. Any later verification outcome must retain its own native record.

Historical A/B acquisitions, separate owner v1/v2 recognition and exact continue disposition, actual development/checks and original raw return bytes retain the meanings independently established in review 01. The observer/transport implementation is unchanged in this delta. Those real A/B records belong to their then-current source versions; neither their labels nor b1446c8's cost measurements establish all paths on 6dab09e. The new provenance correctly preserves the old rejection and failed verification, genuine A pytest command records, and source-specific cost reports rather than relabelling them as new success. The performance diagnosis's single-case and profiled timings have different scopes and do not establish a precise whole-suite speedup.

The previously disclosed A checks-host carrier mismatch and historical CRCRLF/terminal-blank-line diagnostics remain nonblocking evidence notes; the genuine pytest host records are now retained separately. The 24 KiB return, 10-second hook and 1200-second verification bounds remain unchanged. No complete desktop timeout reliability, all-tool interception, semantic understanding/compliance, cross-repository authority, final H7/H8 completion, publication or merge is asserted.

I made no actual-repository source, governed-plan, policy, ledger/state/review-record, installation or trust changes, and did not acquire context through any real session. Only the external isolated Git fixture and this new original review text were written. The actual tracked tree and target HEAD remained frozen. Fix and re-review a new exact subject under the recognized process; this conclusion grants no code approval, final import or attestation.