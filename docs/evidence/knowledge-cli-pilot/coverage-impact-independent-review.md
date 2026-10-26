# Independent diagnostic review: coverage changes orphan an impact disposition

Reviewer: `/root/coverage_impact_diagnosis_review`. Repository: `E:/Work/keepsail`.
HEAD independently resolved: `781d8a83fa6133f13bab096681ad8555cc7588fe`.
This is a read-only diagnostic/design review, not a plan approval, code approval,
knowledge recognition, impact disposition or authorization to implement.
No repository, event ledger, policy, state or source file was changed by this reviewer.

## Confirmed finding

The parent diagnosis is correct. `_context` unions estimated scope, actual coverage
and current code-manifest paths. `_view.impact_basis` hashes the resulting current
raw path list. Historical supplied v1 records are compared to current constraints,
then their impact subjects are regenerated using that mutable basis. The exact
recognized disposition is indexed by the old impact digest, so an unrelated path
addition generates another pending subject despite unchanged knowledge, matching,
challenge and authorization.

Independent minimal read-only probe used the same validated live ledger and policy
(revision `07bf94275cf269ed29fe83889d8bd9ffb76915aac429e3ef856f0a03f669c55c`),
the actual context from `v2-continued-check.json`, and `_view` twice. The only
change was adding `docs/evidence/knowledge-cli-pilot/one-unrelated-fixture.json`.
Original impact `8bfc3023b83ae44d1b52bae64e83e2f84992985c6cf39081bde748bd3d097d3b`
was resolved. The one-path context produced pending impact
`119a22f77793b2e2b4415f8047f7f99d036de03ba33f7315c1e90eaef2d4822c`.
Constraints, evaluated matching and approval stayed identical. This independently
minimizes the actual 44-path coverage expansion without replaying or changing events.
The parent's real CLI final check additionally establishes native exit 2 even after
an exact delivery under the expanded context; new delivery alone cannot resolve it.

This conflicts with C2 and the explicit architecture choice that within-approval
file additions do not revoke authority, while C3/C5 still require actual relevance
changes and unresolved disputes to remain consequential. The approved pilot prohibits
source fixes and requires a separately authorized common-model repair/test plan.

## Recommended concrete repair plan

1. Separate an immutable knowledge-impact episode from mutable delivery context.
   Preserve each impact's exact trigger subject, trigger-time approval and bounded
   applicability/dependency context. Do not regenerate an already recorded subject
   merely because the present coverage list grows. Raw present paths remain in the
   current delivery basis, so current-set delivery refresh is still required.
2. For new triggers, retain a validated trigger-context/impact snapshot through the
   strict native writer. Replay and pure-Git checkpoint validation must consume the
   same immutable snapshot and shared applicability evaluator. Do not implement a
   live-only report special case. Any event/checkpoint schema addition needs explicit
   version/minimum-reader handling; old readers must not silently reinterpret it.
3. Independently compare current versus trigger applicability/dependency facts for
   the relevant old/current versions and recorded applicability judgments. For this
   repository+Change-only selector, unrelated paths have no relevance effect. A path
   boundary crossing, unknown applicability, relevant new challenge, version change,
   recognition/retirement/exclusion or changed recognized applicability still yields
   a distinct unresolved obligation/episode rather than inheriting old continuation.
   Challenge dependency checks continue evaluating actual paths; no blanket removal
   of paths and no automatic downgrade of constraints.
4. Preserve legacy exact subjects and original conclusions. Prefer reconstruction
   only when the retained historical evidence proves the original trigger context.
   Do not substitute the latest delivery context: coverage could have changed between
   that delivery and the trigger. When evidence is insufficient, fail explicitly and
   provide a narrowly scoped, owner-authorized native append-only context-recovery
   binding to the exact legacy impact/conclusion and recovered original evidence.
   For this pilot, retained actual resume/check outputs contain the original context
   and exact resolved subject; they can support such a recovery after authorization.
   Never rewrite old receipts, rehash/import the owner's answer as a new answer, or
   match dispositions solely by old/new version pair.
