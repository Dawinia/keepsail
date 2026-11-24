---
change: 2026-11-24-verify-timeout
stage: plan
---

# Raise the local pytest verification timeout

## Problem

On the owner's Windows machine the serial full pytest run no longer finishes within
the configured 2700-second limit. Change 2026-11-10-delivery-policy-transition timed
out at 2700s in two consecutive `keepsail verify` runs, including one on an idle
machine; its historical passing runs took 2407-2650s, so the margin was already too
small. A sharded diagnostic run of the same code passed every test, so the failure is
the limit, not a test result.

The root cause is product performance on Windows: one profiled test spent about 820
of 912 seconds waiting on roughly 9,100 `git` subprocesses (repeated v2 activation
validation, per-blob `git cat-file` reads and repeated commit resolution). That is a
product problem and will be addressed by a separate performance Change.

## Commitment

1. In `.harness/verification.yaml`, change only the `pytest` check's
   `timeout_seconds` from 2700 to 4500 and update its adjacent comment with the
   measured reason and the exit condition below. No other check, command, layer,
   `must_pass`, default, parallelism or selection changes.

## Boundaries

- Scope: `.harness/verification.yaml` and this plan only.
- Not in scope: product code, tests, relaxing `must_pass`, skipping or filtering
  checks, test selection, or any change to review recognition or policy files.
- Exit condition: after the separate performance Change is merged and the serial
  suite again shows an adequate measured margin, a later Change restores a lower
  limit. This plan does not authorize that later change.

## Validation

Run `keepsail decision check --changed` and `keepsail doc check`. This Change's own
`keepsail verify` runs under the current trusted baseline configuration (2700s).
Obtain and import independently produced recognized reviews for the exact frozen plan
and code subjects. No merge is authorized by this plan.
