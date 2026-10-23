---
id: d-fixed-transition-matrix
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:27.695262Z'
ratified_text_hash: sha256:bd22ae2dcac7f0630529e2d42457b809858d2ca19e33a4bf870b1bc76b1ba52b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-23T14:04:06.851142Z'
last_reconcile_kind: self
last_reconcile_justification: Compared the complete anchored modules with 9442ba0
  after normalizing only namespace, environment and product names. No behavior changed;
  decision_check only repoints its sentinel to the ratified successor. Event append-only/frozen
  semantics, pure fold, transition matrix, integrity verdicts, record lifecycle and
  canonical hard-coded gate allowances remain intact. Re-stamp anchors at src/keepsail.
reconciled_anchors:
  src/keepsail/core/transitions.py: sha256:fae754af9ff682663ee904fc90053ef604bdfef21af63984207e1a2e5300d088
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
