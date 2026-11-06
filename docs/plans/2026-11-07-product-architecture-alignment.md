---
change: 2026-11-07-product-architecture-alignment
stage: plan
tier_hint: Micro
scope:
  - AGENTS.md
  - README.md
  - README.zh-CN.md
  - docs/ARCHITECTURE.md
  - docs/README.md
  - docs/architecture-fitness.md
  - docs/cli-reference.md
  - docs/concepts.md
  - docs/getting-started.md
  - docs/implementation-architecture.md
  - docs/limitations.md
  - docs/overview.md
  - docs/product-architecture-coverage.md
  - docs/product-architecture.md
  - docs/product-foundations.md
  - docs/plans/2026-11-07-product-architecture-alignment.md
  - .harness/attestations/v2/2026-11-07-product-architecture-alignment.jsonl
  - scripts/gen_cli_reference.py
  - src/keepsail/cli/report.py
  - src/keepsail/engineering/agents_md_render.py
---

# Align the documentation set with the product architecture

## Objective and authority

The owner asked, in the current session, for the whole present branch content to
be treated as **one** Change, and for `private/VISION.md` remediation and the
reference-resolution design to be deferred to a later session. The normative
authority for this work is `docs/product-architecture.md`: it states what must
hold; every other live document is expected to agree with it.

This Change brings the live documentation set into agreement with that
architecture, removes facts that no longer match the code, and removes dead
references. It adds no product capability beyond three small source edits needed
to make the corrected statements true.

The one edit to `docs/product-architecture.md` is a **navigational cross-reference**
to `docs/implementation-architecture.md`. It is an *extraction correction* in the
sense of that document's maintenance section: no obligation is added, narrowed or
relaxed, and no commitment change is proposed.

## Commitments

- **C1 — one normative document, one implementation map.** `docs/product-architecture.md`
  keeps stating what must hold. `docs/ARCHITECTURE.md` is renamed to
  `docs/implementation-architecture.md`, its H1 becomes "Implementation
  architecture", and the two documents point at each other: the map is
  descriptive and cannot narrow or extend the normative statement. Every live
  reference resolves to the new path. Historical plans and frozen evidence are not
  rewritten; this Change's own plan document is the only file inside `docs/plans/`
  that lands, and the superseded plan of `2026-11-03-readme-refresh` is not
  carried onto the rebuilt branch.
