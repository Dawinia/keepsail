# Product architecture

This is the normative product definition and architecture of keepsail.
The product owner confirmed these meanings through product-design discussion on
2026-10-21 and 2026-10-22, then confirmed the complete account. This publication
does not assert that the implementation already satisfies it.

Architecture governs implementation discrepancies: record a gap rather than
narrowing the obligation to fit code. Changing this architecture requires product
authority. This does not authorize bypassing existing gates, rewriting historical
evidence or hand-editing ratified decisions. See the separate dated
[implementation coverage](product-architecture-coverage.md).

## Purpose and positioning

Keepsail is a product-work control layer across agent harnesses. It
serves developers and product owners using agents for software work. It keeps
effective human commitments and long-lived product knowledge consequential across
continuous work, enables agent autonomy within approved bounds, and makes
deviations, knowledge evolution and completion evidence traceable.

A product is the long-lived governance scope and can span repositories. A Change
is one unit of work with its own objective and authorization boundary. Product
knowledge persists across Changes and sessions: product concepts, project style,
technology choices, rationale, and positive and negative experience.
AGENTS.md is one carrier of knowledge, not its entirety or an independent source
of authority.

## Foundations and selected boundaries

| Historical ID | Recovered foundation or retained principle |
|---|---|
| F1 | Work must not silently depart from effective human commitments or present unmet obligations as completion. |
| F2 | Recorded commitments, knowledge, approvals and unresolved matters must survive individual sessions. Complete recovery of all reasoning is not promised. |
| F3 | Knowledge can be formed, used, tested, revised, superseded and retired, with the basis and authority changes preserved. |
| F4 | Shared product meanings are independent of a particular agent or specification framework; Keepsail is positioned above execution harnesses. Equal integration coverage does not follow. |
| F5 | Reliability principles do not change solely with personal, team or enterprise identity; work policies may differ. This retained principle was not amended in this discussion. |

F1–F3 organize the confirmed purpose and responsibilities. F4 expresses the
confirmed positioning choice; F5 retains the earlier account. Their historical
axiom classifications remain candidates, not newly ratified architecture decision
records. Present confirmation does not establish unknown historical origins.

Necessary consequences include recoverable recorded authority (F1/F2), visible
handling of governed deviations (F1), and revisable rather than write-only knowledge
(F3). They do not uniquely derive event logs, hooks, formats, fixed state names,
CI or any particular storage or retrieval system.

The following are confirmed product choices, not unique deductions:

- Implementation requires an approved plan. Approval grants autonomy within
  commitments and explicit restrictions. New files, implementation-method changes
  or a new Git HEAD alone do not revoke it.
- Changed commitments, relaxed restrictions or changed risk acceptance need
  appropriate authorization.
- People decide recognition policies. Authorized external processes may perform
  routine knowledge confirmation, applicability judgments and review automatically,
  without a person confirming every execution. Product goals, foundations,
  authority and risk-boundary changes remain with the authorized human.
- Keepsail does not own the complete agent execution loop, universal semantic
  understanding or complete knowledge recall. Independence requirements for
  reviewers are project policy rather than an intrinsic control-layer requirement.

The earlier [plan-authority foundation record](product-foundations.md) preserves
the authority and dated context of that local evolution; its historical
pre-implementation wording is not a current coverage verdict. The earlier P1
(repository Changes as governance units) is refined here: a Change remains the
work/authorization unit, while product knowledge can outlive it and span
repositories. P2's separation of policy/semantic judgment from mechanical
validation remains in the responsibilities below. No implementation migration
is claimed by these product-level statements.

## Domain meanings

| Concept | Meaning |
|---|---|
| Commitment | Authorized objectives, expected behavior, acceptance obligations and explicit restrictions. |
| Product knowledge | Long-lived understanding, concepts, style, choices, rationale or experience, with provenance and applicability. |
| Change | Work that uses commitments and knowledge and has an objective and approval boundary. |
| Recognition policy | Project rules specifying which process, evidence and conclusions can acquire which authority. |
| Applicability relation | A link between knowledge/commitments and work, established by explicit scope, declaration or recognized external judgment. |
| Evidence | Support for a judgment or claim, bound to its object, version and coverage. |

Knowledge has independent dimensions:

- State: candidate, effective, challenged, superseded or retired.
- Applicability: the contexts, work and versions for which it holds.
- Authority: effective guidance or an effective constraint.

Not adopting guidance is not itself a violation. Applicable constraints must be
respected and cannot be downgraded by the implementation agent. Lack of an
executable check does not turn a constraint into mere guidance. Recognition does
not make knowledge permanently true.

Agents can propose and, within task authority, consult or test candidate knowledge.
Candidates do not thereby acquire authority over later work. Finding, using,
checking and recognizing knowledge are distinct facts. New evidence can challenge
knowledge but cannot automatically release a human commitment. Writing a rule
into a knowledge document does not itself recognize it.

## Capability architecture

