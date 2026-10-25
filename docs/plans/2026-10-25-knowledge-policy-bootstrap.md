---
change: 2026-10-25-knowledge-policy-bootstrap
stage: plan
---
# First knowledge-policy delivery and Keepsail pilot preparation

The owner confirmed the diagnosis and implementation proposal in this chat with
“开始” on 2026-10-25. This authorizes implementation of this plan, subject to the
existing recognized plan/code review. It does not authorize merge or activation.
The normative source remains `docs/product-architecture.md`.

On 2026-10-25 the owner additionally answered “确认调整至 1200 秒并继续” to
the concrete proposal changing only the full pytest check's execution budget
from 600 to 1200 seconds. This revision adds P5; P1–P4 and all other restrictions
remain unchanged. It requires a new recognized plan conclusion before that edit.

The owner subsequently asked to deliver the repair and pilot requirement in one
PR and answered “开始” to the proposal to add the confirmed pilot configuration
and documentation, update coverage and repeat verification/review of the complete
subject. This revision adds P6–P9 and replaces the earlier prohibition on installing
a first candidate. It authorizes preparing and publishing that combined PR, not
merging it or claiming that the real policy or pilot has already taken effect.

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
- P6: Include the owner-selected first policy candidate at
  `.harness/knowledge-recognition.yaml`: product `keepsail`, repository
  `Dawinia/keepsail`, protocol `knowledge-operation/v1`; only
  `keepsail-product-owner` may recognize knowledge, applicability and dispositions
  through `keepsail-owner-knowledge` version `1`. The separately selected
  `keepsail-cli-observer` may record actual retained CLI output, never understanding
  or compliance. Preserve the exact visible owner choices, approvals and limits
  in `docs/evidence/2026-10-25-knowledge-pilot-owner-authorization.json` and bind
  the candidate to that retained source with a canonical policy digest. Owner labels
  are local trust configuration, not authenticated identity. No agent-generated
  recognition or fabricated owner approval for a knowledge version.
- P7: Document the single target Change `2026-10-25-knowledge-cli-pilot`, first
  knowledge `delivery-evidence-boundary`, its exact candidate body/source and AND
  selector for repository and Change. Supply a reviewable version JSON, not a
  pre-approved operation/ledger event. Preserve the distinction between candidate,
  trusted policy activation, exact version recognition, supply, actual acquisition,
  agent statement and check result. Describe actual replacement-session acceptance,
  v1/v2 impact disposition, repository-wide protocol impact (including empty-set
  delivery), active Change inventory and withdrawal/history limits. No claim of
  completed real-agent use or of per-Change protocol activation.
- P8: Exercise the concrete repository candidate through existing isolated normal
  governance delivery and owner-controlled trusted-base advancement, with actual
  CLI subprocess retrieval and owner fixture evidence explicitly distinguished
  from real owner recognition. Verify target matching versus another Change,
  candidate non-authority, retained output/statement/check separation and pure Git
  attestation. Retain the full current-subject verification/review and create one
  PR for repair + candidate + pilot instructions. Do not merge or activate without
  the owner's later approval of the concrete result and repository-wide effects.
- P9: Correct the CI verifier execution boundary without changing its trust root:
  keep installing and executing the BASE_SHA verifier; run it in the explicitly
  identified trusted BASE checkout with exact target Git objects and only original
  target attestation bytes projected there. Always pass immutable base/head, bind
  the complete target manifest from Git, reject missing objects/nonregular evidence,
  and never fall back to candidate verifier code. Candidate schema/runtime acceptance
  is separately required and is not advertised as a new ability of historical
  trusted readers. Validate the real historical BASE reader and final combined
  subject, not only the current candidate reader.

## Boundaries

The earlier P1–P5 checkpoint installed no real policy. This revision permits the
first candidate file in the real worktree and combined PR, but it remains inactive
under the current trusted base. No merge, actual policy activation,
ledger/state/approval/receipt edits, historical migration, or
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

## Combined PR sequence and concrete pilot

1. Submit this revised exact plan with P1–P9 and obtain the existing recognized
   independent plan conclusion. Keep the original review/verification history.
