---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-30T18:11:24.428017Z'
last_reconcile_kind: self
last_reconcile_justification: 'Reviewed native writer and derived v2 readers: existing
  physical events are never edited or truncated. New review references and checkpoints
  append through EventWriter. Derived exports use new identities and canonical source
  digests, retain legacy originals, and validate their Git closure. Lazy recovery-prefix
  normalization preserves exact original prefix comparison. Independent exact code
  review remains required.'
reconciled_anchors:
  src/keepsail/core/events.py: sha256:5eed02f5ae5f51038081ee7c9cc5f0b68aa2178d13168b44c75a70bfea3cc196
  src/keepsail/core/writer.py: sha256:041af786a49ec5d1538e58f9c11084992a5ab011c4cf19661eca5d64d2c77f1c
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
