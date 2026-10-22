---
change: 2026-10-22-attestation-contract-recovery
stage: plan
---

# Mixed-history attestation validation repair

## Problem and authority

At main bfcdb007, the committed product publication at 149df645 fails merge
validation: a historical review_round_started causes the latest recognized
external-evidence code approval to require old protocol receipt_ids. The four
uncovered-document errors follow from rejecting that attestation. A two-event
probe reproduces the receipt error; removing the historical round removes it.
The existing new-contract validator independently returns no blockers for the
unchanged real publication object.

The confirmed product architecture and separate coverage report in the product
publication checkout govern product meanings. This repair changes delivery
validation only; implementation gaps do not authorize narrowing that architecture.

## Commitments

- A1: Select review validation using the effective contract and current approval,
  so historical rounds do not impose obsolete receipt requirements on a recognized
  external-evidence lifecycle. Preserve all historical events and disclosures.
- A2: Preserve legacy receipt enforcement for legacy protocol approvals. Do not
  accept an evidence_id marker alone as authority or weaken recognition, policy
  binding, evidence retention, ordering, exact subject, verification or coverage.
- A3: Add regression coverage at the real merge-verifier seam for mixed histories,
  including malformed/unrecognized/missing or wrong-subject current evidence and
  legacy missing receipts. Observe the positive regression fail before fixing.
- A4: Validate the original committed publication read-only using isolated fixed
  imports; compare its HEAD, attestation bytes and subject before/after. Do not edit
  that checkout, generated attestation, event history, state or ratified decisions.
- A5: Run affected tests, configured verification, doc/decision checks and exact
  subject independent code review. Retain original review conclusions and import
  their exact records. No skip, fabricated receipt, bypass, merge or release.

## Implementation and scope estimate

Inspect all callers of check_attestation and the receipt helper. Reuse existing
trusted-base recognition resolution and new-contract validation, keeping Git-only
merge validation. Prefer a small explicit handoff between legacy and recognized
validation rather than a second implementation of evidence validation. The exact
placement remains subject to the tests and review; reject partial marker bypasses.

Estimated paths: this plan, src/super_harness/engineering/attestation.py,
tests/unit/engineering/test_attestation.py and
tests/integration/lifecycle/test_plan_authority.py. Record actual coverage via
implementation record before completion, including any within-approval test
placement adjustment. No dependencies or product-design changes.

## Acceptance and delivery

The real mixed-history object passes with fixed code while original main still
reports its known receipt blocker. Negative cases remain blocked. The repair
itself reaches a formally verified and independently reviewed exact subject with
generated attestation. If a PR is created, use the repository PR lifecycle and
attach it; do not merge. Distinguish local fixed-code proof from deployment and
the original document branch's delivery permissions.