2. Add the candidate policy, retained owner record, immutable first-version JSON
   under `docs/knowledge-pilot/`, and `docs/knowledge-pilot.md`; link the operator
   guide from docs/knowledge.md. The original preparation record and subsequent
   “one PR / 开始” exchange are both retained, explicitly preserving the still
   unapproved merge and exact knowledge-version recognition.
3. The first constraint body is: “交付、可观察获取、agent 采用声明、检查结果必须分开记录；缺失获取或检查不能宣称已读、已理解或已合规。”
   Its selector is `repository_ids: [Dawinia/keepsail]` AND
   `change_ids: [2026-10-25-knowledge-cli-pilot]`, authority `constraint`,
   previous_version null. Retain source architecture text and repository baseline.
   This is a proposal for later exact-version owner recognition, not approval from
   the generic “开始” message.
4. Reuse the existing BootstrapWorkspace fixture for concrete-policy integration
   coverage; add only the test logic needed for this real configuration. Tests may
   simulate owner recognition only in an explicitly isolated Git fixture. No real
   knowledge operations are possible under the inactive trusted base.
5. Inventory active Changes using the real CLI, report next-action impacts without
   transitioning unrelated Changes. Other Changes require exact current-set supply
   after activation, even if this knowledge does not match them. No silent protocol
   exemption, blanket approval revocation or automatic retirement of old work.
6. Record all actual coverage against the revised approval. Run focused concrete
   policy/bootstrap regressions, normal full done under the retained 1200-second
   budget, decision/doc checks, exact independent code review, attestation export
   and pure Git verification. Push the branch and create/update one PR; retain CI
   results separately. Freeze edits while a review is pending.

Estimated additional files: .harness/knowledge-recognition.yaml,
docs/evidence/2026-10-25-knowledge-pilot-owner-authorization.json,
docs/knowledge-pilot.md, docs/knowledge-pilot/delivery-evidence-boundary-v1.json,
tests/integration/lifecycle/test_keepsail_pilot_configuration.py and docs/knowledge.md.
No runtime extension is planned beyond already delivered P1–P5. A product defect
requiring changed commitments must be diagnosed and proposed before implementation.

Merge acceptance is explicitly separate: confirm actual trusted-base/source
versions, repository-wide affected Changes, CI, preserved local event continuity,
and the absence of effective knowledge until later exact-version recognition.
Rollback is not deletion of active policy or events: stop new pilot work, retain
history, use recognized retirement/exclusion and impact disposition as applicable;
general active policy replacement/deactivation remains a separate design gap.
An actual replacement agent session is required to close real cross-session use;
this PR may ship its prerequisites and handoff but must report that step pending.

## Trusted verifier compatibility within the same PR

The first combined plan was independently rejected because `.github/workflows/
merge-gate.yml` installs the old BASE verifier but invokes it in candidate context.
Its old code-subject recomputation consults that mutable context and rejects first
policy delivery. The original reject evidence is imported and retained. An isolated
real-Git comparison with the historical 7e2e6f8 reader reproduces exit 2 on the
candidate workspace and exit 0 on the trusted BASE workspace with the same exact
target objects, evidence and base/head. P9 addresses the common execution boundary,
not the error message or its authority checks. The policy remains in the complete
reviewed target manifest; this is not deleting it from an alleged HEAD checkout.

P9 adds `.github/workflows/merge-gate.yml` and focused integration coverage for the
workflow's actual evidence-projection program. Fetch target objects from the local
candidate checkout into the trusted checkout, verify its HEAD remains BASE_SHA,
project only regular `.harness/attestations/*.jsonl` Git blobs after path validation,
and verify copied bytes. Do not copy candidate source/config or execute candidate
verifier modules. Ensure negative evidence/missing-object cases reject. Add concrete
candidate/bootstrap tests to the required candidate-acceptance job, retaining all
existing tests. Validate activated-base strictness with the current reader and
historical-reader limits explicitly; do not claim the old reader can validate the
new candidate-policy semantics. Final historical installed-verifier acceptance
against the complete frozen branch is required before PR publication.
