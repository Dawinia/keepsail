---
id: d-fixed-transition-matrix
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:27.695262Z'
ratified_text_hash: sha256:bd22ae2dcac7f0630529e2d42457b809858d2ca19e33a4bf870b1bc76b1ba52b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-24T05:51:17.338404Z'
last_reconcile_kind: self
last_reconcile_justification: 'Reviewed the complete transitions.py diff: knowledge
  signals are declared informational in the single existing table; compute_target_state
  and lifecycle transitions are unchanged and no ad-hoc state assignment was introduced.
  Independent code review remains required for this Change.'
reconciled_anchors:
  src/keepsail/core/transitions.py: sha256:21b04c4ac7b8b5327b0f7846ca2d29febc93daf5a9edd237933b3f4e12c55e11
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
