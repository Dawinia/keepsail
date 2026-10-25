# Explicit knowledge delivery (protocol v1)

This is the single-repository CLI surface of the
[product architecture](product-architecture.md). An unchecked effective constraint
is still binding. Knowledge recognition and work authorization remain separate.
The repository policy became effective through the trusted base after PR #130
merged; see the [real pilot acceptance record](knowledge-pilot/acceptance.md).

The repository carries the first delivered policy and a bounded
[Keepsail pilot procedure](knowledge-pilot.md), including retained owner choices,
the proposed first knowledge version and activation/acceptance limits. The actual
trusted base now includes the policy: repository protocol obligations are active.
This does not itself recognize the first knowledge version or complete acceptance.

## Activation and trust

Effective authority comes only from an owner-controlled
`.harness/knowledge-recognition.yaml` in the trusted base selected by the existing
contract-base resolver (or the explicit base supplied to attestation verification).
A first candidate can be delivered through an ordinary approved Change while that
base has no policy: the candidate must pass schema/digest validation and remain in
the complete code subject, actual coverage and exact plan/code review. It does not
activate the knowledge protocol. `knowledge show` then returns exit 0 with
`coverage=not_recorded` and `policy_candidate.status=candidate` plus its policy
digest; knowledge writes remain unavailable. Subject generation and export do not
invent a knowledge basis or checkpoint for this inactive delivery.

Committed attestation validation applies the same candidate checks to the target
Git commit, independently of mutable worktree configuration. Invalid or unreadable
configuration and unavailable trusted Git fail explicitly. A candidate cannot
replace, disable or delete an already effective policy. A general policy-update
or deactivation cutover is outside this first-delivery repair.

The required mapping contains:

```yaml
version: knowledge-recognition/v1
enabled: true
product_id: stable-product-id
repository_id: stable-repository-id
minimum_reader: knowledge-operation/v1
owner_activation:
  id: retained-owner-authorization-id
  source: retained-original-authorization
  by: authorized-owner
  decision: activate
human_issuers: [authorized-owner]
observation_issuers: [recognized-observer]
processes:
  - id: owner-selected-process
    version: '1'
    issuers: [recognized-reviewer, authorized-owner]
    kinds: [recognition, applicability, disposition]
policy_digest: digest-of-the-entire-mapping-excluding-this-field
```

Digests are SHA256 of the existing canonical JSON representation (sorted keys,
UTF-8, no NaN); no YAML byte fingerprint is substituted. This is a schema example,
not an owner activation record. The owner must retain actual authorization and
upgrade trusted validation surfaces before activation. The ordinary plan/code
review policy grants no knowledge authority. Stored issuer/process labels follow
the existing local trust model; they are not identity authentication.
Unsupported policy requirements are rejected rather than silently ignored.
After activation, declare a governing Change before the first knowledge operation;
the normal Change command creates the event ledger. A missing activated ledger
is reported as unavailable rather than interpreted as an empty knowledge set.

Activation occurs only when an authorized owner-controlled delivery makes the
policy part of the trusted base and the validation surfaces have been upgraded.
Committing a candidate, an ordinary review approval, or writing `owner_activation`
labels is not an independent grant of knowledge authority or identity proof.
Historical delivery subjects stay unchanged; later actions use the now-effective
policy and satisfy its delivery requirements without rewriting past approvals.
The repair alone did not activate the policy; the later authorized merge into
the actual trusted base did. Historical pre-activation evidence stays historical.

Policy activation affects the repository protocol. A knowledge selector restricted
to one Change limits that knowledge's applicability, not activation itself. Other
Changes must still retain an exact delivery of their current constraint set,
including an empty set. There is no per-Change activation or implicit empty-set
exemption.

## Operations and machine output

Use root options before the group: `keepsail --workspace <repo> --json knowledge …`.
Every JSON result has the existing six keys: command, version, status, exit_code,
data and errors. Human errors go to stderr. JSON errors leave stdout as a single
envelope, and check failures retain their context in data. Exit codes are 0 success,
1 I/O/internal failure, 2 invalid evidence/corruption/unmet obligation, 3 missing
or invalid activated configuration, 4 trusted Git failure, 5 revision/operation
conflict. Importing an explicit reject successfully uses exit 0 while retaining
`decision=reject` and `effective=false`.

`knowledge show` returns the current revision. Each write consumes an explicitly
supplied workspace JSON file with this outer shape:

```json
{"schema_version":"knowledge-operation/v1","operation_id":"unique-operation","expected_revision":"exact-revision-from-show","change_id":"governing-change","version":{}}
```

The final member is `version` for propose, `evidence` for import, or `record` for
record. The input file's original byte digest is retained. Matching operation IDs
and canonically identical inputs return the original receipt, even if JSON
whitespace changes; a reused ID with different
content fails. A stale expected revision fails under the event writer lock before
append. The full log prefix digest is the CAS revision; the semantic basis digest
separately identifies relevant knowledge, applicability and authorization.

`knowledge propose --record <file>` requires an approved governing Change in
implementation. The version object contains exactly schema_version
(`knowledge-version/v1`), product_id, knowledge_id, body, rationale, sources,
selector, authority (`guidance` or `constraint`), and previous_version (null for
the first version). Each source retains origin and content. The CLI returns the
immutable version_digest; the version is a candidate and has no effective authority.

