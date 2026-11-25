---
id: d-fixed-transition-matrix
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:27.695262Z'
ratified_text_hash: sha256:bd22ae2dcac7f0630529e2d42457b809858d2ca19e33a4bf870b1bc76b1ba52b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-11-12T16:48:15.165052Z'
last_reconcile_kind: self
last_reconcile_justification: 'Reviewed transition handling: the no-review event has
  one explicit matrix entry, and reducer state changes continue to use compute_target_state.'
reconciled_anchors:
  src/keepsail/core/transitions.py: sha256:724a5c540a5445a1c5e088fa3853d5cf322b1a3cfae059ceb5fc93f694d4517b
---
State transitions come only from the fixed declared matrix; no ad-hoc transition.

```review
Every state transition is looked up in the fixed declared `_TRANSITIONS` matrix (via
compute_target_state); no module computes or assigns a change's state through an
ad-hoc transition outside this table. On any change to transitions.py, confirm the
matrix remains the sole source of transitions and no hardcoded/ad-hoc state change
was introduced elsewhere. Still holds -> `decision reconcile d-fixed-transition-matrix`;
broken -> `decision betray d-fixed-transition-matrix` with a justification.
```
