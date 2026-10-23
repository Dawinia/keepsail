---
change: 2026-10-23-keepsail-brand-migration
stage: plan
---

# Keepsail direct migration: owner revision

## Authority and preserved product

The owner clarified that this project is unpublished and has no external users:
migrate directly, removing the earlier legacy-runtime compatibility strategy and
handling existing local consumers locally. This supersedes K2/K3 compatibility
retention and K8's deferral of local integration maintenance in the earlier plan.
Use the same unfinished Change and PR127, now draft; do not reuse an unrelated
Change or claim the previously reviewed subject approves these new commitments.

Implementation baseline is 9442ba09f63933a975a4009463301da46218ff24, with PR127
still OPEN/unmerged. origin/main was last verified at60e2ecd; network revalidation
must be retried before delivery after an observed transport failure. The normative
product architecture and separate dated coverage remain governing; product
responsibilities, capability gaps and authority rules do not change.

## New binding commitments

- D1: Keep one implementation under the canonical keepsail Python namespace.
  Move src/super_harness to src/keepsail and migrate imports, resource names,
  build/mypy/import-linter settings, generators, tests and current documentation.
  Ship only keepsail, keepsail-hook and keepsail-daemon console entries. Remove
  legacy namespace/console aliases and tests promising them; do not add a shim.
- D2: Use KEEPSAIL_* variables, keepsail managed HTML/PR/gitignore markers,
  keepsail version metadata field, Keepsail logger/backup/lock names and
  keepsail.yml generated workflow filename. Migrate all current producers,
  readers, templates and tests consistently; old names have no candidate runtime
  fallback. Preserve generic .harness storage and unbranded schema/event names:
  these are not the former product brand and are not legacy alias interfaces.
- D3: Preserve contemporaneous plan/event/review/attestation/receipt contents and
  slug/subject identity. Do not mechanically rewrite historical evidence or seed
  event/state. Keep the recognized policy byte-identical: its opaque historical
  outside-super-harness-core provenance label is an existing authority identity,
  not a module/CLI compatibility interface. New reviews use this unchanged
  recognized process and digest. No inferred approval, skip or policy weakening.
- D4: Migrate binding decisions by native governance. For locked bodies containing
  old module/CLI/environment or executable paths, create proposed Keepsail
  successor records, copy equivalent obligations using canonical names, run
  ratify --dry-run for executable checks, ratify and supersede using the CLI.
  Retain original bodies and linked prior authority. Move code anchors to the
  ratified successor IDs only after ratification. Reconcile other tier-2 records
  through their real review criteria and native CLI to record new source paths.
  No hand-edit of ratified bodies and no hollow or disabled conformance checks.
- D5: Update existing local usage operationally after code review/validation:
  global editable installation, registered adapter hooks and generated guidance,
  local verification command configs and local consumer workflows that actually
  invoke the old CLI. Inventory tapscribe/pantheon and other detected workspaces.
  Use native generators or explicit one-time local conversion with backups;
  preserve unrelated user text/configs and event/state/review evidence. Respect
  each consumer's applicable gates and active work, stop/surface a real gate block.
  Do not overwrite dirty unrelated files or invalidate another Change's approvals.
  Keep local consumer edits local unless separately requested; no unrelated PRs.
- D6: Regenerate this repository's managed artifacts from canonical sources with
  a one-time conversion of its old generated sections. Old markers need not
  remain recognized by the shipped runtime. No migration compatibility layer is
  added for hypothetical external consumers. Current docs must describe the
  direct cutover and distribution dependency changes, replacing prior promises.
- D7: Keep trusted-base merge validation independent of candidate code. Resolve
  the verifier's module namespace and console entry from the trusted BASE_SHA's
  own pyproject metadata, then prove installed site-packages/source hashes match.
  This generic trusted-artifact loading works for the pre-migration base without
  giving the Keepsail runtime old aliases or importing candidate source.
- D8: Freeze complete subjects and obtain recognized independent plan and code
  review; record actual coverage, run done, generate native attestation/PR
  metadata and update PR127. Verify canonical-only wheel/sdist and isolated
  imports/entrypoints, missing old namespace/entrypoints, hook refresh, current
  workspace recovery, machine envelope/exit behavior, docs/sync/decision checks
  and configured full verification. Inspect actual Linux/macOS/Windows CI.
  Never merge, publish a placeholder/package or delete an old published artifact.

## Implementation decisions and boundaries

The move affects every current import and package resource, not product semantics.
The prior initial inventory remains historical; regenerate the residual audit for
the direct result with concrete reasons. Old names are permitted only in preserved
historical records, deliberate negative installation tests, historical recognized
authority labels, actual existing repository/filesystem addresses or one-time local
migration evidence. They are not supported runtime names.

For decisions, inspect actual bodies before choosing successors. Expected affected
records include d-core-is-base, d-gh-cli-not-rest (counterexample path),
d-merge-gate-pure-git, d-identity-resolution-order, d-pitfall-is-proposed-decision
and d-single-gate-policy. Use new d-keepsail-* IDs for those successors; migrate
anchors and import contracts consistently. Other generic rules keep their identity
and receive real CLI reconciliation of moved anchors. Historical/proposed/retired
records remain historical, not rewritten to appear newly authored.

Local installation directories and saved checkout paths are filesystem addresses,
not product import/CLI interfaces. Do not move the active main checkout or repair
unrelated worktrees merely to rename their containing folder during this live task.
Use the reviewed migration checkout for the new editable CLI until PR delivery is
merged by the owner. Preserve .superpowers/ and docs/research/. No GitHub repository
rename or registry publication is implied by this local runtime cutover; links
continue to the actual repository until an explicit external cutover.

The ordinary local updates require no public compatibility promises. Inventory
each consumer's clean/dirty state, current adapters, local hook settings and
configured commands before changing it. Refresh hooks with the canonical binaries,
verify idempotence and unrelated hook preservation, and report the actual files
changed plus any active-governance limitation. Do not rewrite its historical
recognized policy or ledger to make a new path pass.

## Scope estimate and validation

Scope includes this plan, existing current migration guide/audit, src package move,
all current tests/scripts/configs/workflows/example guidance, .importlinter,
pyproject/uv lock, generated AGENTS/docs, native decision successors and linked
decision frontmatter. Historical plan, attestation and seeded ledger/state contents
remain preserved. Record additions/renames/removals in implementation coverage.

Acceptance: importing keepsail and using its three installed scripts works from a
clean wheel outside the checkout; importing super_harness fails and wheel metadata
contains no old script entries. Canonical environment/marker/backup/workflow names
agree across all current surfaces. Existing local projects use the new executable
and refreshed settings without duplicate managed blocks; no persistent compatibility
shim is present. Generic storage and historical subjects stay readable unchanged.
All binding decisions, full verification and trusted-base attestation pass for the
same frozen code subject; PR CI is inspected and no merge/release is performed.

