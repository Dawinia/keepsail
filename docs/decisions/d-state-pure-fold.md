---
id: d-state-pure-fold
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-22T19:25:38.517675Z'
ratified_text_hash: sha256:8a106295b2f00df8c9f657c22e02af8cf6b37cee29ee005e772647d62be48ed0
last_reconciled_by: codex-implementation-session
last_reconciled_at: '2026-11-23T07:31:03.554521Z'
last_reconcile_kind: self
last_reconcile_justification: The reducer clears only per-change derived state based
  on the current event; it does not mutate event inputs or module globals, and identical
  event sequences derive identical state.
reconciled_anchors:
  src/keepsail/core/reducer.py: sha256:347de44b44d51f3c7d6e5429a6cfe5a7998bf9a291ba6211c06362f5e0abd02d
---
State is a pure left-fold over the event log; never mutated in place.

```review
reducer.derive_state is a pure left-fold over the event log: it constructs and
returns a fresh state and never mutates its inputs or any module-level global in
place (logging is permitted; referential transparency is about the returned value).
On any change to reducer.py, re-review the anchored fold: confirm no in-place
mutation of the accumulator or inputs was introduced and that it stays referentially
transparent (same events -> same state). If it still holds, `decision reconcile
d-state-pure-fold`. If purity was broken (in-place mutation or non-determinism
introduced), do NOT reconcile -- `decision betray d-state-pure-fold` with a
justification instead.
```