| ID | Required outcome | Upstream relationship |
|---|---|---|
| C1 — continuity | Recover recorded commitments, knowledge states, approvals and unresolved matters when replacing a session or executor. | Required by F1/F2. |
| C2 — work authorization | Establish approved bounds, distinguish within-bound implementation adjustments from commitment changes, and support autonomy for the former. | F1 and the confirmed plan-authority choices. |
| C3 — applicability and bounded delivery | Establish the applicable constraint set using explicit scope, matching and recognized judgments. Deliver effective constraints declared globally applicable or selected by explicit matching rules. | Selected control-layer delivery responsibility; not complete semantic recall. |
| C4 — knowledge evolution | Form candidates from discoveries; recognize, revise, supersede or retire under policy; preserve evidence and prevent authorization bypass through knowledge edits. | Required by F3, subject to the selected recognition authority. |
| C5 — bounded control and deviations | Enforce preconditions and configured checks on declared integration surfaces; handle failures, exceptions and disputes explicitly. | Required by F1 within the selected coverage boundary. |
| C6 — work trace | Preserve knowledge identity, contemporaneous version, provenance, delivery and observable acquisition, separating agent statements from check facts for later review. | F1/F2 and the explicitly selected traceability responsibility. |

The capabilities form a loop: long-lived records inform a Change's constraints and
approval; the execution harness performs work; checks and review yield results,
evidence and new candidates; recognized changes update long-lived records and
feed back to linked work. C1 restores those relationships. C6 makes their recorded
basis inspectable; it does not replace C3 delivery or C5 checking.

Recognizable failures include losing an approval on session replacement (C1),
restarting approval merely for an in-bound fixture addition (C2), failing to deliver
an explicitly selected constraint (C3), silently granting candidate authority (C4),
laundering a required check failure (C5), and losing the version actually supplied
to work (C6).

## Responsibility and trust

| Participant | Responsibility |
|---|---|
| Product/project owner | Commitments, recognition policy, risk acceptance and authority boundaries. |
| Execution agent harness | Context retrieval, semantic reasoning, tool invocation and execution. |
| Recognized external process | Semantic applicability, knowledge assessment and review conclusions; may execute automatically. |
| Keepsail | Records, state, authority relationships, workflow preconditions, control and trace; validates recognized source, object and explicit conclusion without re-performing substantive review. |

Keepsail can mechanically match explicit scope. It does not promise to discover every
semantic relation. A received applicability judgment proves completion of a
prescribed process, not absence of omissions. A project's applicability policy
can require judgments; an agent's assertion of completeness is not completeness
proof. Owner-controlled recognition is not cryptographic identity or proof of
review quality.

## Change, challenge and recovery

Long-lived knowledge/constraint changes must expose changes on recorded links to
ongoing work. A recognized process decides applicability and whether approval
remains suitable; Keepsail records and applies that conclusion. Neither universal
approval revocation nor automatic continued validity is the default inference.

A challenge does not itself release a constraint. Actions that require violating
the disputed constraint wait for authorized resolution; independent work can
continue. Knowledge updates must not silently overwrite prior grounds. Later
review must be able to recover the version supplied at the time, rather than
judge past actions as though today's knowledge had always applied.

## Trace and guarantee boundaries

Distinguish what Keepsail supplied, what observed retrieval/read operations returned,
what the agent stated it adopted/rejected/challenged and why, and what result
checks verified. Record identity, version and provenance within the observable
integration boundary and disclose missing observations.

Supply or reading does not prove understanding or adoption; agent statements do
not prove compliance. Absence of a record cannot prove absence of exposure when
other context sources are unobservable. Unchecked, failed, no-conclusion and
passed are different states. Traceability supports investigation without claiming
access to private reasoning.

Keepsail does not guarantee complete recall, correct semantic judgments, absence of
omitted knowledge or correct code. Source configuration, package publication,
installed behavior, CI execution and required branch protection are separate
evidence layers.

## Semantic scenarios

1. **Omitted recall.** Failure to deliver an explicitly global/matched constraint
   is a delivery gap. Unidentified semantic relevance remains a disclosed limit.
   Traces support investigation without proving completeness.
2. **Mistaken recognition.** A local command failure is overgeneralized into a
   platform rule. Counterevidence can challenge it; recognized correction adjusts
   its scope/state while preserving prior recognition and use history.
3. **Authorization bypass.** An unstable test is a factual candidate; permission
   to skip an acceptance test changes an obligation and cannot be obtained merely
   by recognizing ordinary knowledge.
4. **In-flight choice change.** A technology constraint changes while Changes
   are underway. Recorded relations expose the impact; recognized judgments
   decide continuation, adjustment or renewed approval. A replacement session
   can recover the issue and its resolution.

## Maintenance

This is the normative product account. Keep evidence updates in the separate
coverage document. Classify future edits as extraction corrections, capability
evidence updates or actual commitment changes. Preserve unknown history and the
authority of new choices. Existing ratified decisions retain their recorded
history; conflicts require explicit governed handling, not silent rewriting.
