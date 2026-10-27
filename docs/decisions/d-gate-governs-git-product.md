---
id: d-gate-governs-git-product
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-07-29T13:14:27.000496Z'
ratified_text_hash: sha256:5614ab4fe81201905d53b409478e0e56c63af05ff01b2d5c7b0b3a0ca8f7692b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-27T14:35:43.836165Z'
last_reconcile_kind: self
last_reconcile_justification: Reviewed full gate diff and canonical whitelist branches.
  Existing scratch/plan path allowances are unchanged, canonicalized, disjoint and
  independent of gitignore. Optional entry prerequisites only tighten otherwise allowed
  product edits; no new product/config path allowance. 96 gate tests passed; independent
  exact code review remains required.
reconciled_anchors:
  src/keepsail/gates/pre_tool_use.py: sha256:cdfb8ef62c1e4018899c2871c50b9fa77130a68e67c219970c712896813822b5
---
The pre-tool-use gate governs files that will enter git as product; its allowances are hard-coded path whitelists, never derived from gitignore status.

The gate's job is to stop unreviewed *product* from being written before its plan is
approved. It is not to stop the change from thinking. Blocking a file no reviewer will
ever see buys no safety — it only makes the harness something to route around, and this
project has already watched that happen: with no legal way to revise a rejected plan,
"write it through the shell" became documented procedure in its own pothole list.

Hence the narrowings in `gates.decisions`: the change's plan document (`INTENT_DECLARED`,
`PLAN_PATH_ALLOW_STATES`), its recorded plan artifacts (`PLAN_REJECTED`,
`PLAN_ARTIFACT_ALLOW_STATES`), and its scratch area (`SCRATCH_ROOT`, every state).

**Why allowances are never derived from gitignore status.** "Ignored by git, therefore
harmless" is the obvious shortcut and it is fatal. These are all gitignored:

| path | what it is |
|---|---|
| `.harness/gate-disabled` | the gate's own kill switch |
| `.claude/settings.local.json` | the hook registration that installs the gate |
| `.codex/hooks.json` | the same, for Codex |
| `.harness/state.yaml` | the state the gate reads to decide |

Under a gitignore-derived rule, an agent blocked from editing source could simply write
`.harness/gate-disabled` and the gate would be gone. Allowances must therefore be
hard-coded path whitelists, compared **after** `canonical_relpath` has resolved `..` and
symlinks, so that a traversal out of an allowed prefix lands on its real target and
blocks.

```review
Confirm that every allowance in `gates.decisions` is a literal, hard-coded path or
pattern shape, and that none is computed from gitignore status, `git check-ignore`,
`.gitignore` contents, or any other "is this tracked?" test. Confirm the gate compares
against the CANONICALIZED path (post-`canonical_relpath`), so `..` and symlink escapes
out of an allowed prefix resolve elsewhere and block. Confirm that
`.harness/gate-disabled`, `.claude/settings.local.json`, `.codex/hooks.json` and
`.harness/state.yaml` are reachable by NO allowance in any lifecycle state.

Deliberately NOT armed with an executable check: a `counterexample` block can only ADD a
file, and no added file can make the gate allow a path the whitelists do not name — so
any check written here would pass its bite-test for the wrong reason, i.e. be hollow.
Re-review by reading the four literals whenever the gate paths change.

Still holds -> `decision reconcile d-gate-governs-git-product`; broken ->
`decision betray d-gate-governs-git-product` with a justification.
```
