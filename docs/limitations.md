# Limitations & FAQ

Trust is built on honesty about scope. The following are not in v0.1 — most are
deliberately deferred to a later version; one is blocked by an upstream bug
(flagged explicitly).

## What v0.1 does NOT ship yet

**Explicit knowledge slice:** The [knowledge CLI](knowledge.md) handles finite
global/explicit selectors, immutable supplied versions, recognized corrections and
recorded in-flight impacts in one repository. It does not discover all relevant
knowledge or synchronize a product authority across repositories. Native editor
hooks do not infer knowledge dependencies for every tool or shell command.
Prepared output, observed acquisition, agent statements and actual check outcomes
are distinct. Imported issuer labels do not cryptographically authenticate a
producer. A trusted-base owner activation and upgraded validators are required;
installing this code does not activate a knowledge policy. Old binary behavior is
not retroactively changed by a minimum-reader declaration.

Adjustment may enter verification/code review while its recognized disposition is
executing; final knowledge check and attestation require verified execution.
Reapproval dispositions additionally require a new effective plan approval.
Historical Changes without a knowledge protocol are reported as `not_recorded`,
not retrospectively compliant. Retained snapshots prove the recorded cut, not
unobserved changes in another workspace or service.

**Framework adapters (v0.2+):**
- Spec Kit framework adapter
- BMAD framework adapter

**Agent adapters (v0.2+):**
- Cursor / Aider agent adapters — platform hook capabilities vary. Claude Code is
  the reference v0.1 adapter; Codex ships as an experimental second adapter (see
  [Codex adapter](adapters/codex.md)).

**Custom plugins (v0.2+):**
- Custom sensors / gates / framework adapters loaded from `.harness/*.yaml`
  (`path` + `class`). v0.1 is builtin-only: loading contributor Python in-process
  needs a trust/sandbox model, which lands with the plugins themselves in v0.2. A
  non-builtin entry is rejected — it is not executed.

**Process / orchestration:**
- Reviewer execution and supervision. The owner-recognized external process runs
  reviews and retains original conclusions. keepsail validates subject,
  explicit decision and recognition/provenance; it does not invoke reviewers,
  select models, organize rounds or authorize retries. This boundary is intentional.
- Host-native subagents are an external workflow choice, not a universal core
  primitive. The CLI consumes recognized evidence regardless of how that process
  is organized. It does not prove substantive review quality or cryptographic
  identity in the owner-controlled local trust environment.
- Daemon-autonomous event-driven dispatch — v0.1 uses CLI one-shot dispatchers
  (e.g., `keepsail on-merge` dispatches the merged-event sensors).

**Plan-authoring gate carve-out (reject-loop revision):**
- Recording a change's plan artifacts (so PLAN_REJECTED allows editing them) happens
  only for the **manual `keepsail plan ready`** verb; framework-adapter
  auto-recording is deferred (openspec identifies changes by directory, not a
  `change:` marker, and needs its own sound design).
- A plan document is only recorded if it is a **marked `.md`** (frontmatter
  `change: <slug>`) in the declared scope. Unmarked plans record nothing.
- **Codex** provides no per-file hook input (`file_path` is absent), so the path-based
  carve-out cannot fire for Codex — Codex-driven plan revision uses the
  draft-before-`change start` path. This is fail-safe (Codex is more restricted).
- **Hardlink residual:** a hardlink from a marked `.md` name to a source file shares an
  inode that path resolution cannot detect. This requires the shell to create (the same
  unhooked primitive already conceded), most edit tools break it via write-temp-rename,
  and the content still passes plan + code review + attestation — it is not a new
  capability beyond the conceded shell primitive.

**Plan-path authoring allowance (`INTENT_DECLARED`):**
- Coverage is **path-shaped**. A pattern in `.harness/plan-paths.yaml` must contain
  `{slug}`, so the allowance is always bound to the active change. That guard rail is
  what keeps `AGENTS.md`, `README.md` and `docs/decisions/**` out of it — and it is
  also the source of the gap below.
