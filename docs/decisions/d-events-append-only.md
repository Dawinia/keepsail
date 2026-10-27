---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-27T05:39:25.333689Z'
last_reconcile_kind: self
last_reconcile_justification: Reviewed record type/shape and single newline-terminated
  framing on fresh/resumed recovery, strict shared validation and unchanged original
  prefix. A self-consistent transport checksum cannot admit another event type or
  incomplete framing. Replay stays offline and append-only; independent exact re-review
  required.
reconciled_anchors:
  src/keepsail/core/events.py: sha256:9bed97ea13b9538de6c317051aec8777ba69c16e033eee054055789d068c5967
  src/keepsail/core/writer.py: sha256:43c6d5706cb56fc6390416e208475ffb57d114cd3ae3365abcc9d04bdbe516b2
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
