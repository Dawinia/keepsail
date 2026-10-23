---
id: d-keepsail-single-gate-policy
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-10-23T14:02:36.491824Z'
supersedes: d-single-gate-policy
ratified_text_hash: sha256:d1c0a806764e84409b7e35ca60d5f70ef52d7dc8fb1a3f4c7f23a809df5080cc
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-23T14:05:09.655775Z'
last_reconcile_kind: self
last_reconcile_justification: 'Read gates.decisions and shared PreToolUseGate reader:
  same four literals, disjoint allowance states and canonical hard-coded paths; hook
  and gate CLI still share the single policy.'
reconciled_anchors:
  src/keepsail/gates/decisions.py: sha256:7646c57c7beabdf2f903fe00667d6be1444a59907e9a794d03bb6469bd2ff892
---
Gate policy lives in one module (gates.decisions); the in-process gate reads it, neither invents nor forks policy.

```review
The gate decision policy lives in one module (`gates.decisions`), now in FOUR
literals: the per-state `PRE_TOOL_USE_DECISIONS` matrix, `PLAN_ARTIFACT_ALLOW_STATES`
(the PLAN_REJECTED plan-artifact narrowing — HG-PLAN-AUTHORING), `PLAN_PATH_ALLOW_STATES`
(the INTENT_DECLARED plan-document narrowing), and `SCRATCH_ROOT` (the per-change
scratch prefix, allowed in every state). The in-process gate (`PreToolUseGate`, shared
by the `keepsail-hook` decision path and the `gate check` CLI) reads these
declarations — it does not invent, hardcode, or fork its own per-state or per-path
allow/block policy, and no future gate may fork them.

Every narrowing only ever turns a `block` into a *specific* allow; none widens to
source:
- plan-artifact: a marked `.md` recorded by the reviewed `plan ready` submission;
- plan-path: a path matching an owner-configured pattern from the tracked
  `.harness/plan-paths.yaml`, where each pattern must contain `{slug}` (binding the
  allowance to the active change) and the RESOLVED path must end in `.md`;
- scratch: the `SCRATCH_ROOT/<change_id>/` prefix only — gitignored, never reviewed,
  never merged.

Two invariants a reviewer must re-confirm on any gate change: (a) the allow-state sets
stay disjoint, so branch ordering cannot change a verdict — there is a unit test in
tests/unit/gates asserting exactly this; (b) allowances are hard-coded path whitelists
and are NEVER derived from gitignore status — see the d-gate-governs-git-product record.

Confirm the reader still defers to this single SSOT module. Still holds ->
`decision reconcile d-keepsail-single-gate-policy`; broken -> `decision betray
d-keepsail-single-gate-policy` with a justification.
```
