---
change: 2026-10-23-keepsail-brand-migration
stage: plan
---

# Keepsail brand migration

## Authority and baseline

The user selected Keepsail and authorized a complete brand migration in an independent
Change. Baseline main/origin/main: 60e2ecdcb22f4ce443aa29d65b7b23faa52a0cdf,
verified after fetch on 2026-10-23; PR125 and PR126 are merged.
Work is isolated in the attached keepsail-brand-migration worktree on
codex/keepsail-brand-migration. Preserve the daily E:/Work/super-harness checkout,
its editable CLI, .superpowers/ and docs/research/.

Read docs/product-architecture.md and docs/product-architecture-coverage.md first.
Keepsail remains the product-work control layer across agent harnesses: effective
human commitments, authorized autonomy, long-lived evolving product knowledge,
continuity and traceability. Rename only; preserve all normative meanings and
coverage gaps. No capability expansion or narrowing to CI, memory or agent runtime.

## Binding commitments

- K1: Make Keepsail the current product brand, Python distribution and primary CLI
  family (keepsail, keepsail-hook, keepsail-daemon). Update package metadata,
  lockfile, current documentation, examples, scripts, workflows, adapters and
  generated guidance from their sources. Version remains 0.1.0; publication is separate.
- K2: Preserve one implementation under the existing super_harness Python namespace.
  This is a deliberate supported import compatibility name, not an overlooked rename:
  moving it invalidates locked executable decisions, import contracts and integrations.
  Both CLI families dispatch to the same implementation. Do not ship a speculative
  second module tree. No sh executable alias: sh is the system shell; replace only
  product shorthand in current prose, never shell commands.
- K3: Preserve .harness/ layout, event/schema names, slug/subject identity and hashing,
  attestation/receipt history, recognition policy/digest, SUPER_HARNESS_* environment
  variables, machine keys, logger namespaces, PR metadata markers, managed section/
  gitignore/adapter markers, backup/lock ownership patterns and existing generated
  workflow filenames. Explain these stable compatibility identifiers together.
  New human-facing generated text and hook commands use Keepsail. Hook reinstall
  must replace existing managed hooks without duplication and preserve unrelated hooks.
  Stable markers prevent duplicate managed sections or historical PR identity loss.
- K4: Preserve all historical plans, attestations, seeded demo event/state evidence,
  ratified decision bodies and the dated product-foundations record. Do not rewrite
  past evidence, hand-edit ledger/state/review artifacts/automatic PR metadata, or
  relax governance. Decision reconcile, if anchored code changes, follows the real
  review instruction using the CLI and retained substantive conclusions; no body edits.
- K5: Enumerate every tracked old-name/shorthand occurrence by file and classify
  migrated, compatibility, historical or external follow-up, with reasons. Distinguish
  shell sh, superpowers framework and unrelated harness vocabulary from product aliases.
  Repeat the scan after implementation; every residual occurrence needs a category.
  Review generated and untracked local external state separately, without altering it.
- K6: Verify wheel/sdist metadata and isolated installation outside this checkout,
  installed keepsail and legacy CLI/help/hook/daemon entry points, package import
  location, existing workspace resume, generated init/sync output and idempotent
  legacy-hook replacement. Test trusted-base merge validation across the rename:
  base verifier remains installed from base, never from untrusted PR checkout.
  Cover CLI/JSON/exit compatibility and representative legacy configuration.
  Run affected and full configured verification, doc check/refs, sync --check,
  decision checks including reconcile gate, and diff checks.
- K7: Obtain exact frozen plan approval and code review through the owner-recognized
  independent Codex subagent process in .harness/review-recognition.yaml.
  Retain the original conclusion/provenance and import exact evidence. Failure,
  empty result and skip are not approvals. Record actual implementation coverage.
  Freeze subject before review; no implementation edits while review is pending.
  Generate attestation and PR metadata through native CLI, attach any PR; do not merge.
- K8: Treat external effects separately: no repository rename, local-directory move,
  global editable reinstall, dependency-project edits, package publication/deletion,
  placeholder package or saved Codex project relocation. Prepare concrete reversible
  code/docs first, list external actions and required owner decisions. Links stay on
  the real existing GitHub repository until it is renamed, with an explicit explanation.
  Install/upgrade docs distinguish local source installation from an unpublished
  registry release and explain old-distribution uninstall plus new install conflicts.

## Migration decisions and complete surface checklist

