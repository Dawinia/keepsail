# Overview

Keepsail is an open-source product-work control layer across agent harnesses.
For each change, the owner sets the objective, acceptance criteria and limits.
The agent works within that approval. Keepsail records decisions and deviations
and checks whether the evidence for delivery covers the work being submitted.

This overview explains the workflow. The [product architecture](product-architecture.md)
defines the responsibilities; the dated [coverage report](product-architecture-coverage.md)
separates implementation evidence from outstanding obligations.

## The problem

Software work often spans many agent sessions and changes. A later session needs
to know what was approved, which constraints still apply, why a choice was made,
and which issues remain unresolved. Meanwhile, implementation discoveries need
room to be handled without asking a person to approve every added fixture or file.

Keepsail records these relationships and checks them at configured workflow and
tool boundaries. The execution agent continues to reason, retrieve context and
use tools; the owner determines authority and recognition policies.

## How the pieces fit

A **Change** is a unit of work with an objective and an approval boundary.
**Commitments** are its authorized objectives, expected behavior, acceptance
obligations and explicit restrictions. **Product knowledge** can outlive a Change:
concepts, conventions, technology choices, rationale and experience.

The normal work path is:

```text
Declare → Plan review → Implement → Verify → Code review → Merge and archive
```

An owner-recognized process supplies plan and code review conclusions. Keepsail
checks their object, explicit decision, provenance and retained evidence. It does
not choose reviewers, run models or retry reviews. A failed, empty or skipped
review cannot become an approval.

Approval allows the agent to adjust implementation within the commitments and
record its reasons and actual file coverage. Changed commitments or relaxed
restrictions require appropriate new authorization. Verification and code review
must still match the current implementation, even when the plan approval remains valid.

## Example: deliver an export without breaking existing readers

Suppose a team approves a CSV export on the condition that existing readers can
still consume it. The plan includes a compatibility test. During implementation,
its agent discovers that it needs an extra fixture. It can add the fixture and
record how it supports the approved test. Removing the compatibility requirement
would change the promised outcome and requires renewed approval.

Meanwhile, the project recognizes a new version of its naming convention for CSV
columns. Keepsail can show that this change received the previous version. The
team's recognized process may decide that the export should keep the old names
to preserve compatibility. A later session can recover that decision, the plan
and any unresolved work. See [knowledge delivery](knowledge.md).

At delivery, the reviewer and the configured checks need to cover the actual
export implementation. If a patch changes it after review, the old conclusion
covers only the earlier code. The plan can still stand while verification and
review are refreshed for the revised implementation.

## What is implemented

| Area | Current mechanisms |
|---|---|
| Work authorization | Plan snapshots, effective approvals, implementation assessments, actual coverage and current code subjects. |
| Knowledge evolution | Immutable versions, recognized authority and applicability, retained deliveries, challenges and impact dispositions within one repository. |
| Continuity | Event-based recovery of recorded work and knowledge; optional session-bound context delivery and retrieval observation. |
| Local control | Agent hooks check selected edits against lifecycle rules; context mode also checks current context and dependent impacts. |
| Decision conformance | Ratified decision text hashes, code anchors and optional executable checks tested against counterexamples. |
| Completion evidence | Verification, external review import and Git-based attestation checks for the corresponding change. |
| Integrations | Claude Code and experimental Codex adapters; OpenSpec, Superpowers and Plain workflows; a bundled GitHub Actions workflow. |

The optional [session context integration](knowledge-context.md) binds a session
entry to an explicit Change, supplies the applicable recorded context and validates
complete tool returns before recording acquisition. A new entry requires fresh
retrieval. Its selected real-acceptance target is Windows local Codex desktop;
the guide and [acceptance note](harness-context-acceptance.md) distinguish that
evidence from earlier Claude implementation and fixture coverage.

## Boundaries

Local hooks require installation, host trust where applicable, and actual callback
delivery. They intercept selected agent edit tools, not arbitrary manual, shell
or MCP writes. Legacy and context modes also have different failure handling;
installation alone does not establish protection. CI only constrains merges when
its checks are deployed and required by branch protection.

The product's long-term scope can span repositories, but current knowledge authority
and delivery are local to one repository. Explicit matching and recognized
applicability judgments do not provide complete semantic recall.

Keepsail distinguishes supplied content, observed acquisition, an agent's adoption
or challenge statement, and check results. Reading is not proof of understanding;
statements are not proof of compliance. Recognized provenance is not cryptographic
identity or a guarantee of review quality.

## Where to start

- [README quickstart](../README.md#quickstart): install from source and observe a local gate.
- [Getting started](getting-started.md): follow the change lifecycle and configure review.
- [Knowledge](knowledge.md) and [session context](knowledge-context.md): configure continuity and delivery.
- [Adopting](adopting.md): connect architecture decisions to checks.
- [CLI reference](cli-reference.md) and [implementation architecture](implementation-architecture.md): inspect commands and implementation.
- [Migration guide](keepsail-migration.md): upgrade from the former super-harness name.

For help or contributions, see the [README](../README.md#help-and-contributing).
