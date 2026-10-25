# Replacement-executor handoff: real v1 use still pending

This is a concrete handoff prepared under P6, not authorization to create another
session. Ask the owner to authorize opening the next session after reviewing it.
Do not mark the pilot complete or run `done` while required real use remains pending.

## Identity and retained authority

- Repository: `E:/Work/keepsail`, product `keepsail`, repository ID `Dawinia/keepsail`.
- Work branch: `codex/knowledge-cli-pilot`. Inspect its actual HEAD/worktree before
  acting; this handoff and associated evidence are committed on that branch.
- Change: `2026-10-25-knowledge-cli-pilot`, implementation in progress.
- Governing plan: `docs/plans/2026-10-25-knowledge-cli-pilot.md`, confirmed by the
  owner with "开始" and approved by the independent recognized process.
- Effective approval: `approval:pilot-plan-review-20261025-a75436eb-independent-01`.
- Exact plan subject: `plan:a75436eb347d7d545dce2c1ff15672248ee5caea9644a73f80c629b6140bc0e9`.
- Last observed trusted base: `202171797aaf6899a1a44e51ef1451b0f13a6384`.
- Knowledge policy: `8837f4d7a4fede285eef7d8a15ab450ee70ea779e0580ac90f27cf9efbb86337`.
- Use the explicit repository `.venv/Scripts/keepsail.exe` with `PYTHONUTF8=1`;
  verify actual module paths and resolver output again. The global PATH executable
  was under the historical super-harness virtualenv; do not infer imported source
  from its filename or run repository operations in that old checkout.

## Recover the real supply and unresolved matters

Read AGENTS.md, normative `docs/product-architecture.md`, `docs/knowledge.md`,
`docs/knowledge-pilot.md`, the approved plan and current acceptance record.
Run actual native commands and retain argv, stdout/stderr and exit codes:

```text
keepsail --json change resume 2026-10-25-knowledge-cli-pilot
keepsail --json knowledge show delivery-evidence-boundary --version 0f240f5f1e72ee8bc72665e18ad16ad0d3b06615e0e9fd371007ff8531bb04cb
keepsail --json knowledge check 2026-10-25-knowledge-cli-pilot
```

Original supply ID: `pilot-effective-v1-delivery-20261025-01`.
Version: `0f240f5f1e72ee8bc72665e18ad16ad0d3b06615e0e9fd371007ff8531bb04cb`.
The owner recognized this exact v1 with "认可该确切 v1 为上述范围内的约束".
Native import evidence: `pilot-owner-recognition-boundary-v1-20261025-01`.
Body: 交付、可观察获取、agent 采用声明、检查结果必须分开记录；缺失获取或检查不能宣称已读、已理解或已合规。
Selector: repository `Dawinia/keepsail` AND this Change; authority constraint.
Original basis: `cbdf463be391a6766a42ceec973aba293898f5cd0d58fd4017028e81dd0f7e92`.
After recording actual file coverage, a second exact current-context delivery
`pilot-v1-handoff-coverage-delivery-20261025-01` was retained. Its original stdout
is `docs/evidence/knowledge-cli-pilot/v1-handoff-delivery.json`. No separate
acquisition/adoption is recorded for that second delivery; distinguish this
missing observation from the prior original-supply acquisition below.
Prior acquisition: `pilot-v1-acquisition-20261025-01`; prior adoption statement:
`pilot-v1-agent-adoption-20261025-01`. They belong to the previous executor;
do not claim them as the replacement executor's own observed acquisition or use.

Last observed real impacts/challenges were empty; no v2 exists. Recheck actual
records. Isolated challenge fixtures are not real unresolved work. New HEAD or
files within the existing approved bounds do not revoke the approval. Existing
unrelated baseline/alignment Changes must not be transitioned as a demonstration.

## Required real documentation action

After recovering the original supply/current version/approval/pending obligations,
the replacement executor must add a concrete `Replacement executor use` section
to `docs/knowledge-pilot/acceptance.md`. State what the native recovery actually
returned and maintain separate supplied, observed-acquisition, agent-statement
and check-result fields. Include real source-session and command evidence, any
missing observations and exact original version. This is already within P1/P6.

If the selected observer captures actual returned body and original receipt,
record a new acquisition for this executor against the original supply and exact
version (or clearly distinguish a new native supply). Use its actual body SHA256
and original receipt; no invented observation. Record this executor's adoption
statement separately. New native operations require unique operation IDs and the
then-current show revision. Read/resume alone must not be described as writing a
new supply or proving understanding. Retain the actual resulting document diff
and fresh decision/doc/knowledge checks separately from the declaration.

## Remaining approved work and reserved decisions

Only after real v1 recovery/use, prepare a justified narrow v2 correction under
P7; preserve v1 and its supplied text. Exact v2 recognition still belongs to the
owner. Propose first, present actual returned digest plus full text, and wait for
the owner's concrete conclusion before import. Generic prior approval is not
recognition. After v2 recognition, recover the exact impact and its trigger approval
context; present it to the owner for continue/adjust/reapprove disposition and an
explicit chosen version. Do not auto-continue, auto-revoke or self-report closure.

Finish assessment/coverage and native verification/code review/attestation only
after actual obligations are met. Runtime fixes require a separate root-cause and
repair/test plan plus owner confirmation; this pilot authorizes no source patches.
No more user sessions are authorized by this handoff itself.

Preserve untracked `.superpowers/`, `docs/research/`, and the retained
`.harness/.events-7byibijm.tmp` from the failed earlier attempt. Do not replay that
temporary file as authoritative history. Do not hand-edit events/state/receipts.
