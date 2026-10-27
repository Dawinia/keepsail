# Product architecture: implementation coverage

This descriptive snapshot is subordinate to the normative
[product architecture](product-architecture.md). Conflicts are implementation or
documentation gaps; this report does not narrow architecture or authorize repairs.

## Evidence boundary

Source links below follow the current Keepsail namespace. The audited revision
used the former namespace; this path-only update does not refresh its findings.

Source audited: bfcdb0073b1950067e8b3be278aa09535526bff7, checked on 2026-10-22.
The independent audit verified main and origin/main after fetch and confirmed that
the CLI and test environment imported that source checkout. It reported 233 passing
targeted tests across plan authority, approval, decision records/checks, state
snapshots, implementation, events, local gates and Change recovery. This is the
retained audit's historical result, not a fresh run by this document publication
and not acceptance of all architecture obligations. Relevant tracked suites include
[plan authority](../tests/integration/lifecycle/test_plan_authority.py),
[approval](../tests/unit/core/test_approval.py),
[decisions](../tests/unit/core/test_decisions.py),
[decision checks](../tests/unit/core/test_decision_check.py),
[snapshots](../tests/unit/core/test_state_snapshot.py),
[implementation](../tests/unit/cli/test_implementation.py),
[events](../tests/unit/core/test_events.py),
[local gate](../tests/unit/gates/test_pre_tool_use.py) and
[Change CLI](../tests/integration/cli/test_change.py).

Repository-relative links locate evidence in this checkout; inspect the audited
commit for the dated observation if these targets later change. A missing
implementation chain means none was located in the inspected material, not proof
that no external process exists. Source, tests, active hooks, CI runs, packages and
deployed protection must not be conflated.

## Capability coverage

