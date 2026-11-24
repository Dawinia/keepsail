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
for the one-shot dispatcher used by `verify` and `done`. Its batch timer starts
before the check, so a check timeout at or above 3600 would be preempted and
reported as a generic dispatcher timeout. This plan sets the pytest limit to 3300,
below the ceiling, so the check-level timeout stays authoritative, and shortens the
run by parallelism instead.

## Commitments

1. **xdist** - declare `pytest-xdist` in the existing `dev` extra of
   `pyproject.toml` (`[project.optional-dependencies]`), constrained to the version
   installed in the current `.venv` (3.8.0), and update `uv.lock` with `uv lock` so
   it resolves pytest-xdist 3.8.0. No other dependency is added, removed or
   re-pinned; if the lock update would change other packages, stop and re-plan.
2. **parallel** - the `pytest` check command in `.harness/verification.yaml` becomes
   `[python, -m, scripts.run_project_check, pytest, -q, -n, "2"]`; the other
   arguments are unchanged.
3. **timeout** - the `pytest` check `timeout_seconds` changes from 2700 to 3300, with
   the adjacent comment stating the reason, the 3600-second dispatcher ceiling and
   the exit condition below.

No other check, `must_pass`, default, layer or `execution` setting changes.

## Measured basis

- PR 140 code at `e30fa03`, full suite with `-n 2`: wall time 2345s; 2647 passed,
  43 failed, 23 skipped (2713 in total). 42 failures were a confirmed real
  regression (the no-HEAD authority check), reproduced in a single process and fixed
  in `4396447`; the remaining one was an e2e test that resolved an outdated global
  `keepsail` from PATH, an environment issue. None was a parallel-only failure.
- PR 140 code at `4396447`, `-n 2`: interrupted at 89% by host memory reclamation;
  all 2422 tests that ran passed. The 19 remaining files were then run in a single
  process: 294 passed, 4 skipped (2720 in total).
- The totals do not reconcile: the fix adds one test, and the source of the
  remaining difference has not been verified.
- The 2345-second and 89% figures are author-reported; their run logs were not
  retained in the repository.
- The 2345-second run was of pre-fix code with failures and may understate the
  fixed-code runtime. No uninterrupted `-n 2` run of the fixed code has completed,
  so this Change's own verify is the first complete measurement. 3300 leaves about
  40% margin over 2345s.

## Parallel safety and risk

`pytest-xdist` 3.8.0 is installed today and will be declared by commitment 1. In the
two-worker runs above no test failed only under parallel execution; one complete
pass cannot prove the absence of ordering or shared-state coupling. CI continues to
run its own serial pytest jobs and is not affected.

The host is memory constrained, so two workers are chosen, not more. If this
Change's first verify is interrupted or times out, there is no automatic fallback to
another configuration: the author submits a new plan candidate for review.

## Which configuration verify reads

In main's code, `keepsail verify` reads the working-tree `.harness/verification.yaml`
(`src/keepsail/cli/verify.py:216`, `src/keepsail/sensors/verification_runner.py:1144`),
so this Change's own verify runs the edited configuration. PR 140's code reads the
configuration from the trusted baseline (`origin/main`), so PR 140 can use the new
configuration only after this Change is merged.

## Boundaries and exit condition

- Scope: `.harness/verification.yaml`, `pyproject.toml`, `uv.lock` and this plan
  only. No product code, tests, `must_pass` relaxation, skipping, filtering or
  selection changes, and no review recognition or policy changes.
- Exit condition, owned by the repository owner:
  - The follow-up Windows git subprocess performance Change must include in its own
    plan one complete serial full pytest measurement on this machine. If the serial
    suite measures below 2000 seconds, that same Change restores the serial command
    and the 2700-second limit, subject to its own review.
  - Backstop: on 2026-12-31, whatever the progress, the owner opens a Change to
    re-evaluate this relaxation.
  - This plan does not itself authorize the restoration.

## Validation

Run `keepsail decision check --changed` and `keepsail doc check`; confirm the diffs
of `.harness/verification.yaml`, `pyproject.toml` and `uv.lock` touch only the
committed items, that the configuration still loads and that the lock resolves
pytest-xdist 3.8.0. This Change's first complete `keepsail verify` on the frozen
implementation is a gate. Obtain and import independently produced recognized reviews
for the exact frozen plan and code subjects. No merge is authorized by this plan.