- **Superpowers artifacts are not fully covered.** That framework identifies its
  artifacts by a `change:` frontmatter *marker*, and its filenames are free-form. A
  repo whose superpowers plan filenames do not contain the slug matches no
  `{slug}`-bearing pattern, so authoring them in `INTENT_DECLARED` stays blocked and
  falls back to drafting before `change start`. Allowing on the marker instead was
  deliberately rejected: the agent can add a marker to any `.md`, which would make the
  governed party the author of its own permission. This is an accepted structural
  trade-off, not an oversight. The shipped skeleton covers superpowers' candidate
  directories for the common case where the filename *does* carry the slug.
- **OpenSpec is covered by default** (`openspec/changes/{slug}/*.md`, shipped enabled),
  because that layout puts the slug in the path by construction.
- **An OpenSpec-driven change still cannot revise a *rejected* plan in-gate.** The
  plan-path allowance is `INTENT_DECLARED`-only; `PLAN_REJECTED` is served by the older
  `plan_artifacts` carve-out instead, and `plan_artifacts` is recorded from the manual
  `plan ready --scope` submission. The OpenSpec adapter emits `plan_ready` with an empty
  payload and no `scope` key (it deliberately refuses to mine a file list out of a task
  checklist), so `plan_artifacts` is always empty for those changes and the carve-out
  never fires. Their reject loop therefore still needs the
  draft-before-`change start` path. The sound repair — apply plan-path patterns in
  `PLAN_REJECTED` *only when `plan_artifacts` is empty*, keeping the two mechanisms
  non-overlapping — is a design change with its own review surface and is not made here.
- The same **Codex** and **hardlink** residuals listed above apply here unchanged: Codex
  supplies no `file_path`, so no path-based allowance can fire for it, and path
  resolution cannot see through a hardlink.

**Gates not yet wired:**
- Cold-path pre-commit / pre-push gates — need git-hook install infrastructure.
- `gate check pr-open` / `gate check pr-merge` — the underlying machinery ships
  via `pr validate`, but the `gate check` wiring is deferred.

**Blocked by upstream:**
- JSON `permissionDecision: deny` for Edit / Write — keepsail currently uses
  exit-2 block instead, because of an upstream Claude Code fail-open bug on
  Edit/deny.

**Platform / integration:**
- MCP integration — v0.2+.
- Windows support — v0.2+; the optional observer host currently uses POSIX
  `os.fork` and `fcntl.flock`.

## FAQ

**Does keepsail run the review or write the verdict?**
No. The recognized external process writes the conclusion. The core checks and
imports its retained evidence against the exact plan/code subject. See
[Concepts](concepts.md).

**Does the report measure all review costs or verification value?**
No. It distinguishes historical issued runs/failures from imported conclusions;
external evidence alone does not establish invocation counts. Usage and money
are recorded subtotals with coverage, and missing values remain unknown.
Structured historical finding dispositions are a limited metric, not total
verification/CI value. See [Report semantics](reporting.md).

**Does it spawn or manage my coding agent?**
No. Your agent calls the harness; the harness gates the agent. See
[Concepts](concepts.md).

**How does a plain-mode change advance past INTENT_DECLARED?**
Plain mode advances with the manual verb `keepsail plan ready`
(INTENT_DECLARED → AWAITING_PLAN_REVIEW); framework adapters emit `plan_ready`
automatically from their artifacts (OpenSpec from `tasks.md`).

**Does the drift gate check my prose docs?**
No. `keepsail doc check` only regenerates docs that have a generator (the CLI
reference, the state-machine diagram). Prose has no ground truth to diff against
and is out of scope by design.

**What does session-bound context establish?**
The [opt-in integration](knowledge-context.md) supplies recorded current approval,
conventions and finite knowledge constraints, and observes complete CLI tool
returns in the selected entry. It separately checks current supply, this epoch's
returns, local dependencies and lifecycle authority. It cannot prove understanding,
semantic compliance or complete recall. Shell/MCP/external writes remain outside
its live editor boundary. Actual host callbacks, two real sessions and recognized
knowledge evolution require their own acceptance evidence; process fixtures do
not prove those facts. Missing symlink privileges can leave platform tests skipped.

New v2 exports retain accepted facts with explicit source digests and local Git
baseline references; they do not publish the original callback bytes or prove
cryptographic identity. Compact observation relies on strict validation at the
local observer boundary. Legacy originals retain their former meaning. Loss of
unfinished v2 retry material can require reacquisition; successful persistence
allows readiness without those temporary callbacks. See
[knowledge formats](knowledge.md#inputs-coverage-and-derived-exports).