- **C2 — positioning.** No live document describes keepsail as a harness, as a
  part of the agent, or as responsible for the agent's own reliability. Live
  documents say it is a control layer above the execution harness, and that its
  binding lands on git and CI rather than on any one hook. The evidence is a
  recorded grep for the forbidden formulations plus a hand review:

  ```
  git grep -n -i -E "wire the harness|organs? of the same harness|same harness|is a harness|as a harness|part of the (agent|harness)" -- AGENTS.md README.md README.zh-CN.md docs
  ```

  Its current result is exactly one hit outside the excluded trees:
  `docs/implementation-architecture.md:110`. Three sentences are fixed:
  `docs/implementation-architecture.md:110` ("**Agent adapters** wire the harness
  into an agent's hook surface" → "wire keepsail into the hook surface of a
  specific agent harness"), `docs/concepts.md:131` ("it only makes the harness
  something to route around" → "something to route around" applied to the gate),
  and `docs/getting-started.md:675` ("a fully harnessed repo" → "a fully wired-up
  repo"). The positioning paragraphs of `README.md`, `README.zh-CN.md`,
  `docs/overview.md`, `docs/concepts.md` and `docs/implementation-architecture.md`
  are read by hand and the grep is repeated on the final tree; a remaining hit is
  recorded with why it refers to the *agent harness* and not to keepsail.
- **C3 — drifted facts.** Live documents state the 8-job CI workflow
  (pr-decorate, pr-validate, verification, attest-verify, candidate-acceptance,
  on-merge, decision-check, doc-check — including the enumeration in
  `docs/implementation-architecture.md:92-95`, which today lists only seven and
  omits `candidate-acceptance`), the `on-merge` exit codes 0/1/3, tier-hint
  semantics (a recorded estimate; strictness comes from each check's `must_pass`),
  and the retired review verbs' exit code 2. `docs/cli-reference.md` is
  regenerated from `scripts/gen_cli_reference.py`; it is never hand-edited.
- **C4 — references.** Define the live document set explicitly as `AGENTS.md`,
  `README.md`, `README.zh-CN.md`, and every `*.md` under `docs/` **except**
  `docs/decisions/**`, `docs/plans/**` and `docs/evidence/**` (and `private/**`,
  which is outside `docs/`). Inside that set, every `super_harness` source link
  resolves to an existing `src/keepsail/...` path, and no link points at the old
  `docs/ARCHITECTURE.md`. Evidence is the recorded grep, whose current result is
  zero hits outside the excluded trees:

  ```
  git grep -n -E "super_harness/|ARCHITECTURE\.md" -- AGENTS.md README.md README.zh-CN.md docs
  ```

  Mentions of the former product name that are not paths — the migration guide,
  the overview line and the historical framing in `docs/product-foundations.md` —
  are not references and stay.

  Ratified decisions are hash-locked and intentionally keep historical paths; they
  are read-only for this Change. The `keepsail verify` sentence in `AGENTS.md`
  states what verification actually runs and is identical in `AGENTS.md` and its
  template `src/keepsail/engineering/agents_md_render.py`.
- **C5 — evidence.** `keepsail sync --check`, `keepsail doc check`,
  `keepsail doc refs --gate`, `keepsail decision check --changed` and the affected
  unit tests pass on the final tree. `keepsail attest verify --base <rebuilt
  base> --head HEAD` exits 0 as well — but only after the merge-base prerequisite
  in Delivery is satisfied; if it is not, the Change stops at READY_TO_MERGE with
  the PR still draft and the blocker recorded, rather than claiming mergeability.

## Delivery: merge-base prerequisite, branch reconstruction, lifecycle disposition

**The merge gate reads the review-recognition contract from the merge base.** The
CLI's `review import` validates evidence against the working tree
(`src/keepsail/cli/review.py:345-354`), while `keepsail attest verify` revalidates
the embedded approval against the base commit (`_trusted_recognition(root,
base=...)` at `src/keepsail/engineering/attestation.py:330-348`; policy binding at
`:552-564`). `origin/main` (`7f5de5e`) still recognizes `codex-subagent-review`
(policy digest `41e290b3…`), and the Codex backend is unreachable from this
machine, while this Change's evidence is produced under `dsh-subagent-review`
(policy digest `a1252a5d…`, owner decision recorded in
`.harness/review-recognition.yaml`). Therefore:

0. **Prerequisite (owner action, outside this Change).** The owner lands the
   minimal recognition update on `main` — switching
   `.harness/review-recognition.yaml` to `dsh-subagent-review` — using admin merge
   or a direct push, because that one-file change cannot itself pass the gate it
   reconfigures. This Change neither performs that bypass nor claims it in its
   evidence; it only depends on the resulting base contract.
1. `keepsail change abandon 2026-11-03-readme-refresh --reason "superseded by one
   documentation-alignment Change; its content lands under
   2026-11-07-product-architecture-alignment"`. Its events stay in
   `.harness/events.jsonl` as history; before the rewrite its tip is pushed as a
   backup ref so the disposed lifecycle stays auditable.
2. `codex/readme-refresh` is rebuilt from the **then-current** `origin/main`
   (after step 0), so the trusted base contract matches the evidence. The rebuilt
   branch carries the final tree — the rename, the edits and this plan — and
   neither the old `.harness/attestations/v2/2026-11-03-readme-refresh.jsonl` nor
   the superseded `docs/plans/2026-11-03-readme-refresh.md`. The previous tip is
   kept under a backup ref; PR #138 is updated by force-push.
3. When the Change reaches READY_TO_MERGE, `keepsail attest write
   2026-11-07-product-architecture-alignment` adds the ADD-only attestation, which
   is committed on the rebuilt branch.
4. `keepsail attest verify --base origin/main --head HEAD` exits 0, then the PR
   metadata block is updated and the PR is marked ready for review.

## Explicit restrictions

- Do not touch `private/VISION.md`; its systematic drift is deferred by the owner.
- Do not design or implement the reference-resolution mechanism; that is a
  separate Change in a later session.
- Do not rewrite historical plans or frozen evidence; the sole exception is this
  Change's own plan document.
- Do not change product behavior beyond the three source edits needed for C3/C4
  (`scripts/gen_cli_reference.py`, `src/keepsail/cli/report.py`,
  `src/keepsail/engineering/agents_md_render.py`).
- Do not hand-edit `docs/cli-reference.md`; regenerate it.
- Do not perform or claim the step-0 admin bypass; recognition is owner-owned.

## Out of scope (deferred)

- The seven systematic deviations in `private/VISION.md`.
- "Reference as a first-class edge" (doc_refs identity plus knowledge-source
  origin resolver), which needs its own Change and plan.
- The recognition-policy change itself (step 0), which the owner lands on `main`.

## Risks

- **Merge-gate blocker while the old attestation exists.** Until the branch is
  rebuilt, `attest verify` fails with 21 blockers; the reconstruction removes the
  stale attestation instead of editing it.
- **Recognition contract at the base.** If step 0 does not land, C5's attestation
  check cannot pass; the fallback is READY_TO_MERGE plus a recorded blocker, never
  a bypass.
- **Semantic statements are not machine-checked.** C2 and C3 are prose fixes; the
  four gates and the unit tests cannot detect a re-introduced mis-statement. They
  are covered by the recorded greps, a hand review, and the independent review of
  this Change.
- **History rewrite.** The rebuild replaces nine commits with a new series on a
  draft PR. Content is preserved; the backup ref restores the previous tip.
- **Abandoning a READY_TO_MERGE Change.** The old change is abandoned rather than
  merged. Its attestation and plan document disappear with the rebuilt branch, and
  `.harness/events.jsonl` / `.harness/state.yaml` are gitignored
  (`.gitignore:48-49`), so the disposition is preserved by the pushed backup ref
  plus this plan's record.

## Verification

`keepsail verify` runs the repo's baseline checks (ruff, mypy, pytest). In
addition, `keepsail sync --check`, `keepsail doc check`, `keepsail doc refs --gate`,
`keepsail decision check --changed` and `keepsail attest verify --base <rebuilt
base> --head HEAD` must pass, and the targeted unit tests for the renderer, the
sync check, the CLI-reference generator and doc refs must pass.
