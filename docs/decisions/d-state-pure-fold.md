---
id: d-state-pure-fold
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-22T19:25:38.517675Z'
ratified_text_hash: sha256:8a106295b2f00df8c9f657c22e02af8cf6b37cee29ee005e772647d62be48ed0
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-23T14:04:06.345620Z'
last_reconcile_kind: self
last_reconcile_justification: Compared the complete anchored modules with 9442ba0
  after normalizing only namespace, environment and product names. No behavior changed;
  decision_check only repoints its sentinel to the ratified successor. Event append-only/frozen
  semantics, pure fold, transition matrix, integrity verdicts, record lifecycle and
  canonical hard-coded gate allowances remain intact. Re-stamp anchors at src/keepsail.
reconciled_anchors:
  src/keepsail/core/reducer.py: sha256:6d7624bf5e5110e5643ececc50d100a12b8924c3737dfdb673530f770becd229
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