| Obligation | Evidence at audited revision | Coverage and limit |
|---|---|---|
| C1: restore commitments and approval | [State](../src/keepsail/core/state.py), [reducer](../src/keepsail/core/reducer.py) and [status](../src/keepsail/cli/status.py) preserve approval, plan snapshots, revisions and assessments. | Partial. [Resume](../src/keepsail/cli/change.py) mainly renders state, recent events and scope, not complete effective commitments and their relations. |
| C1: knowledge states and unresolved matters | [Decision records](../src/keepsail/core/decisions.py) retain current status; state retains pending plan revision. | Partial. No complete general knowledge dispute/applicability recovery chain located. Resume's empty pending-sensor list is not proof of no unresolved matters. |
| Product continuity across repositories | [Workspace resolution](../src/keepsail/core/paths.py) uses the nearest harness directory. | No complete evidence located for cross-repository product identity, shared knowledge authority and recovery. |
| C2: approval before implementation | [Implementation CLI](../src/keepsail/cli/implementation.py), [review import](../src/keepsail/cli/review.py), [emit validation](../src/keepsail/core/emit_validation.py). | Covered on inspected new-contract paths. Does not imply every tool write is intercepted. |
| C2: in-bound additions retain approval | [Assessment and approval](../src/keepsail/core/approval.py), implementation coverage; fixture-addition integration test. | Covered on inspected scenarios. Structured assessment is retained reasoning, not mechanical proof that its semantic conclusion is right. |
| C2: commitment changes need approval | Approval snapshots, commitment IDs and pending revisions. | Partial evidence chain. Cumulative semantic drift still needs external judgment; that dependency is intentional. Remaining work is to establish the appropriate judgment/coverage, not demand semantic understanding from core. |
| C3: explicit/global constraint delivery | [Anchor scanner](../src/keepsail/core/anchor_scanner.py), [source scope](../src/keepsail/core/source_scope.py), [decision checks](../src/keepsail/core/decision_check.py). | Partial neighboring mechanisms, not complete delivery. Source anchors relate code to decisions; checks do not demonstrate an applicable Change constraint set was supplied to an executor. |
| C3: recognized applicability judgments | [Recognition and evidence](../src/keepsail/core/approval.py) support plan/code kinds. | No complete knowledge-applicability recognition/import/relation/execution chain located. |
| Knowledge authority independent of checkability | [Decision shape](../src/keepsail/core/decisions.py) has status and checkability tiers. [Technical architecture](ARCHITECTURE.md#7-decision-conformance--the-core-decisions-bind-code-subsystem) calls tier-3 context that never gates. | Missing independent guidance/constraint authority dimension; the quoted technical account conflicts with the product rule that lack of a mechanical check does not downgrade authority. Preserve product rule. |
| C4: candidate, supersede, retire | [Decision CLI](../src/keepsail/cli/decision.py) supports lifecycle operations. | Partial: the decision subset exists, not a complete general product-knowledge model. |
| C4: policy-recognized knowledge authority | Plan/code recognition; decision ratification stores identity/time/text hash. | Partial neighboring mechanisms. Command execution and an identity field do not establish completion of an authorized knowledge-recognition process. |
| C4: challenge and historical grounds | Decision betray/reconcile, supersession and Git history. | Partial. No complete per-knowledge recognition/challenge/use-version history located; Git history alone does not bind a working version to a Change. |
| C4: no knowledge-based authorization bypass | Plan approval is separate from knowledge files; active contract does not grant authority from skip. | Partial. No complete classification/judgment chain linking knowledge changes to changed acceptance obligations located. |
| C5: control on declared surfaces | [Gate](../src/keepsail/gates/pre_tool_use.py), [runner](../src/keepsail/sensors/verification_runner.py), [attestation](../src/keepsail/engineering/attestation.py). | Partial and bounded: edit tools, CLI and CI have different coverage. Shell writes are outside live edit gating; configuration does not prove hook activation. See [Codex limits](adapters/codex.md). |
| C5: explicit exceptional-state handling | [Snapshot loader](../src/keepsail/core/state_snapshot.py) maps several damaged-state cases to no state; gate permits no-active-change behavior. | Observed gap: damage is conflated with normal absence. This does not select blanket blocking as the replacement policy. Verification and empty/failed review have separate fail-closed behavior. |
| C6: precise plan/code/check evidence | Plan snapshots, blob manifests, evidence IDs, original conclusions/provenance and attestation. | Covered on inspected object chains; no proof of substantive review quality or cryptographic producer identity. |
| C6: supply/read/adoption/check distinction | Lifecycle/check/review/gate records; [observer](../src/keepsail/daemon/framework_observer.py) watches framework changes. | No complete knowledge-identity/version acquisition chain located. File-change observation is not retrieval observation; agent statements require a separate evidence category. |

## Responsibility and in-flight rules

Active review imports recognized conclusions without organizing reviewers or
retries. Historical modules alone do not contradict this boundary. The tracked
[recognition policy](../.harness/review-recognition.yaml) is an owner-selected
plan/code process, not a universal product requirement. Knowledge recognition and
applicability still lack the complete corresponding chain.

Anchor drift and tier-2 reconciliation provide partial related mechanisms, but do
not establish knowledge-version change → linked in-flight Change → recognized
applicability judgment → applied outcome → session recovery. Plan revision handling
already demonstrates part of the authorization pattern, not its knowledge-wide
completion. Betray can leave a decision ratified, consistent with challenge not
automatically revoking authority; dispute dependencies and action-local waiting
were not located as a complete feature.

## Scenario assessment

| Product scenario | Assessment |
|---|---|
| Omitted recall | Partial: anchor integrity is checked, but required delivery and supply/read trace are not established. |
| Mistaken recognition | Partial decision lifecycle; no complete policy correction plus recognition/use-history chain established. |
| Unstable-test authorization bypass | Approval and non-approval safeguards exist; no complete end-to-end semantic proof for this scenario. Assessment shape alone cannot prove unchanged acceptance. |
| In-flight technology change | No complete knowledge-change/linked-work/judgment/application/recovery chain located. |

## Remaining evidence limits

The audit did not validate published packages, clean installation, current CI
execution, active hook trust or remote required branch protection. Targeted tests
do not establish production outcomes or full architecture acceptance. No runtime,
knowledge policy or ratified decision was changed by the audit or this publication.

The main reuse opportunity is existing Change authorization and exact-subject
evidence. Main gaps are product-knowledge authority, explicit delivery, versioned
acquisition trace and in-flight feedback. These are design inputs, not an
implementation roadmap or permission to alter the normative architecture.

## 2026-10-24 explicit-constraint slice (local implementation evidence)

The table above remains the dated bfcdb007 audit. The new
[CLI contract](knowledge.md), [implementation plan](plans/2026-10-24-explicit-constraints-implementation.md)
and [PostgreSQL lifecycle test](../tests/integration/lifecycle/test_knowledge_delivery.py)
describe a later, bounded implementation. This section does not rewrite that
historical verdict or assert full architectural acceptance.

| Capability | New implementation and remaining limit |
|---|---|
| C1 | Resume reconstructs supplied historical text, effective approval, current constraints, challenges and impact execution from persistent records, across replacement processes. Full reasoning and unknown semantic relationships remain outside recovery. |
| C2 | Existing plan/code approval remains separate; current knowledge basis binds new subjects. Reapproval dispositions require a new effective plan approval. In-bound file additions still use implementation assessment. Semantic commitment/risk classification depends on the recognized process. |
| C3 | The CLI retains the complete finite set selected by global, explicit repository/change/path selectors or recognized applicability. Non-matching and unknown are separate. It does not guarantee semantic recall or cross-repo delivery. |
| C4 | Candidates, immutable versions, recognized authority, retirement, supersession and challenges have distinct records. No check is required for constraint authority. Knowledge correction cannot itself approve a changed work commitment. |
| C5 | Strict event validation and attestation enforce declared knowledge preconditions; adjustment can enter verification/review, while final closure requires verified execution. This does not change native editor/shell interception coverage or the historical snapshot loader's behavior. |
| C6 | Delivery snapshots retain exact versions and recognition evidence; observations, agent statements and check/review facts remain separate. Generated checkpoints retain cross-governing-Change knowledge for pure Git validation. Producer labels are not cryptographic authentication. |

The isolated lifecycle scenario executes a failing PostgreSQL-version fixture,
corrects it, obtains current-subject verification/review, records execution and
validates attestation without the local event/state cache. The fixture demonstrates
the governance chain; it is not a running PostgreSQL server or a production
database migration. Concurrent processes compete for one exact ledger revision.
Dedicated unit scenarios exercise candidate nonauthority, immutable identity,
explicit matching, rejection/failure, challenge independence, corruption and
policy downgrade refusal.

The product identity is stable but the ledger is local to one repository. Shared
product authority across repositories, broad knowledge formation, universal
semantic applicability, full agent-loop ownership and all-tool enforcement remain
unimplemented obligations/boundaries as specified by the normative architecture.
At the 2026-10-24 slice above, this repository's policy had not been activated.
The following dated update records the later trusted-base activation; source,
installed hooks, package publication and actual CI/session evidence remain separate.

## 2026-10-27 baseline refresh and single-harness integration candidate

Live audit baseline: main, origin/main and remote main were all
`bb69097dffee4e782568da4ea688d06b5773cbf4`. The native contract-base resolver
returned the same commit. This dated section preserves the earlier historical
audit instead of applying its gaps as current capability claims.

| Obligation | Current evidence and remaining boundary |
|---|---|
| Trusted knowledge policy | [PR #130](https://github.com/Dawinia/keepsail/pull/130) merged the policy; native resolution reports active `8837f4d7...`. Repository protocol applies separately from the pilot knowledge's Change-specific selector. |
| Stable in-flight grounds | [PR #131](https://github.com/Dawinia/keepsail/pull/131) preserves immutable trigger/approval/disposition across unrelated coverage changes while exposing real relevance changes. |
| Real manual cross-session CLI use | [PR #132](https://github.com/Dawinia/keepsail/pull/132) and [acceptance](knowledge-pilot/acceptance.md) retain the actual replacement executor, v1/v2 and four fact categories. This is not proof of the new hook path. |
| Baseline and historical closure | [PR #133](https://github.com/Dawinia/keepsail/pull/133) supplies historical merged-Change recovery compatibility; native product-baseline and pilot states are ARCHIVED. Unrelated READY_TO_MERGE remnants remain outside this Change. |
| Checkability and authority | The old table's tier-3 quotation is historical. Current [technical architecture](ARCHITECTURE.md#7-decision-conformance--the-core-decisions-bind-code-subsystem) separates checkability from constraint authority. |
| C1/C2 entry context | The [confirmed plan](plans/2026-10-27-harness-knowledge-context.md) adds explicit Change/session/epoch binding and complete frozen approval/commitment/restriction and ratified-text projection. Candidate implementation needs current exact review and actual host acceptance. |
| C3/C6 delivery and observation | Native supply, bounded pages, exact CLI-return reconstruction, native whole-version acquisition and separate declarations/checks. SessionStart printing is not acquisition; empty-set context receipts are not knowledge versions. |
| C4/C5 recovery and local action | Current-authority refresh retains old version/approval grounds; actual paths can expose new applicability. Selected edit preconditions preserve independent work and existing authoring allowances. Real A/B and recognized v1/v2 disposition remain required. |

The [new entry guide](knowledge-context.md) describes the candidate interface.
Implementation fixtures are supplemental evidence, not actual Claude callback or
replacement-session acceptance. No current claim of complete H7/A1–A12 acceptance,
published package, merged integration, shared cross-repository authority, semantic
recall, all-tool interception or model understanding/compliance is made here.
