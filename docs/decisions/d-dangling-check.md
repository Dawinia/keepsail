---
id: d-dangling-check
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:28.846809Z'
ratified_text_hash: sha256:d1aa4710844e840396baf69320b33fa30565d79879eb8c0c0ab03d6a7f2273b2
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-23T14:04:07.391697Z'
last_reconcile_kind: self
last_reconcile_justification: Compared the complete anchored modules with 9442ba0
  after normalizing only namespace, environment and product names. No behavior changed;
  decision_check only repoints its sentinel to the ratified successor. Event append-only/frozen
  semantics, pure fold, transition matrix, integrity verdicts, record lifecycle and
  canonical hard-coded gate allowances remain intact. Re-stamp anchors at src/keepsail.
reconciled_anchors:
  src/keepsail/core/decision_check.py: sha256:a3f0db0624c9c69f88ea5ffc5614dd9409e82ba7bb8a7842b094ea6d33374ada
---
CI checks referential integrity: dangling-up blocks, dangling-down warns.

```review
The whole-repo referential-integrity check splits by direction: a dangling-up
reference (a decision/doc anchor pointing at code that no longer exists) BLOCKS (exit
2); a dangling-down anchor (code `@decision:` with no live decision) WARNS only. On
any change to decision_check.py, confirm the up=block / down=warn semantics are
preserved. Still holds -> `decision reconcile d-dangling-check`; broken -> `decision
betray d-dangling-check` with a justification.
```