Selectors are either `{"global":true}` or nonempty combinations of repository_ids,
change_ids and paths (arrays). Dimensions use AND; alternatives within a dimension
use OR. Paths are POSIX relative segment prefixes, with no glob/regex: `src/db`
matches its descendants but not `src/db2`. Paths are evaluated against the union
of estimated scope and actual coverage/code manifest. Missing necessary path
context is unknown, not non-matching. Initial scope is not an authorization limit.

`knowledge import --evidence <file>` consumes an operation whose evidence object
contains schema_version (`knowledge-evidence/v1`), evidence_id, kind, subject_id,
decision, process (id/version), issuer, original_evidence, provenance (including
policy_digest), and explicit authorization_effect (`unchanged` or
`requires-human-authorization`). The latter requires a recognized human issuer and
retained human_authorization. Constraint authority/selector changes and exclusions
require that explicit owner authorization; semantic commitment/risk classification
still depends on the recognized process. No failed/empty/skip record grants authority.

Recognition decisions are recognize/reject/retire against an exact version digest.
Retiring an effective constraint also requires explicit owner authorization;
ordinary guidance retirement can use the recognized process's existing authority.
Replacing a version preserves its predecessor and recognition. Applicability
decisions apply/not_applicable name the version and target_change_id. Knowledge
correction alone cannot release work commitments or acceptance obligations.

## Delivery, acquisition and recovery

`knowledge deliver <change> --operation-id <id> --expected-revision <digest>` saves
the full finite constraint set, contemporaneous text, exact recognition evidence,
selection inputs and basis before printing stdout. `prepared` proves retention,
not recipient acquisition; a broken output pipe does not retract the receipt.
Retrying the same delivery returns its original text and reports stale if the
current basis changed. A new operation is required for a fresh delivery.

`knowledge record --record <file>` supports typed statement, challenge,
acquisition, emitted and execution records. A statement names delivery_id,
version_digest, decision (adopt/reject/challenge), and reason. A challenge also
declares dependent_paths or dependency=global. Acquisition names an owner-selected
observer, retained original_receipt, and the SHA256 of the returned body in
returned_content_digest. These observed operations do not prove understanding or
compliance; agent-declared adoption is a different category. Acquisition coverage
is shown per delivery/version, including missing observations.
Manually submitted emitted records are retained as self-reported output statements;
they do not become observations of receipt or native stdout completion.

`change resume <change>` recovers original supplies, current versions, effective
approval, challenges, impact dispositions, action evidence and missing observations.
It is pure read, including when used from a replacement process. `knowledge show
[id] --version <digest>` reads immutable history. Neither read silently records a
new supply or an acquisition.

## Correction and impact handling

`knowledge check <change>` reports unmet obligations and requires an exact retained
delivery of the current effective set. With `--paths <path>` it checks declared
independent-action dependencies; it does not grant execution authority. Challenges
do not release constraints. Global or unknown dependencies cannot be dismissed by
asserting that another path is independent.

After a recorded supplied version changes or is retired/excluded, resume exposes
an impact with an exact impact_id and immutable subject fields. Disposition
uses the approval effective when the knowledge change or challenge was recorded,
captured by the strict writer in its immutable approval_context. Delivery telemetry
cannot choose this baseline. Reapproval preserves that trigger context; a later
knowledge-change trigger captures the then-current approval epoch. Disposition
evidence uses that impact_id as subject_id and the complete subject as impact
(exclude display fields impact_id/status/disposition_id/disposition). Decisions
are continue, adjust, reapprove, not_applicable. Select an explicitly recognized
constraint in use_version; candidates cannot acquire authority via disposition.
Adjust/reapprove also require obligations. Continuation explicitly chooses whether
this work retains v1 or adopts v2. There is no blanket approval revocation or
implicit permission to continue dependent work.

An execution record references disposition_id, outcome
(reported/failed/no-conclusion/verified), retained evidence, subject_id and
fulfilled_obligations. Only the actual current passed verification, assessment,
recognized code review and complete obligation accounting allow verified execution.
Reapprove also requires a different effective plan approval through the existing
plan revision/import flow. The recognized adjustment can enter verification/code
review before its execution is verified; pending judgments still block, and final
check/attestation wait for completion. Statements alone cannot close an adjustment.

Attestation export appends a strictly validated knowledge_checkpointed event and
retains knowledge events across governing Changes without recursively embedding
prior checkpoints. Pure Git validation checks trusted policy, immutable evidence,
current subject/basis and historical knowledge already retained in base
attestations. Local CAS prefixes remain trace receipts, not a cryptographic proof
of the original writer. No local state cache is used as authority.

## Coverage limits

Only global/explicit/recognized recorded applicability is covered. Semantic
omissions, all-agent tool interception, cross-repository product knowledge sharing,
automatic extraction, external retrieval integrations and the full agent loop
remain outside this slice. Historical Changes stay readable with knowledge
coverage=not_recorded. No historical event, decision or receipt is migrated or
retroactively promoted into an observation. Damaged enabled-protocol records fail
explicitly; absence is not substituted for corruption.
