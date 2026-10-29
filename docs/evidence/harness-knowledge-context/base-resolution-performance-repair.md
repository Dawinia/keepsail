# Verification timeout and live baseline lookup repair

2026-10-29 checkpoint. This is implementation/check evidence, not a new plan,
knowledge recognition, impact disposition or final code approval.

Frozen candidate b1446c8, subject
`code:fb526c2191ed58698857a7357d8c35dfc77d62bc30de5677cb92407a4bb02351`,
did not complete final verification. The first native run ended abnormally after
1104.025s (pytest exit 0x40010004); a following Git operation also exited abnormally.
The later retry reached the unchanged 1200s pytest deadline (1200.620s). Neither
run supplied a passing test summary. Ruff, mypy and lifecycle checks passed; the
existing non-mandatory scope comparison remained advisory. The independently
retained candidate review explicitly rejected completion because required
verification had not passed, without inventing a test assertion failure.

Only after that external review ended did implementation continue in its existing
IMPLEMENTATION_IN_PROGRESS state. No current native final code subject had been
created by the failed done operations; no review approval or lifecycle rejection
was fabricated to obtain an edit allowance.

## Diagnosis and bounded change

A focused native invocation of the PostgreSQL adjustment case passed in 26.95s.
A separate profiled run passed in 30.96s; its profile recorded 499 subprocess
calls and 123 baseline resolutions, with about 15.24s cumulative time in baseline
resolution. Profiling adds overhead; these are diagnostic samples, not a general
latency guarantee or proof that every timeout has one cause.

The existing trusted base order is retained as the symbolic remote default,
origin/main, then local main. A single fresh Git for-each-ref query supplies full
ref identities and object types. A direct, non-symbolic origin/HEAD is ignored;
same-named tags cannot impersonate trusted branches. Ordinary commit refs need
one Git process; an annotated-tag target is still peeled and checked as a commit
through the existing resolver. Tree/blob targets cannot become authority. There
is no persistent cache and each invocation observes current refs.

The new real-Git regression first failed on repeated subprocesses, then caught
the intermediate direct-origin/HEAD mistake before finalization. It now covers
the process bound, live ref movement, default-ref precedence, same-named tags,
annotated-tag peeling, non-commit fallback and missing-baseline rejection.
This preserves the intended branch authority and fixes its short-name ambiguity;
it does not recognize a new policy or write actual repository refs.

## Current focused checks and retained boundaries

The final targeted run passed 23 cases in 62.49s: approval predicates, knowledge
policy bootstrap and the public adjustment/attestation/replacement-process case.
That case's call phase was 19.45s. The earlier 26.95s number is the whole single-case
pytest run, so it is not used as a precise speedup percentage. Ruff, mypy and
decision/doc checks passed. Test assertions, selections in verification.yaml and
the 1200s deadline were not relaxed. The complete new subject still needs native
full verification and exact external review.

A/B evidence remains scoped to the actual implementations at those checkpoints.
The observer, transport and knowledge/approval protocols were not changed by this
lookup repair. A new original-chat resume acquired current v2 under the same
approval; its prior entry's acquisition was not inherited. Final native return
validation and current-source checks must accompany the retained historical A/B
facts rather than relabelling their source commits.

## Enumeration-error review and correction

The subsequent exact candidate 6dab09e,
`code:799477163f44c219a0d59122150628089b0f2ea0e7a32a0021dc9c8d90a05b71`,
was rejected for a real error-path defect: treating a failed Git enumeration as
an empty candidate set could make recognition_contract_active return false when
a disabled working copy coexisted with an enabled trusted main. A corrupt,
non-symbolic remote HEAD reproduced it while main was still readable. The new
candidate's complete check was stopped after that independent finding, not
reported as a test pass or a pytest assertion failure.

The correction distinguishes Git metadata/configuration from an uninitialized
workspace only on the error path. Detected Git metadata (including worktree
markers, bare metadata and explicit Git directory configuration) makes failed
enumeration an ApprovalError; metadata inspection errors also remain errors.
The existing no-Git initialization case remains inactive. The real-Git regression
first reproduced the erroneous downgrade and now expects an explicit failure.
Normal successful lookup still uses one fresh Git query and no persistent cache.

The corrected focused run passed 23 cases in 57.76s; Ruff/mypy and decision/doc
checks passed. Previous candidate conclusions and controller-stop evidence remain
retained. The next exact subject requires independent source confirmation before
its full check, then the actual complete result before any final approval.

Exact failed native summaries, candidate rejection, A's directly retrieved pytest
host records, focused output and cost reports are retained under
codex-b/provenance/. Costs recorded on b1446c8 remain historical to that source;
current-source measurements and the final result must identify their own subject.
