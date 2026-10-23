---
id: d-keepsail-core-is-base
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-10-23T14:02:31.159634Z'
supersedes: d-core-is-base
ratified_text_hash: sha256:3288f9d22784cfc5b5f40b4ff5e79c11146c8aee921970fd50267f965fc200b9
authoring_time: true
---
core/ is the base layer: it must not import the upper layers cli/gates/sensors/engineering.

`keepsail.core` is the pure foundation the upper layers build on. It must not
depend (directly OR transitively) on the upper layers `keepsail.cli`,
`keepsail.gates`, `keepsail.sensors`, or `keepsail.engineering`, so the
core can be imported (e.g. by the daemon) without dragging in the
CLI/gate/sensor/engineering stack. The faithful mechanical form
of this invariant is an import-graph contract, not a text grep: `grep` sees only direct
textual imports and is blind to the transitive and function-local edges that actually
break layering. The rung-1 check is the import-linter `core-is-base` contract in
`.importlinter`.

(`sensors` is now covered too. Two transitive `core -> sensors` edges both flowed through
`adapters -> sensors` (a `WorkspaceContext` re-export): `core.review_bundle -> adapters`
and `core.sync_check -> engineering -> adapters`. import-linter caught both where grep
declared the code clean. They were severed by moving `WorkspaceContext` into
`core.workspace` (so `adapters` no longer imports `sensors`) and by injecting the
spec/plan-path resolver into `core.review_bundle` instead of importing `adapters` there.)

(`engineering` is now covered too (F9). Besides the transitive path above, there was a
*direct* `core -> engineering` edge the forbidden set had never listed: `core.sync_check`
imported `engineering.agents_md_render` and `engineering.gitignore_injector`. `sync_check`
is sync-orchestration logic that depends on nothing in `core`, so it was relocated to
`engineering.sync_check` (it no longer lives in `core` — do not grep for a `core.sync_check`
edge), and `engineering` was added to the forbidden list. The contract now covers all four
upper layers cli/gates/sensors/engineering.)

```check
PYTHONPATH=src lint-imports --config .importlinter --contract core-is-base --no-cache
```

```counterexample path=src/keepsail/core/_ce_core_is_base.py
from keepsail.cli import plan  # forbidden: core importing an orchestration layer
```
