# Concepts

## The lifecycle state machine

A *change* moves through a sequence of states. Each transition is caused by a
recorded event; the gate reads the current state to decide what is allowed. The
happy path:

```
INTENT_DECLARED
  → AWAITING_PLAN_REVIEW      (plan_ready, from the framework adapter or `plan ready`)
  → PLAN_APPROVED             (plan_approved, from a reviewer verdict)
  → IMPLEMENTATION_IN_PROGRESS (implementation_started)
  → AWAITING_CODE_REVIEW      (implementation_complete, emitted by `done`)
  → READY_TO_MERGE            (code_review_passed, from a reviewer verdict)
  → ARCHIVED                  (merged, after the PR lands on main)
```

Reviews can send a change back: a rejected plan goes to PLAN_REJECTED (re-emit
`plan_ready` to retry) and a failed code review goes to CODE_REVIEW_REJECTED; a
change can also be ABANDONED. The state machine is fixed, not configurable — see
the generated [state-machine diagram](state-machine.md) for the authoritative
transition matrix.

In PLAN_REJECTED the gate blocks source edits as usual, but **revising the change's
own plan document is authorized**: if `plan ready` recorded the plan doc as a plan
artifact (a marked `.md` in the declared scope), editing that file through the normal
`Edit`/`Write` tools is allowed — the reject-loop revise path needs no shell bypass.
Source files stay blocked; only the recorded marked-`.md` plan doc is editable there.

## Recording what not to do

Some of what you learn while building is negative: don't do this, here be dragons,
doing X also requires Y. super-harness has no separate place for that. A `proposed`
decision record *is* the place.

A proposed record is the state for "we got burned, we haven't settled the rule yet".
Filing one costs nothing — `decision check` excludes anything not yet ratified from every
verdict, so it cannot block a teammate — and it stays out of the tier tally. Its
advantage over a notes file is the **exit**: `ratify` it once you can state the rule (arm
it with a check if the violation has a mechanical signature), or `retire` it once it stops
being true. A note has no exit, which is why notes files fill up with entries nobody can
tell are still valid.

One exception, worth knowing before you act on the above: **filing is free, anchoring is
not.** Attaching a `@decision:` sentinel to a record that is not yet ratified makes it a
dangling-up reference, which is a hard CI failure. Anchoring a record at the site it
describes is otherwise good practice — just wait until the record is ratified.

Two shapes turn up, and only one of them lasts. A **defect** record says "the current
code has this hole"; it names the fix and dies when the fix ships — as a proposed
decision it exits cleanly, whereas as a note it would sit there advising you about a
hole that no longer exists. A **precondition** record says "doing X requires also
doing Y and Z"; no fix retires it, because it constrains code not yet written. The
second kind is what is worth ratifying.

This is not a preference. Standalone lessons-learned repositories have a documented
failure record — NASA's LLIS, audited in OIG report IG-12-012, went years with only
one contributing center and could not be searched usefully by its own knowledge
architect. The forms that survive in the field all impose an entry condition:
an executable detector (Clippy's lints), a subject stable enough not to move
(PostgreSQL's "Don't Do This"), or a named replacement (the AntiPatterns catalogue).
A decision record can carry all three, and adds two those forms lack: a lifecycle
that retires it, and anchors that flag it as suspect when the code it describes
changes.

## super-harness does not review your code for you

The core checks recognized external evidence before implementation and merge.
The owner enables `.harness/review-recognition.yaml` for a process, issuer,
version and evidence form. The external process supplies an explicit approve or
reject conclusion, original evidence and provenance for the exact frozen subject;
`review import` validates and records that conclusion. Execution, retry policy and
substantive judgment belong to the external process. Failure, empty output and
skip are not approval. The core does not mechanically prove reviewer quality or
identity beyond the owner-controlled recognition/evidence contract.

Plan approval covers commitments and explicit restrictions. Within those bounds,
new fixtures, file additions and implementation-method changes use
`implementation record --assessment` to retain reasoning and actual coverage.
Changing commitments or relaxing restrictions requires `plan redeclare --plan`
and approval of the new candidate. A changed Git HEAD alone does not revoke plan
approval; code review and verification still need an accurate current subject.
Use `implementation reopen` for code fixes after freezing completion, then refresh
verification and code evidence. Finish or explicitly withdraw a pending revision
before delivery under the previously approved commitments.

After `CODE_REVIEW_REJECTED`, edits are allowed but the rejected code subject stays
frozen. `verify` records a result for the current commit; it does not re-submit the
implementation or replace that frozen subject. For corrected code, run
`implementation reopen <change> --reason "<why>"`, update the implementation
assessment/coverage, commit, and run `done <change>`. This preserves plan approval
and rejection history, clears the previous code/verification projection, and then
freezes the freshly verified subject in `AWAITING_CODE_REVIEW`. Import recognized
external evidence for that exact subject to reach `READY_TO_MERGE`. An approval
for an older subject cannot approve the new commit. A rejected plan still requires
plan revision and recognized plan approval; code recovery cannot bypass it.

`status` shows authority and current evidence. Historical reviewer governance,
profiles, rounds, failures, skips and authorizations remain readable as history.
Removed execution commands are described as retired in the CLI reference and
cannot advance a new Change. See [Getting started](getting-started.md) for the
current workflow and [Report semantics](reporting.md) for observation boundaries.

## super-harness does not spawn your agent

Your agent or terminal calls the harness through hooks and CLI. The harness gates
implementation and validates retained evidence. The external review workflow owns
invocation, retries, source retention and reviewer instructions; the core has no
model selection, automatic rounds, retry budget or human nonce executor.

## What the gate governs

> The gate governs files that will enter git as product. It does not govern the
> change's own thinking artifacts.

That one sentence explains every narrowing in the state table:

- **Source stays blocked** until a plan is approved — that is the whole point.
- **The change's plan document is writable in `INTENT_DECLARED`**, at any path
  matching `.harness/plan-paths.yaml` (default `docs/plans/*<slug>*.md`). Every
  pattern must contain `{slug}`, so the allowance is bound to the active change and
  can never name `AGENTS.md` or a ratified decision record. That file is *tracked*,
  so widening the allowance is itself a gated edit.
- **The change's scratch area `.harness/scratch/<slug>/` is writable in every
  state**, including terminal ones. It is gitignored, never enters a review bundle,
  and never reaches a merge gate — blocking it would prevent nothing and would only
  push an agent toward the shell to get around the gate.

Blocking a file the reviewer will never see buys no safety; it only makes the
harness something to route around. See [Limitations](limitations.md) for the
residuals.

## Two gate paths

- **Hot path** — the PreToolUse gate, decided in-process from a single
  `state.yaml` snapshot, blocks Edit / Write tool calls in Claude Code (and
  `apply_patch` in Codex, experimental — see [Adapter docs](adapters/)) when the
  current state forbids them. No resident process is on the decision path.
- **Cold path** — CI gates on the PR: metadata + lifecycle-state validation, the
  verification-runner sensor, and the merge gate.
