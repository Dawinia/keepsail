---
id: d-events-append-only
status: ratified
ratified_by: dawinialo@163.com
ratified_at: '2026-06-26T09:45:08.963090Z'
ratified_text_hash: sha256:8db7275f6ea859c6e8ada8b4e77ec8a954024d45bffcc6a822ede1d62f69254b
last_reconciled_by: codex-implementation-session
last_reconciled_at: '2026-11-23T07:31:12.466939Z'
last_reconcile_kind: self
last_reconcile_justification: The writer adds a completion journal, staged validation,
  binary append and recovery by appending the verified missing suffix; readers expand
  only complete validated transactions. Existing event bytes are not edited, reordered
  or truncated, and state remains derived from the log.
reconciled_anchors:
  src/keepsail/core/completion_transaction.py: sha256:f29f29265adeca0210bd7adc839d9abcbf10e131b7970aa4d027c2aee4883b70
  src/keepsail/core/events.py: sha256:8f03174f371da76beace629706cbff2c7238c952572dee309f1d31a23bb84a94
  src/keepsail/core/writer.py: sha256:db4d1ab1b29f581f20c588a14c128e6a8dcc09981f59bf47140d7669c3360f39
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
