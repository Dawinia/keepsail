---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: dawinialo@163.com
last_reconciled_at: '2026-11-28T12:07:14.448432Z'
last_reconcile_kind: self
last_reconcile_justification: 'Plan 2026-11-27-git-subprocess-cost C5/C9: writer.py
  now expands the prefix bytes it already read under the lock at most once per write
  (a local closure, no module or process state) and hands that snapshot to is_new_contract_event
  and the first event''s precondition validation. Validation still runs against the
  staged copy; the append, completion-transaction and fsync paths are unchanged, no
  existing event is edited, reordered or truncated, and state remains a fold over
  the log.'
reconciled_anchors:
  src/keepsail/core/completion_transaction.py: sha256:f29f29265adeca0210bd7adc839d9abcbf10e131b7970aa4d027c2aee4883b70
  src/keepsail/core/events.py: sha256:58a6d6ff9a0d510d77976e8e9a998b0869c03b27ea44d9e47d73e6bb5126a1cc
  src/keepsail/core/writer.py: sha256:0994d70002d034e8785a257cba2f194dfbdf812e5a0fcbb673c499bc88a6de7d
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
