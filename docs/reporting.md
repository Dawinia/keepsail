# Report semantics after plan-authority cutover

`super-harness report` reads the existing ledger and gate-block telemetry. It
does not execute reviewers or modify history. `--brief` carries the same limits;
`--json` exposes per-record details in `cost_breakdown`. For current approval
applicability, use `status` and attestation, not aggregate report counts.

## Review observations

| Field | Meaning |
|---|---|
| `review_rounds_started` | Distinct historical round-start records in the window. |
| `review_attempts_started` | Distinct run IDs issued in those starts. This is not proof of invocation. |
| `review_execution_failures` | Distinct historical run IDs with a recorded failure in the window; can include intentional nonexecution. |
| `review_rounds_execution_failed` | Historical closures labelled execution_failed, separately from run failures. |
| `review_results_imported` | Distinct old result imports; not starts, failures or lifecycle mirrors. |
| `external_conclusions_imported` | Distinct new evidence IDs imported, including superseded/historical evidence. |
| `external_approvals`, `external_rejections` | Explicit decisions in those new evidence records; not counts of currently applicable approvals. |
| `review_skips` | Historical plan/code milestones explicitly marked skipped; not approval. |
| `authorizations_total` | Distinct authorization event IDs, not verified human interactions or review conclusions. |
| `review_invocations_total` | Unknown (`null`); these event formats do not establish actual invocation counts. |
| `rejected_rounds` | Historical rejected closures only; execution_failed is not substantive rejection. |

Each external row retains process/version, issuer, subject, evidence ID,
`supersedes` and `historical_only`. The report reads the recorded decision; it
does not revalidate approval applicability or infer decisions from old checklists.
Legacy row outcomes describe recorded round closures, not per-source decisions.

Event replay is deduplicated by Change/event ID before applying date bounds.
Repeated result imports/failures use Change/run ID; repeated external imports use
Change/evidence ID. Starts/closures use Change/round identity (and closure outcome).
Missing identities fall back to the event ID rather than merging unrelated records.
Two authorizations with identical text but different event IDs remain two records.

Dates select observations, not whole run lifetimes: a run issued before the window
and failing inside it contributes a failure and a record, but no in-window start.
Usage is included only when recorded inside the window. Replaying an old import
inside a later window does not move its original observation date. Within the
window, starts/failures/results for the same run form one row, with the latest
observed numeric fields replacing earlier fields rather than summing them twice.
The event ledger itself is never normalized or rewritten.

## Usage and cost coverage

`review_records_total` counts distinct observable legacy run or external evidence
records in the window. `review_records_with_usage` and
`review_records_with_reported_cost` are the coverage numerators. The older
`review_runs_total`, `review_runs_with_usage` and `review_runs_with_reported_cost`
fields cover legacy run rows only; external evidence is never a run.

`review_tokens` and `review_reported_cost_usd` are recorded subtotals across both
record types. No data is `null`/unknown, while an explicitly recorded zero is zero.
Missing records are not free. A full record coverage ratio still does not prove
all token components, all invocations or total billing were captured.

For legacy records, read receipt usage/cost (or explicit failure payload fields).
For external evidence, only optional top-level `usage` and `reported_cost_usd`
are counted; opaque `original_evidence` prose and nested provider blobs are not
searched. The evidence producer is responsible for stating what its subtotal covers.
An explicit nonnegative integer `total_tokens` takes precedence. Otherwise sum
recorded `input_tokens`, `output_tokens`, `cache_read_input_tokens` and
`cache_creation_input_tokens`. These component-only sums are labelled by
`review_component_subtotals`; missing components remain unknown. Cached-input and
reasoning-output subset fields are not added again. Negative, boolean, nonfinite
or nonnumeric money/token values are excluded. No model-price conversion is made.

Coding-agent costs and unrecorded external executions are outside coverage. A
historical failure can have no receipt or usage; neither `0/0` nor a zero subtotal
proves there were no attempts or no costs.

## Findings and guardrail limits

The findings metrics read structured historical code-review `verdict.findings`
and `prior_findings` only, identified by Change/finding ID. They do not parse
opaque new review prose. `findings_resolved`/`findings_wontfix` count IDs with those
recorded dispositions in the window, not independently proven fixes or false
alarms. `findings_open_undisposed` counts IDs raised in the window without a
disposition anywhere in the full ledger, including later dispositions. These
fields are not an as-of-date inventory of all product defects.

Gate-held targets are deduplicated by Change/file/state, a conservative floor.
Verify and CI failures are not independent defect findings. These partial
observations neither measure total validation value nor support a total-value
score or a claim that the harness did nothing when recorded findings are zero.

The optional `scope-vs-plan-final` verification sensor still compares changed
paths with the initial `scope.files` estimate. Its advisory difference is not an
approval or attestation verdict. Within-approval additions update assessment and
actual coverage; the new-contract completion/attestation checks those separately.

For recognized external approvals, final attestation coverage uses the validated
actual implementation manifest. Historical lifecycles retain their initial-scope
rule. Exact code/verification subjects, retained recognized approvals and full
changed-path coverage remain required.

Attestation review disclosures classify referenced imported conclusions as
`external-evidence`, reporting process id/version, issuer, subject, evidence id and
importer separately. The importer actor is not the external reviewer. These are
recorded provenance claims, not verified identity or proof of independence. Legacy
identity-based classifications and skipped-review disclosures remain unchanged.
