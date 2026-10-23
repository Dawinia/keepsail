---
id: d-decision-records
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:29.090702Z'
ratified_text_hash: sha256:b2ee29066411206363cb90de2251e44e17d4f53bca0c4d4018fc9dd538f4badd
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-23T14:04:07.906580Z'
last_reconcile_kind: self
last_reconcile_justification: Compared the complete anchored modules with 9442ba0
  after normalizing only namespace, environment and product names. No behavior changed;
  decision_check only repoints its sentinel to the ratified successor. Event append-only/frozen
  semantics, pure fold, transition matrix, integrity verdicts, record lifecycle and
  canonical hard-coded gate allowances remain intact. Re-stamp anchors at src/keepsail.
reconciled_anchors:
  src/keepsail/core/decisions.py: sha256:72f807061b65b67e7cf3d67d6048c950667915d08e91364592a0c68567ba694a
---
Decisions are one-file-per-record under docs/decisions/, four-state lifecycle.

```review
Decisions are stored one-file-per-record at docs/decisions/<id>.md with a four-state
lifecycle (proposed -> ratified -> superseded / retired). The loader in decisions.py
enforces this shape; there is no multi-record file and no fifth state. On any change
to decisions.py, confirm the one-file-per-record model and the four-state lifecycle
are preserved. Still holds -> `decision reconcile d-decision-records`; broken ->
`decision betray d-decision-records` with a justification.
```