5. Keep the original approval epoch immutable through reapproval and use the new
   effective approval only for genuinely later triggers. Preserve strict CAS,
   operation idempotency/conflict, subject matching, issuer policy and corruption
   rejection. Repair selection must not turn reported execution into verified work.

## Compatibility constraint requiring design attention

`checkpoint()` retains `ledger['events']`, which contains knowledge events only.
`validate_checkpoint()` replays `_apply` with `approval_context`; it does not have
all historical non-knowledge plan/coverage events. Therefore deriving trigger paths
from the live full event prefix is not a complete solution for retained/pure-Git
validation. A trigger snapshot (and explicit legacy recovery where needed) must
travel with retained evidence. Merely replacing raw paths with a semantic hash is
also insufficient: it changes the already approved legacy impact ID immediately.

## Regression and acceptance seams

- Native CLI integration: real governing approval, v1 supply, v2 recognition,
  exact continue-v2 disposition; unrelated implementation coverage addition;
  check first requires fresh exact delivery, then passes after delivery, while the
  original impact ID/conclusion and trigger approval remain intact.
- Global and repository+Change selectors; path selectors with unchanged matching;
  matching-to-nonmatching, nonmatching-to-matching and unknown-context cases.
- Global/path/unknown challenges and disjoint versus dependent action checks;
  actual knowledge/applicability changes cannot inherit a prior disposition.
- Two approval epochs: old trigger retains its original approval; later trigger
  uses the later approval. Adjust/reapprove still require actual execution evidence.
- Replay existing pilot records byte-for-byte, preserving the exact original
  disposition. Insufficient legacy context must fail explicitly; authorized
  append-only recovery must be exact and reject mismatched context or conclusion.
- Export checkpoint/attestation and verify from pure Git with no mutable local
  ledger/state. Include old and new retained formats and missing/tampered trigger
  snapshot cases. Live and retained validation must agree.
- Retain stale-revision, conflicting operation ID, unknown issuer, corrupted records,
  missing/failed/skip conclusions and historical evidence completeness failures.
- Only after targeted red/green evidence: normal decision/doc/full verification,
  exact independent plan/code review and attestation under the separately approved
  repair Change. Resume the pilot without declaring the current blocker resolved
  before real native regression and exact-subject acceptance pass.

## Required owner decision

Approve a separately governed source-repair effort with the scope and tests above,
including any explicit additive trigger-snapshot/legacy-recovery protocol work.
The present continuation answer authorizes neither source fixes nor unbounded
creation of new sessions. If a separate session is desired, request that authorization
explicitly. Until then keep the pilot blocked, retain its actual results, and do not
request repeated equivalent impact confirmations as a workaround.

## Bounded legacy compatibility refinement

A narrower automatic compatibility path is sound for this pilot if it proves the
exact legacy subject, rather than inferring a new authorization. Enumerate validated
retained delivery contexts for the same Change (do not choose the latest context).
For each, recompute the complete legacy impact and its full basis using those paths
and the applicable policy, versions/states/current, applicability records, trigger
approval and trigger kind/challenge ID. Require exact equality with the retained
recognized disposition's complete `impact` object and its `subject_id` digest.
Additionally require the relevant selectors/dependencies to be demonstrably path
insensitive, or a separately validated complete relevance equivalence predicate;
the initial bounded implementation should support the path-insensitive case only.
This includes retaining ordinary current-path applicability/challenge checks.

For this pilot the original handoff delivery supplies a candidate path context
matching the original impact. Exact hash validation is an evidence reconstruction,
not a new inferred owner answer. Require the exact original issuer/process/policy
and all normal evidence validation. A later relevant knowledge/applicability change
must make the full legacy basis differ and prevent reuse. This compatibility
algorithm belongs in the shared replay/view/checkpoint model, with regression tests
for a matching older context, a nonmatching latest context, missing candidate context,
wrong approval, changed applicability/state/policy, path-sensitive or unknown
relevance, and tampered historical receipts.

If no exact candidate context is provable, or relevance is path sensitive/unknown,
fail closed and require the explicit native append-only recovery described above.
Do not claim that delivery contexts generally reconstruct trigger-time scope.
