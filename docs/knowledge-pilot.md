# Keepsail CLI pilot: activation and acceptance

This procedure delivers the first policy and prepares real use in one PR with the
bootstrap repair. It does **not** claim that merging code completes the pilot.
The [product architecture](product-architecture.md) remains normative.

PR #130 has since merged. The actual trusted base now includes the policy and
the CLI reports active protocol coverage. The [real acceptance record](knowledge-pilot/acceptance.md)
tracks completed operations separately from pending knowledge recognition and
replacement-session use. Pre-merge instructions below retain their original
conditional meaning; they are not a claim that the current policy is inactive.

## Owner choices and current authority

The [retained owner excerpts](evidence/2026-10-25-knowledge-pilot-owner-authorization.json)
authorize preparing the selected policy and publishing the combined PR. The
candidate policy is `.harness/knowledge-recognition.yaml`, product `keepsail`,
repository `Dawinia/keepsail`, process `keepsail-owner-knowledge/1`. Only issuer
`keepsail-product-owner` is recognized for knowledge, applicability and disposition.
The `keepsail-cli-observer` label is limited to retained actual CLI returned content.
These labels follow the existing local trust model; they do not authenticate a person.

Before authorized merge into the actual trusted base, `knowledge show` must return
`coverage=not_recorded` and `policy_candidate.status=candidate`. No knowledge writes
or effective constraint can be obtained from that file. The merge decision is still
reserved: **once the policy is in the trusted base, repository protocol obligations
start**, even though no knowledge version has yet been recognized.

The proposed first work is `2026-10-25-knowledge-cli-pilot`, limited to documenting
and exercising the CLI evidence/recovery procedure. Its proposed first knowledge
is [delivery-evidence-boundary v1](knowledge-pilot/delivery-evidence-boundary-v1.json).
That file is a `knowledge-version/v1` proposal, not an import operation or a recognized
constraint. Its repository AND Change selector limits knowledge applicability, not
the repository-level protocol. Owner recognition must name the exact returned
version digest after proposal; generic preparation approval is not that conclusion.

## Before deciding to merge

Record the exact current HEAD, trusted-base SHA, installed CLI/module paths, CI
verifier source and retained final verification/review subject. CI must keep the
BASE_SHA verifier as authority and validate target manifests using explicit base/head.
Its BASE workspace receives only exact target attestation blobs, never candidate
source or configuration. Required candidate acceptance separately validates the
concrete candidate and current protocol. An old verifier is not claimed to acquire
new candidate-schema semantics merely by moving its working directory.

The local active-Change inventory at preparation was:

| Change | Recorded state | Effect on later actions after activation |
|---|---|---|
| `2026-09-04-product-baseline` | IMPLEMENTATION_IN_PROGRESS | Restore existing authority and retain exact current-set delivery before covered actions; do not restart or abandon it automatically. |
| `2026-09-15-plan-authority-alignment` | READY_TO_MERGE | Retain historical approval/review; evaluate subsequent knowledge preconditions, delivery and current subject before a new action. |
| `2026-10-25-knowledge-policy-bootstrap` | This combined delivery | Its inactive delivery subject remains historical; later actions use the then-effective policy. |

Refresh this inventory with `keepsail --json status --all` at merge time. An empty
constraint set still requires its own exact delivery for later covered actions.
Do not transition unrelated Changes as a demonstration. Retain the existing local
event ledger through checkout updates; a clean executor must use supported retained
evidence/recovery rather than invent missing events. Missing activated history is
an explicit failure, not proof there are no obligations.

## Real pilot sequence after authorized activation

Use root options before the command group:
`keepsail --workspace E:/Work/keepsail --json ...`. Retain original command, output,
exit code, input files, returned IDs/digests and exact subjects in the pilot's
governed evidence. Operations read workspace-local JSON files; do not hand-edit
events, state, review conclusions or delivery receipts.

1. Verify actual base/HEAD/imports, policy digest, `knowledge show` and ledger
   availability. A candidate result means activation has not happened. Declare the
   target Change with normal `change start`; freeze a specific operator-work plan,
   obtain recognized plan approval, retain an initial exact delivery (possibly empty),
   and use `implementation start` before authoring knowledge.
2. Wrap the proposed version file as `version` in a `knowledge-operation/v1` with
   unique operation_id, current show revision and the governing change_id. Submit
   with `knowledge propose --record <workspace-file>`. Retain version_digest and
   candidate body/source. Ask the owner-recognized process for an explicit conclusion
   on that exact digest; preserve the actual original conclusion and policy provenance.
   Only then use `knowledge import --evidence <workspace-operation-file>`.
3. Run `knowledge deliver 2026-10-25-knowledge-cli-pilot --operation-id <new-id>
   --expected-revision <current-revision>`. Retain complete text, recognition,
   selection inputs, version and basis. `prepared` means saved supply, not acquisition.
   Another Change must evaluate as non-matching for this version; global/path rules
   and corrupt-data failures are exercised only in isolated tests.
4. If a recognized observer actually captured this returned body, record acquisition
   with delivery_id, version_digest, producer `keepsail-cli-observer`, the SHA256 of
   returned body and retained original_receipt. Without such output, keep missing
   acquisition. Separately record an agent statement with adopt/reject/challenge and
   reason. `knowledge check` reports its covered obligations, not semantic compliance.
5. Have the owner open a genuine replacement agent session on the same product/work.
   That executor checks identity/import/base and runs `change resume <target>` plus
   `knowledge show delivery-evidence-boundary --version <digest>`. It identifies
   original supply, current version, effective approval and unresolved matters from
   retained records, performs a real approved documentation action and records its
   declaration and actual checks. A Python subprocess test alone does not satisfy this.
6. Propose a correction v2 with previous_version=v1 digest; recognition must again
   name its exact subject. Old supply/text must remain. Resume must expose the exact
   impact and trigger approval context; affected completion waits for a recognized
   disposition. The owner/process chooses continue (explicit v1/v2), adjust or
   reapprove as appropriate; knowledge correction cannot release work commitments.
   Adjust/reapprove need actual obligations/checks/current code review and any new
   approval required, never a self-reported execution relabeled verified.
7. Exercise challenge/dependency failures in an isolated copy: the constraint remains
   effective, dependent actions wait, clearly independent actions can continue.
   Empty/failed/skip/unknown issuer/old revision/conflicting operation or corrupt
   records never become recognition. Do not inject corruption into the real ledger.
8. Record implementation assessment/actual coverage, run decision/doc checks and
   normal done, obtain exact code review, retain attestation and separate CI evidence.
   Mark passing, failing and unverified layers separately.

## Withdrawal and completion boundaries

Before merge, withdraw the candidate PR without activation. After activation, do
not delete policy/events or rewrite old receipts to make knowledge disappear.
Stop new dependent pilot work; use owner-authorized retirement or non-applicability
and exact impact disposition where appropriate while retaining immutable history.
A general active-policy replacement/deactivation cutover is **not implemented by
this repair** and requires its own authorized design. A Git revert is not a knowledge
disposition. Independent authorized work may continue.

This PR validates installation paths/source, candidate delivery, exact Git evidence
and isolated protocol behavior. Real activation, exact first-version recognition,
replacement-agent acquisition/use and real v2 disposition remain pending their
actual operations. Cross-repository sharing, universal tool interception, complete
semantic recall and long-term usage effectiveness remain outside this slice;
those limits do not narrow the normative product architecture.
