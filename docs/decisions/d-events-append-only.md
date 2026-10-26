---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-26T18:30:50.605819Z'
last_reconcile_kind: self
last_reconcile_justification: Reviewed frozen event, shared effective reader, strict
  recovery transaction and suffix journal. Existing bytes are never mutated, reordered
  or truncated; original source bytes remain in one self-contained log event. Journal
  resumes only the exact suffix and is not state authority. Independent exact code
  review remains required.
reconciled_anchors:
  src/keepsail/core/events.py: sha256:390c267f88379ad3a24540fa7fe27e66673d531ca9115b1849030c5f1b0fd194
  src/keepsail/core/writer.py: sha256:433d84f67b4617edcf9a354406391f6042dcf831f429092b9c663e8b3d855a32
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
