---
change: 2026-10-24-keepsail-repository-cutover
stage: plan
---

# Complete the Keepsail repository cutover

The owner explicitly authorized renaming the remote repository and local checkout
after PR127 merged. This is a new Change, separate from the archived runtime
migration. Baseline: main c5a19837386f049042dfd6ffb9b0449b9afa4e2c.

## Commitments

- R1: Update every current repository URL to https://github.com/Dawinia/keepsail:
  package metadata, CLI documentation links, skill/docs pointers, generated agent
  guidance and their existing tests. Regenerate managed sections through native
  renderers. Keep one implementation and the existing runtime interfaces.
- R2: Preserve historical plans, original review/attestation/event records,
  locked decision bodies, generic .harness storage and the recognized policy
  byte-for-byte. Remove the obsolete current-repository-link exception from the
  name scanner, refresh its report, and update the migration guide to distinguish
  the completed runtime migration from this repository/directory cutover.
- R3: Operationally rename the remote to Dawinia/keepsail and origin accordingly;
  move the checkout to E:/Work/keepsail while preserving all tracked, ignored
  authority/private and untracked user files. Repair linked worktrees using native
  Git, rebuild the relocated development environment, and repoint the global
  editable install. Back up and update the saved Codex project paths/name and
  trust key, preserving IDs, other projects and historical chats. Do not edit
  live SQLite records or kill running applications. Report any cache/lock limit.
- R4: Update TapScribe/Pantheon local workflow URLs while preserving immutable
  version pins, jobs, permissions, user text and project HEAD/authority. Refresh
  generated URL pointers through native renderers after code review. Keep these
  consumer edits local, without commits, pushes or unrelated PR changes.
- R5: Commit/freeze complete plan and implementation subjects; obtain recognized
  independent reviews, record coverage, run configured done verification plus
  decision/doc/sync checks, produce native attestation/PR metadata and inspect CI.
  Do not publish packages, merge this source PR, weaken gates or add legacy aliases.

## Current operational evidence and boundaries

The admin rename already succeeded and the remote resolves to Dawinia/keepsail.
The main checkout contents have moved to E:/Work/keepsail; all 1238 recorded
non-cache files matched their pre-move hashes. Native Git2.53 repaired linked
worktree pointers. Backup: C:/Users/DawiniaLo/.codex/migration-backups/
2026-10-24-repository-cutover. The current app still caches its old project path;
saved JSON paths/name and config trust were updated with backups, but UI refresh
must be verified separately. The old folder contains only an empty .git directory;
the current app held the old root open, and an automatic policy rejected a command
that included empty-directory removal. No deletion bypass, junction or legacy
runtime alias is authorized; retain/report that harmless remnant if still blocked.

Use the already attached worktree on a fresh codex/keepsail-repository-cutover
branch and this independent slug; do not reopen the completed migration Change.
Main's pre-existing .superpowers, docs/research, private and lifecycle records
remain untouched. Source files stay unchanged until recognized plan approval.

## Validation

Verify canonical remote fetch, preserved Git HEAD/worktree links and user/authority
hashes, imports/entrypoints from the new main directory, consumer URL pins and
generated-region preservation. Existing URL/renderer tests cover the literal
updates; no new abstraction or test framework is needed. Full configured done,
decision check --gate-reconcile, doc check and sync --check must pass. A source PR
may remain unmerged; remote name, physical directory, saved UI configuration,
cached app display and source delivery are separate claims.