| Surface | Action and acceptance |
|---|---|
| README, Chinese README, docs landing/overview/concepts/architecture | Keepsail branding and product shorthand; preserve normative meaning and dated coverage claims. |
| Python distribution, authors, description, keywords, version, lock | Distribution keepsail; description matches product architecture; same version/dependencies; consistent lock metadata. |
| Python imports, import-linter and hash-locked paths | Keep super_harness as supported compatibility namespace; explain in migration guide. |
| CLI root, errors, help, daemon/hook entry points, internal subprocesses | Primary Keepsail names plus old console aliases; same machine envelope/schema/exit semantics; test both. |
| Existing .harness workspace and persisted evidence | No directory/event/state migration or replay rewriting; resume works with same records. |
| Environment variables and machine/protocol identifiers | Retain exact legacy spellings and semantics; document them. |
| Adapters, hooks, settings merge/backup/locks | New commands use Keepsail; stable identity/ownership ensures old hook replacement and uninstall safety. |
| AGENTS/CLAUDE generated sections and source templates | Modify source then native regeneration; keep stable HTML marker grammar; verify no duplicate sections. |
| Gitignore generated blocks | Keep stable markers/backup patterns; regenerate if source changes; preserve unrelated user text. |
| Workflow templates and repository CI | Current commands use Keepsail; stable generated target filename retained to replace old workflow; trusted-base verifier supports old base binary. |
| PR decoration, attestation and receipts | Stable metadata identity and historical records; new presentation uses brand; native generator only. |
| Skills, examples and integration references | Update current instructions; preserve seed ledger/state and historical fixtures; shell sh and superpowers are unrelated. |
| Plugins/MCP/npm | Search tracked manifests/config and local registrations; no invented npm distribution or MCP server if none exists. |
| Build/releases/badges/URLs | Real existing repository links remain valid; registry install instructions accurately pending until publication. No fake release badge claim. |
| Tests/fixtures | Current brand assertions updated; old protocol/workspace tests remain explicit; real installed wheel tests. |
| External/local state | Read-only inventory global executable/editable source, local hooks, saved project/path references; owner follow-up checklist. |
| Residual matrix | Reproducible tracked-file scan including hidden files and uppercase/underscore/space variants; per-file category, count and reason. |

## Name check evidence and limits

On 2026-10-23 direct HTTPS requests returned 404 for both
https://pypi.org/pypi/keepsail/json and https://registry.npmjs.org/keepsail.
gh search repos keepsail returned only keepsail/keepsail.github.io (empty
description). Web search transport returned HTTP403, so broad public-web conflict
checking is incomplete. These observations do not reserve names or prove
trademark/domain availability. Retry accessible primary registries/search; report
any concrete serious same-domain conflict, without treating unrelated names as blockers.
Never publish a package to test name availability.

## Execution and review sequence

1. Commit this complete plan and inventory, submit with K1-K8 commitments,
   retain exact plan subject, obtain independent recognized review and import it.
2. After effective approval, start implementation; inspect each family above and
   implement bounded naming changes with compatibility tests. Use writing-for-agents
   for skill/generated instruction sources; no manual managed-block edits.
3. Create a worktree-local .venv and editable install; keep global environment intact.
   Record actual changed-file coverage/assessment against K1-K8 through the CLI.
4. Regenerate docs/guidance, audit residuals, verify package/old-workspace behavior,
   run conformance and configured checks. Reconcile anchored decisions only after
   substantive review that their unchanged rule still holds.
5. Commit implementation, record exact subject, run done and independent code review.
   Fix/re-review through implementation reopen if needed. Generate attestation,
   dry-run trusted-base merge validation, create native PR and inspect CI; never merge.
6. Report code delivery, historical/compatibility retention, external actions and
   unavailable evidence independently. Incomplete external migration stays explicit.

## Initial per-file inventory

Scan covers all 568 tracked baseline files, including hidden files; matches include
old hyphen/underscore/space/case variants, superharness and product/shell sh.
Counts below are exact content-match counts, not a claim every occurrence is branding.
The 503 matching paths are selected from git ls-tree -r --name-only at baseline
60e2ecd, by a content OR path match. Paths containing the import namespace may have
zero content matches. Decode UTF-8 and apply Python re.IGNORECASE to the literal
pattern super[-_ ]harness|superharness|(?<![A-Za-z0-9_])sh(?![A-Za-z0-9_]).
The new plan is excluded from the baseline inventory and separately retained as
historical migration evidence. Shell-only matches are unrelated system-shell syntax;
product-architecture shorthand is current brand prose to migrate.
H records remain byte-preserved except authorized native decision reconciliation
frontmatter. M+C requires occurrence-level inspection during implementation.
This plan is itself historical naming evidence and will be retained after approval.

