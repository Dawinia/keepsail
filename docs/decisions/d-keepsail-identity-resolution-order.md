---
id: d-keepsail-identity-resolution-order
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-10-23T14:02:35.932361Z'
supersedes: d-identity-resolution-order
ratified_text_hash: sha256:0635403d3ec9b995aace7485eed68bec0d3726632d578629a16239bf3faca765
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-23T14:05:08.612867Z'
last_reconcile_kind: self
last_reconcile_justification: 'Read resolve_identity: override, KEEPSAIL_ACTOR, git
  email, cli in fixed order; stripping and first nonempty behavior unchanged.'
reconciled_anchors:
  src/keepsail/core/identity.py: sha256:b4eaab4999749d991840b119e98dbafc00ba11f3965356d05733822eb5362c9e
---
Identity resolution order is fixed: --as > env > git config > "cli".

```review
`resolve_identity` resolves in the fixed precedence override(--as) > env
KEEPSAIL_ACTOR > git config user.email > "cli"; first non-empty value (after
strip) wins and the result is always non-empty. On any change to identity.py, confirm
this order is unchanged and no source is added or reordered. Still holds -> `decision
reconcile d-keepsail-identity-resolution-order`; broken -> `decision betray
d-keepsail-identity-resolution-order` with a justification.
```
