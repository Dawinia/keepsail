---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-24T05:51:16.869981Z'
last_reconcile_kind: self
last_reconcile_justification: 'Reviewed the complete events.py diff: only fixed knowledge
  event names were added; Event remains frozen, serializer and append-only writer
  are unchanged, no mutation/truncation path was added. Independent code review remains
  required for this Change.'
reconciled_anchors:
  src/keepsail/core/events.py: sha256:e68e8cec3ffbab7c40625991bf234a1e1cc24281bb2fea5cd80b96ba3010cae2
  src/keepsail/core/writer.py: sha256:eb72a1f4776295fef635cdd8e1ec074009d3ea8e1cb4ffea15f11775ea51aa96
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
