---
id: d-fixed-transition-matrix
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:27.695262Z'
ratified_text_hash: sha256:bd22ae2dcac7f0630529e2d42457b809858d2ca19e33a4bf870b1bc76b1ba52b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-11-28T11:11:52.058370Z'
last_reconcile_kind: self
last_reconcile_justification: 'Plan 2026-11-27-git-subprocess-cost C9: transitions.py
  only adds policy_change_accepted to the informational (non-transition) set; _TRANSITIONS
  is unchanged and compute_target_state remains the sole source of state transitions.
  The new event never changes state.'
reconciled_anchors:
  src/keepsail/core/transitions.py: sha256:02b2bfd20a8f4d2a7be881293c46a475bae00ced603718a56830196e684e3b10
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
