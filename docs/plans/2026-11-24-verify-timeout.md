---
change: 2026-11-24-verify-timeout
stage: plan
---

# Run local pytest verification on two workers within the dispatcher ceiling

## Problem

On the owner's Windows machine the serial full pytest run of recent code often
exceeds the configured 2700-second limit with little margin. Change
2026-11-10-delivery-policy-transition timed out at 2700s on 2026-11-23 and again on
2026-11-24 (the 2026-11-24 run also failed `ruff`, fixed separately); its passing
run on 2026-11-20 took about 2610s, and its recorded passes took 2532-2649s.

The root cause is product performance on Windows: one profiled test spent about 820
of 912 seconds waiting on roughly 9,100 `git` subprocesses. That is a product
problem; the owner has decided to address it in a separate "Windows git subprocess
performance" product Change. This plan does not change product code.

## Ceiling

`src/keepsail/sensors/dispatcher.py:82` fixes `ONESHOT_DISPATCHER_TIMEOUT_S = 3600`
for the one-shot dispatcher used by `verify` and `done`. No single check can run
longer than that; a check timeout above 3600 cannot take effect. This plan therefore
raises the pytest limit only to 3600 and shortens the run by parallelism instead.

## Commitments

Only the `pytest` check in `.harness/verification.yaml` changes:

1. **parallel** - its command becomes
   `[python, -m, scripts.run_project_check, pytest, -q, -n, "2"]`; the other
   arguments are unchanged.
2. **timeout** - its `timeout_seconds` changes from 2700 to 3600, with the adjacent
   comment updated to state the reason, the 3600-second dispatcher ceiling and the
   exit condition below.

No other check, `must_pass`, default, layer or `execution` setting changes.

## Measured basis

- PR 140 code at `e30fa03`, full suite with `-n 2`: wall time 2345s; 2647 passed,
  43 failed, 23 skipped. 42 failures were a confirmed real regression (the
  no-HEAD authority check), reproduced in a single process and fixed in `4396447`;
  the remaining one was an e2e test that resolved an outdated global `keepsail`
  from PATH, an environment issue. None was a parallel-only failure.
- PR 140 code at `4396447`, `-n 2`: interrupted at 89% by host memory reclamation;
  all 2422 tests that ran passed. The 19 remaining files were then run in a single
  process: 294 passed, 4 skipped.
- Limitation: no uninterrupted `-n 2` run of the fixed code has completed, so this
  Change's own verify is the first complete measurement.

## Parallel safety and risk

`pytest-xdist` 3.8.0 is installed. In the two-worker runs above no test failed only
under parallel execution. CI continues to run its own serial pytest jobs and is not
affected. The host is memory constrained, so two workers are chosen, not more.

## Which configuration verify reads

In main's code, `keepsail verify` reads the working-tree `.harness/verification.yaml`
(`src/keepsail/cli/verify.py:216`, `src/keepsail/sensors/verification_runner.py:1144`),
so this Change's own verify runs the edited configuration. PR 140's code reads the
configuration from the trusted baseline (`origin/main`), so PR 140 can use the new
configuration only after this Change is merged.

## Boundaries and exit condition

- Scope: `.harness/verification.yaml` and this plan only. No product code, tests,
  `must_pass` relaxation, skipping, filtering or selection changes, and no review
  recognition or policy changes.
- Exit condition: after the separate Windows git subprocess performance Change is
  merged, if the serial full suite measures below 2000 seconds on this machine, a
  new Change restores serial execution and the 2700-second limit. This plan does not
  authorize that restoration.

## Validation

Run `keepsail decision check --changed` and `keepsail doc check`; confirm the diff of
`.harness/verification.yaml` touches only the pytest command and timeout lines and
the comment, and that the file still loads. Run this Change's `keepsail verify` on
the frozen implementation. Obtain and import independently produced recognized
reviews for the exact frozen plan and code subjects. No merge is authorized by this
plan.