| Tracked file | Matches | Classification |
|---|---:|---|
| .github/workflows/decision-check.yml | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| .github/workflows/doc-check.yml | 3 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| .github/workflows/merge-gate.yml | 7 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| .github/workflows/test.yml | 12 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| .gitignore | 8 | G: regenerate managed content; retain protocol markers |
| .harness/adapters.yaml | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| .harness/attestations/2026-06-04-layer2-merge-gate.jsonl | 6 | H: preserve historical or locked record |
| .harness/attestations/2026-06-04-review-identity-substrate.jsonl | 5 | H: preserve historical or locked record |
| .harness/attestations/2026-06-08-decision-records-anchors.jsonl | 43 | H: preserve historical or locked record |
| .harness/attestations/2026-06-11-doc-leg-derivable-docs.jsonl | 8 | H: preserve historical or locked record |
| .harness/attestations/2026-06-15-decision-text-lock.jsonl | 3 | H: preserve historical or locked record |
| .harness/attestations/2026-06-16-decision-executable-checks.jsonl | 3 | H: preserve historical or locked record |
| .harness/attestations/2026-06-17-agents-md-decision-conformance.jsonl | 6 | H: preserve historical or locked record |
| .harness/attestations/2026-06-20-tier-2-reviewable-anchors.jsonl | 3 | H: preserve historical or locked record |
| .harness/attestations/2026-06-23-auto-review-hardening-slice2.jsonl | 5 | H: preserve historical or locked record |
| .harness/attestations/2026-06-23-auto-review-hardening.jsonl | 21 | H: preserve historical or locked record |
| .harness/attestations/2026-06-23-check-drafting-assist.jsonl | 2 | H: preserve historical or locked record |
| .harness/attestations/2026-06-25-doc-deadref-gate.jsonl | 5 | H: preserve historical or locked record |
| .harness/attestations/2026-06-26-arm-legacy-decisions.jsonl | 1 | H: preserve historical or locked record |
| .harness/attestations/2026-06-26-gate-escape-hatch-hardening.jsonl | 8 | H: preserve historical or locked record |
| .harness/attestations/2026-06-26-generalize-gate-bypass-wording.jsonl | 2 | H: preserve historical or locked record |
| .harness/attestations/2026-06-26-language-profile-doc-refs.jsonl | 2 | H: preserve historical or locked record |
| .harness/attestations/2026-06-27-architecture-fitness.jsonl | 1 | H: preserve historical or locked record |
| .harness/attestations/2026-06-30-core-sensors-decoupling.jsonl | 7 | H: preserve historical or locked record |
| .harness/attestations/2026-06-30-fix-stale-cycle-comment.jsonl | 3 | H: preserve historical or locked record |
| .harness/attestations/2026-07-01-authoring-conformance-feedback-v6.jsonl | 6 | H: preserve historical or locked record |
| .harness/attestations/2026-07-01-codex-stop-delivery.jsonl | 8 | H: preserve historical or locked record |
| .harness/attestations/2026-07-02-active-change-recency.jsonl | 7 | H: preserve historical or locked record |
| .harness/attestations/2026-07-02-authoring-parallel-checks.jsonl | 6 | H: preserve historical or locked record |
| .harness/attestations/2026-07-02-gitignore-daemon-runtime.jsonl | 1 | H: preserve historical or locked record |
| .harness/attestations/2026-07-02-p0-gate-soundness-v3.jsonl | 9 | H: preserve historical or locked record |
| .harness/attestations/2026-07-02-sync-check-engineering-move-v3.jsonl | 7 | H: preserve historical or locked record |
| .harness/attestations/2026-07-02-unified-shell-runner.jsonl | 6 | H: preserve historical or locked record |
| .harness/attestations/2026-07-03-gate-in-process-daemon-demotion-v2.jsonl | 16 | H: preserve historical or locked record |
| .harness/attestations/2026-07-03-parse-ts-and-encoding-debt.jsonl | 24 | H: preserve historical or locked record |
| .harness/attestations/2026-07-03-writer-flock-toctou.jsonl | 5 | H: preserve historical or locked record |
| .harness/attestations/2026-07-04-architecture-norm-discovery-skill.jsonl | 2 | H: preserve historical or locked record |
| .harness/attestations/2026-07-06-codex-coverage-caveat-wording.jsonl | 3 | H: preserve historical or locked record |
| .harness/attestations/2026-07-06-docs-ia-narrative-layer.jsonl | 5 | H: preserve historical or locked record |
| .harness/attestations/2026-07-06-plan-redeclare-cli-verb.jsonl | 3 | H: preserve historical or locked record |
| .harness/attestations/2026-07-06-quickstart-adapters-and-zh-readme.jsonl | 1 | H: preserve historical or locked record |
| .harness/attestations/2026-07-06-remove-custom-plugin-loading.jsonl | 12 | H: preserve historical or locked record |
| .harness/attestations/2026-07-15-review-cost-breakdown.jsonl | 66 | H: preserve historical or locked record |
| .harness/attestations/2026-07-16-per-severity-round-policy.jsonl | 374 | H: preserve historical or locked record |
| .harness/attestations/2026-07-29-claude-cli-schema-fix.jsonl | 28 | H: preserve historical or locked record |
| .harness/attestations/2026-07-29-gate-authoring-space-v2.jsonl | 439 | H: preserve historical or locked record |
| .harness/attestations/2026-07-29-lint-ruff-pin.jsonl | 1 | H: preserve historical or locked record |
| .harness/attestations/2026-07-30-pitfall-is-proposed-decision.jsonl | 184 | H: preserve historical or locked record |
| .harness/attestations/2026-07-30-scope-and-review-import-fixes.jsonl | 310 | H: preserve historical or locked record |
| .harness/attestations/2026-08-06-plan-review-round-budget.jsonl | 305 | H: preserve historical or locked record |
| .harness/attestations/2026-08-06-plan-scope-fail-open.jsonl | 81 | H: preserve historical or locked record |
| .harness/attestations/2026-08-08-hint-and-disclosure-sweep.jsonl | 85 | H: preserve historical or locked record |
| .harness/attestations/2026-08-08-model-alias-suffix.jsonl | 36 | H: preserve historical or locked record |
| .harness/attestations/2026-08-08-plan-review-prompt.jsonl | 51 | H: preserve historical or locked record |
| .harness/attestations/2026-08-09-authorization-channel.jsonl | 263 | H: preserve historical or locked record |
| .harness/attestations/2026-08-20-windows-file-locks.jsonl | 71 | H: preserve historical or locked record |
| .harness/attestations/2026-09-04-product-baseline.jsonl | 37 | H: preserve historical or locked record |
| .harness/attestations/2026-09-04-windows-verification.jsonl | 247 | H: preserve historical or locked record |
| .harness/attestations/2026-09-11-plan-authority.jsonl | 397 | H: preserve historical or locked record |
| .harness/attestations/2026-09-15-plan-authority-alignment.jsonl | 225 | H: preserve historical or locked record |
| .harness/attestations/2026-10-22-attestation-contract-recovery.jsonl | 32 | H: preserve historical or locked record |
| .harness/attestations/code-only-recovery.jsonl | 129 | H: preserve historical or locked record |
| .harness/attestations/codex-agent-adapter.jsonl | 18 | H: preserve historical or locked record |
| .harness/attestations/init-interactive-wizard.jsonl | 352 | H: preserve historical or locked record |
| .harness/attestations/init-wizard-cohesion.jsonl | 307 | H: preserve historical or locked record |
| .harness/attestations/init-wizard-progressive-disclosure.jsonl | 252 | H: preserve historical or locked record |
| .harness/attestations/multi-independent-reviewer-gate.jsonl | 96 | H: preserve historical or locked record |
| .harness/attestations/plan-authoring-gate-v2.jsonl | 22 | H: preserve historical or locked record |
| .harness/attestations/record-gate-blocks.jsonl | 91 | H: preserve historical or locked record |
| .harness/attestations/report-doc-accuracy.jsonl | 19 | H: preserve historical or locked record |
| .harness/attestations/review-contract-compiler.jsonl | 209 | H: preserve historical or locked record |
| .harness/attestations/value-report-stage1.jsonl | 270 | H: preserve historical or locked record |
| .harness/attestations/verification-env-scrub.jsonl | 2 | H: preserve historical or locked record |
| .harness/review-recognition.yaml | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| .importlinter | 6 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| AGENTS.md | 39 | G: regenerate managed content; retain protocol markers |
| LICENSE | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| README.md | 10 | M+C: migrate current guidance; explain compatibility and dated evidence |
| README.zh-CN.md | 10 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/ARCHITECTURE.md | 20 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/README.md | 2 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/adapters/claude-code.md | 34 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/adapters/codex.md | 14 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/adapters/openspec.md | 15 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/adapters/plain.md | 18 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/adopting.md | 5 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/architecture-fitness.md | 6 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/cli-reference.md | 170 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/concepts.md | 3 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/decisions/d-core-is-base.md | 7 | H: preserve historical or locked record |
| docs/decisions/d-dangling-check.md | 1 | H: preserve historical or locked record |
| docs/decisions/d-decision-records.md | 1 | H: preserve historical or locked record |
| docs/decisions/d-events-append-only.md | 2 | H: preserve historical or locked record |
| docs/decisions/d-fixed-transition-matrix.md | 1 | H: preserve historical or locked record |
| docs/decisions/d-gate-governs-git-product.md | 1 | H: preserve historical or locked record |
| docs/decisions/d-gh-cli-not-rest.md | 1 | H: preserve historical or locked record |
| docs/decisions/d-identity-resolution-order.md | 2 | H: preserve historical or locked record |
| docs/decisions/d-merge-gate-pure-git.md | 3 | H: preserve historical or locked record |
| docs/decisions/d-no-backticked-nonexistent-identifiers.md | 1 | H: preserve historical or locked record |
| docs/decisions/d-no-recovery-from-awaiting-code-review.md | 6 | H: preserve historical or locked record |
| docs/decisions/d-pitfall-is-proposed-decision.md | 2 | H: preserve historical or locked record |
| docs/decisions/d-single-gate-policy.md | 2 | H: preserve historical or locked record |
| docs/decisions/d-state-pure-fold.md | 1 | H: preserve historical or locked record |
| docs/getting-started.md | 75 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/limitations.md | 7 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/overview.md | 9 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/plans/2026-06-02-superpowers-framework-adapter-design.md | 5 | H: preserve historical or locked record |
| docs/plans/2026-06-02-superpowers-framework-adapter.md | 11 | H: preserve historical or locked record |
| docs/plans/2026-06-03-layer2-merge-gate-design.md | 7 | H: preserve historical or locked record |
| docs/plans/2026-06-03-self-host-hard-gate-design.md | 9 | H: preserve historical or locked record |
| docs/plans/2026-06-03-self-host-hard-gate.md | 42 | H: preserve historical or locked record |
| docs/plans/2026-06-03-sync-gitignore-refresh-design.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-06-03-sync-gitignore-refresh.md | 34 | H: preserve historical or locked record |
| docs/plans/2026-06-04-layer2-merge-gate-plan.md | 69 | H: preserve historical or locked record |
| docs/plans/2026-06-04-review-identity-substrate-design.md | 5 | H: preserve historical or locked record |
| docs/plans/2026-06-04-review-identity-substrate-plan.md | 40 | H: preserve historical or locked record |
| docs/plans/2026-06-05-decision-conformance-harness-design.md | 6 | H: preserve historical or locked record |
| docs/plans/2026-06-08-decision-records-anchors-design.md | 5 | H: preserve historical or locked record |
| docs/plans/2026-06-08-decision-records-anchors-plan.md | 92 | H: preserve historical or locked record |
| docs/plans/2026-06-09-capability-retirement-design.md | 3 | H: preserve historical or locked record |
| docs/plans/2026-06-10-capability-retirement-plan.md | 16 | H: preserve historical or locked record |
| docs/plans/2026-06-11-doc-leg-derivable-docs-design.md | 13 | H: preserve historical or locked record |
| docs/plans/2026-06-11-doc-leg-derivable-docs.md | 63 | H: preserve historical or locked record |
| docs/plans/2026-06-12-decision-text-lock-design.md | 2 | H: preserve historical or locked record |
| docs/plans/2026-06-15-decision-text-lock-implementation.md | 27 | H: preserve historical or locked record |
| docs/plans/2026-06-16-decision-executable-checks-implementation.md | 48 | H: preserve historical or locked record |
| docs/plans/2026-06-17-agents-md-decision-conformance-design.md | 19 | H: preserve historical or locked record |
| docs/plans/2026-06-17-agents-md-decision-conformance-implementation.md | 75 | H: preserve historical or locked record |
| docs/plans/2026-06-20-tier-2-reviewable-anchors-implementation.md | 41 | H: preserve historical or locked record |
| docs/plans/2026-06-23-arm-decision-teeth-design.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-06-23-arm-decision-teeth-implementation.md | 34 | H: preserve historical or locked record |
| docs/plans/2026-06-23-auto-review-hardening-slice1-implementation.md | 86 | H: preserve historical or locked record |
| docs/plans/2026-06-23-auto-review-hardening-slice2-design.md | 2 | H: preserve historical or locked record |
| docs/plans/2026-06-23-auto-review-hardening-slice2-implementation.md | 64 | H: preserve historical or locked record |
| docs/plans/2026-06-23-check-drafting-assist-design.md | 5 | H: preserve historical or locked record |
| docs/plans/2026-06-23-check-drafting-assist.md | 22 | H: preserve historical or locked record |
| docs/plans/2026-06-25-codex-agent-adapter-design.md | 23 | H: preserve historical or locked record |
| docs/plans/2026-06-25-codex-agent-adapter-implementation.md | 97 | H: preserve historical or locked record |
| docs/plans/2026-06-25-doc-deadref-gate-impl.md | 56 | H: preserve historical or locked record |
| docs/plans/2026-06-25-doc-lifecycle-research-reframe.md | 3 | H: preserve historical or locked record |
| docs/plans/2026-06-26-gate-escape-hatch-hardening-design.md | 17 | H: preserve historical or locked record |
| docs/plans/2026-06-26-gate-escape-hatch-hardening-implementation.md | 61 | H: preserve historical or locked record |
| docs/plans/2026-06-26-language-profile-doc-refs-design.md | 10 | H: preserve historical or locked record |
| docs/plans/2026-06-26-language-profile-doc-refs-implementation.md | 22 | H: preserve historical or locked record |
| docs/plans/2026-06-27-architecture-fitness-decisions-design.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-06-27-architecture-fitness.md | 14 | H: preserve historical or locked record |
| docs/plans/2026-06-29-core-adapters-sensors-decoupling.md | 83 | H: preserve historical or locked record |
| docs/plans/2026-07-01-authoring-time-conformance-sensor-design.md | 3 | H: preserve historical or locked record |
| docs/plans/2026-07-01-authoring-time-conformance-sensor-plan.md | 55 | H: preserve historical or locked record |
| docs/plans/2026-07-01-codex-stop-delivery-design.md | 4 | H: preserve historical or locked record |
| docs/plans/2026-07-01-codex-stop-delivery.md | 67 | H: preserve historical or locked record |
| docs/plans/2026-07-01-verification-env-scrub-design.md | 29 | H: preserve historical or locked record |
| docs/plans/2026-07-01-verification-env-scrub.md | 37 | H: preserve historical or locked record |
| docs/plans/2026-07-02-active-change-recency-plan.md | 5 | H: preserve historical or locked record |
| docs/plans/2026-07-02-authoring-parallel-checks-design.md | 1 | H: preserve historical or locked record |
| docs/plans/2026-07-02-authoring-parallel-checks-plan.md | 4 | H: preserve historical or locked record |
| docs/plans/2026-07-02-gitignore-daemon-runtime-plan.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-07-02-p0-gate-soundness-plan.md | 10 | H: preserve historical or locked record |
| docs/plans/2026-07-02-sync-check-engineering-move-design.md | 11 | H: preserve historical or locked record |
| docs/plans/2026-07-02-unified-shell-runner-design.md | 4 | H: preserve historical or locked record |
| docs/plans/2026-07-02-unified-shell-runner-plan.md | 16 | H: preserve historical or locked record |
| docs/plans/2026-07-03-gate-in-process-daemon-demotion-design.md | 3 | H: preserve historical or locked record |
| docs/plans/2026-07-03-gate-in-process-daemon-demotion-plan.md | 151 | H: preserve historical or locked record |
| docs/plans/2026-07-03-parse-ts-and-encoding-debt.md | 22 | H: preserve historical or locked record |
| docs/plans/2026-07-03-writer-flock-toctou-plan.md | 9 | H: preserve historical or locked record |
| docs/plans/2026-07-04-architecture-fitness-doc-design.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-07-04-architecture-fitness-doc-plan.md | 25 | H: preserve historical or locked record |
| docs/plans/2026-07-04-architecture-norm-discovery-skill-design.md | 14 | H: preserve historical or locked record |
| docs/plans/2026-07-04-architecture-norm-discovery-skill-plan.md | 38 | H: preserve historical or locked record |
| docs/plans/2026-07-06-codex-coverage-caveat-wording-plan.md | 11 | H: preserve historical or locked record |
| docs/plans/2026-07-06-docs-ia-narrative-layer-design.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-07-06-docs-ia-narrative-layer-plan.md | 53 | H: preserve historical or locked record |
| docs/plans/2026-07-06-plan-redeclare-cli-verb.md | 14 | H: preserve historical or locked record |
| docs/plans/2026-07-06-plugin-loading-removal-design.md | 13 | H: preserve historical or locked record |
| docs/plans/2026-07-06-plugin-loading-removal-implementation.md | 44 | H: preserve historical or locked record |
| docs/plans/2026-07-06-quickstart-adapters-and-zh-readme-design.md | 10 | H: preserve historical or locked record |
| docs/plans/2026-07-06-quickstart-adapters-and-zh-readme-plan.md | 39 | H: preserve historical or locked record |
| docs/plans/2026-07-09-multi-independent-reviewer-gate-plan.md | 49 | H: preserve historical or locked record |
| docs/plans/2026-07-11-review-contract-compiler.md | 42 | H: preserve historical or locked record |
| docs/plans/2026-07-15-review-cost-breakdown.md | 11 | H: preserve historical or locked record |
| docs/plans/2026-07-15-value-report-stage1.md | 29 | H: preserve historical or locked record |
| docs/plans/2026-07-16-per-severity-round-policy-plan.md | 13 | H: preserve historical or locked record |
| docs/plans/2026-07-16-plan-authoring-gate-design.md | 2 | H: preserve historical or locked record |
| docs/plans/2026-07-16-plan-authoring-gate.md | 43 | H: preserve historical or locked record |
| docs/plans/2026-07-16-record-gate-blocks.md | 24 | H: preserve historical or locked record |
| docs/plans/2026-07-16-report-doc-accuracy.md | 5 | H: preserve historical or locked record |
| docs/plans/2026-07-17-init-interactive-wizard-design.md | 17 | H: preserve historical or locked record |
| docs/plans/2026-07-17-init-interactive-wizard-implementation.md | 162 | H: preserve historical or locked record |
| docs/plans/2026-07-18-init-wizard-cohesion.md | 56 | H: preserve historical or locked record |
| docs/plans/2026-07-20-init-wizard-progressive-disclosure-design.md | 12 | H: preserve historical or locked record |
| docs/plans/2026-07-20-init-wizard-progressive-disclosure.md | 21 | H: preserve historical or locked record |
| docs/plans/2026-07-29-claude-cli-schema-fix.md | 1 | H: preserve historical or locked record |
| docs/plans/2026-07-29-gate-authoring-space-v2-implementation.md | 80 | H: preserve historical or locked record |
| docs/plans/2026-07-29-lint-ruff-pin.md | 2 | H: preserve historical or locked record |
| docs/plans/2026-07-30-pitfall-is-proposed-decision-design.md | 2 | H: preserve historical or locked record |
| docs/plans/2026-07-30-pitfall-is-proposed-decision-implementation.md | 41 | H: preserve historical or locked record |
| docs/plans/2026-07-30-scope-and-review-import-fixes-implementation.md | 18 | H: preserve historical or locked record |
| docs/plans/2026-08-06-plan-review-round-budget-implementation.md | 19 | H: preserve historical or locked record |
| docs/plans/2026-08-06-plan-scope-fail-open.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-08-08-hint-and-disclosure-sweep.md | 3 | H: preserve historical or locked record |
| docs/plans/2026-08-08-model-alias-suffix.md | 4 | H: preserve historical or locked record |
| docs/plans/2026-08-08-plan-review-prompt.md | 6 | H: preserve historical or locked record |
| docs/plans/2026-08-09-authorization-channel-design.md | 4 | H: preserve historical or locked record |
| docs/plans/2026-08-11-code-only-recovery.md | 11 | H: preserve historical or locked record |
| docs/plans/2026-08-20-windows-file-locks.md | 9 | H: preserve historical or locked record |
| docs/plans/2026-09-04-windows-verification.md | 36 | H: preserve historical or locked record |
| docs/plans/2026-09-11-plan-authority-implementation.md | 60 | H: preserve historical or locked record |
| docs/plans/2026-09-11-plan-authority-spec.md | 8 | H: preserve historical or locked record |
| docs/plans/2026-09-15-plan-authority-alignment-implementation.md | 19 | H: preserve historical or locked record |
| docs/plans/2026-10-22-attestation-contract-recovery.md | 1 | H: preserve historical or locked record |
| docs/product-architecture-coverage.md | 21 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/product-architecture.md | 10 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/product-foundations.md | 6 | H: preserve historical or locked record |
| docs/reporting.md | 1 | M+C: migrate current guidance; explain compatibility and dated evidence |
| docs/state-machine.md | 2 | M+C: migrate current guidance; explain compatibility and dated evidence |
| examples/demo-openspec-claude/.claude/settings.json | 2 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| examples/demo-openspec-claude/.harness/adapters.yaml | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| examples/demo-openspec-claude/.harness/events.jsonl | 1 | H: preserve historical or locked record |
| examples/demo-openspec-claude/.harness/policy.yaml | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| examples/demo-openspec-claude/.harness/state.yaml | 2 | H: preserve historical or locked record |
| examples/demo-openspec-claude/AGENTS.md | 17 | G: regenerate managed content; retain protocol markers |
| examples/demo-openspec-claude/README.md | 23 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| examples/demo-openspec-claude/openspec/changes/demo-add-greeter/proposal.md | 2 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| examples/demo-openspec-claude/openspec/changes/demo-add-greeter/tasks.md | 2 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| examples/demo-openspec-claude/src/greeter.py | 2 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| pyproject.toml | 15 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| scripts/gen_cli_reference.py | 11 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| scripts/gen_state_machine.py | 7 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| scripts/run_project_check.py | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| scripts/smoke-gate.sh | 20 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |
| skills/discovering-architecture-norms/SKILL.md | 5 | M+C: migrate current guidance; explain compatibility and dated evidence |
| src/super_harness/__init__.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/__init__.py | 12 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/agent/__init__.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/agent/_settings_merge.py | 25 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/agent/_stop_protocol.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/agent/claude_code.py | 35 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/agent/codex.py | 24 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/framework/__init__.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/framework/openspec.py | 7 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/framework/plain.py | 7 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/framework/superpowers.py | 10 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/install.py | 14 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/registry.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/reviewer/__init__.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/reviewer/base.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/reviewer/claude_cli.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/reviewer/codex_cli.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/adapters/reviewer/registry.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/__init__.py | 32 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/adapter.py | 21 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/attest.py | 12 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/change.py | 16 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/decision.py | 11 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/doc.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/done.py | 28 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/errors.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/event.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/gate.py | 11 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/group_options.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/implementation.py | 18 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/init.py | 46 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/init_executor.py | 4 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/init_github.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/init_models.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/init_plan.py | 13 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/init_ui.py | 8 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/lazy_group.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/observe.py | 8 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/on_merge.py | 11 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/output.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/plan.py | 20 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/pr.py | 24 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/report.py | 9 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/review.py | 17 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/sensor.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/state.py | 8 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/status.py | 16 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/sync.py | 35 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/verification.py | 4 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/verify.py | 18 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/cli/verify_render.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/__init__.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/_registry.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/active_change.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/anchor_scanner.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/approval.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/authoring_check.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/check_runner.py | 7 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/clock.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/decision_check.py | 4 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/decisions.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/doc_check.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/doc_refs.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/emit_validation.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/events.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/file_lock.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/frontmatter.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/gate_blocks.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/identity.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/language_profile.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/parse_ts.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/paths.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/plan_paths.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/post_emit.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/reducer.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/review_bundle.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/review_checklist.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/review_verdict.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/scope_match.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/shell_runner.py | 15 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/slug.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/source_scope.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/state.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/state_snapshot.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/state_yaml.py | 4 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/transitions.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/ulid.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/workspace.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/core/writer.py | 4 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/daemon/__init__.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/daemon/framework_observer.py | 7 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/daemon/hook_entry.py | 29 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/daemon/server.py | 10 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/daemon/supervisor.py | 7 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/__init__.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/agents_md.py | 33 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/agents_md_render.py | 38 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/attestation.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/gh.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/gitignore_injector.py | 14 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/operation_log.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/pr_metadata.py | 16 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/review_budget.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/review_contract.py | 10 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/review_governance.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/review_profiles.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/review_runs.py | 2 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/sync_check.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/value_report.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/engineering/verification_config.py | 7 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/exit_codes.py | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/gates/__init__.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/gates/decisions.py | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/gates/pre_tool_use.py | 7 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/gates/registry.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/sensors/__init__.py | 9 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/sensors/dispatcher.py | 6 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/sensors/pr_decorator.py | 8 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/sensors/registry.py | 5 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/sensors/verification_runner.py | 18 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/templates/__init__.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/templates/derived_docs_defaults.yaml | 1 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/templates/pull_request_template.md | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/templates/super_harness_workflow.yml | 31 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/templates/verification_defaults.yaml | 3 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| src/super_harness/version.py | 0 | M+C: migrate presentation/commands; preserve internal imports and wire identifiers |
| tests/e2e/__init__.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/e2e/conftest.py | 11 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/e2e/openspec_claude_code/test_full_lifecycle.py | 15 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/e2e/test_plan_authoring_reject_loop.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/e2e/test_pre_tool_use_claude_code.py | 11 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/adapter/test_claude_code.py | 21 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/adapter/test_openspec.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/adapter/test_superpowers_registered.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_adapter.py | 38 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_adapter_install.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_change.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_init.py | 134 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_init_setup_github.py | 127 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_init_windows_entrypoint.py | 39 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_on_merge.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_pr_emit_opened.py | 12 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_pr_validate.py | 23 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_status.py | 36 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_sync.py | 28 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_verification.py | 9 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/cli/test_windows_lifecycle_entrypoint.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/core/test_writer_concurrency.py | 10 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/daemon/test_daemonize.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/daemon/test_framework_observer.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/daemon/test_hook_entry.py | 10 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/daemon/test_hook_entry_plan_paths.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/daemon/test_hook_entry_stop.py | 4 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/daemon/test_observer_host.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/lifecycle/test_plan_authority.py | 25 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/lifecycle/test_state_commands.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/integration/test_authoring_parallel.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/framework/test_openspec.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/framework/test_plain.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/framework/test_superpowers.py | 4 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/reviewer/test_claude_cli.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/reviewer/test_codex_cli.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/reviewer/test_registry.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/test_claude_code.py | 50 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/test_codex.py | 9 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/test_install.py | 4 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/test_protocol.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/test_registry.py | 14 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/test_settings_merge.py | 61 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/adapters/test_stop_protocol.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_attest.py | 10 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_decision.py | 15 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_doc.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_doc_refs_cli.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_done.py | 26 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_entrypoint.py | 12 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_errors.py | 7 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_gate.py | 7 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_gate_check.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_group_options.py | 17 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_implementation.py | 10 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_init_executor.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_init_models.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_init_plan.py | 13 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_init_ui.py | 39 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_lazy_group.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_observe.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_output.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_plan.py | 9 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_plan_records_artifacts.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_report.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_review.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_review_human.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_review_prepare.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_review_runs.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_review_verdict_gate.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_sensor.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_sync.py | 11 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_verify.py | 29 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/cli/test_verify_render.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_active_change.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_anchor_scanner.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_approval.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_authoring_check.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_check_runner.py | 20 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_decision_check.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_decisions.py | 11 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_doc_check_engine.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_doc_check_loader.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_doc_refs.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_emit_validation.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_events.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_file_lock.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_frontmatter.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_gate_blocks.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_identity.py | 16 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_language_profile.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_no_plugin_exec.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_parse_ts.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_paths.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_paths_canonical_relpath.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_plan_paths.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_post_emit.py | 4 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_reducer.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_reducer_plan_artifacts.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_review_bundle.py | 10 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_review_checklist.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_review_verdict.py | 18 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_scope_match.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_shell_runner.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_slug.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_source_scope.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_state.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_state_snapshot.py | 4 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_state_yaml.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_transitions.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_ulid.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_workspace.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/core/test_writer.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/daemon/test_framework_observer.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/daemon/test_hook_entry.py | 4 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/daemon/test_hook_entry_decide.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_agents_md.py | 31 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_agents_md_render.py | 46 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_attestation.py | 9 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_gh.py | 42 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_gitignore_injector.py | 25 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_operation_log.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_pr_metadata.py | 21 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_review_budget.py | 21 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_review_contract.py | 4 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_review_governance.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_review_observations.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_review_profiles.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_review_runs.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_sync_check.py | 10 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_value_report.py | 6 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/engineering/test_verification_config.py | 13 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/gates/test_decisions.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/gates/test_pre_tool_use.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/gates/test_protocol.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/gates/test_registry.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/scripts/test_gen_cli_reference.py | 24 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/scripts/test_gen_state_machine.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/sensors/test_dispatcher.py | 5 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/sensors/test_pr_decorator.py | 24 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/sensors/test_protocol.py | 1 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/sensors/test_registry.py | 3 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/sensors/test_verification_runner.py | 22 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/templates/test_super_harness_workflow.py | 8 | T: update current expectations; preserve legacy fixtures explicitly |
| tests/unit/test_smoke.py | 2 | T: update current expectations; preserve legacy fixtures explicitly |
| uv.lock | 1 | M+C: inspect packaging, automation, example or configuration; preserve compatibility identifiers |

