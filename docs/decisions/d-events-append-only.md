---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-11-12T16:48:09.080372Z'
last_reconcile_kind: self
last_reconcile_justification: 'Reviewed writer and event expansion: completed transactions
  append only, recovery appends verified suffixes, and temporary journals never replace
  or truncate event history. Power-loss durability remains a platform-specific acceptance
  boundary.'
reconciled_anchors:
  src/keepsail/core/events.py: sha256:300a74f9afc2637cf72466a30b4161333c3bb2281d177c8a58dda396e525ea4a
  src/keepsail/core/writer.py: sha256:5e83599588bcca55830219363425964096987a52fb790c68e4c0e639eeaf7c94
---
Events are append-only; the log is the source of truth, state is derived.

```review
The Event dataclass is frozen and events.jsonl is append-only: events are appended
and never edited, reordered, or truncated in place; the log stays the single source
of truth and all state is a derived fold over it (see d-state-pure-fold), never
persisted as the authority. On any change to the Event model or the event writer,
confirm no path mutates/truncates an existing event and that state remains
log-derived. Still holds -> `decision reconcile d-events-append-only`; broken ->
`decision betray d-events-append-only` with a justification.
```
