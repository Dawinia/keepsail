---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-10-28T05:12:13.194185Z'
last_reconcile_kind: self
last_reconcile_justification: 'Reviewed full writer: staged temp cleanup only retries
  Windows 5/32/33 for at most 350ms; persistent failure preserves prefix and temp
  before append. Validation, file lock, O_APPEND, fsync, strict recovery journal and
  log-derived state remain unchanged. Transient/permanent lock regressions passed;
  37 historical recovery tests passed. Exact independent code review remains required.'
reconciled_anchors:
  src/keepsail/core/events.py: sha256:bef3a995d3f10d9537cdc07df82d2f6cf52f589c96c825091d8619ec4f66df78
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
