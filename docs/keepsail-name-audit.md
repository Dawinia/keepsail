# Keepsail legacy-name residual matrix

Generated on 2026-10-23 from the staged/tracked working tree using
python -m scripts.audit_brand_names. The scanner emits every occurrence with its
line, matched token and classification; this document aggregates those results.
The report itself is excluded to prevent recursive counts. New files must be
staged before scanning. Initial coverage and migration commitments are in the
[approved plan](plans/2026-10-23-keepsail-brand-migration.md); rationale and external
cutover boundaries are in the [migration guide](keepsail-migration.md).

Every residual is classified. Import/environment names, wire/managed ownership,
historical evidence, real repository links, copyright attribution, old-version
tests and system-shell syntax have distinct reasons. A zero-count row matches the
path only. Tests retain legacy names as explicit compatibility fixtures; they do
not declare the former brand current. Recognition policy remains hash-identical.
Decision frontmatter reconciliation is native; locked bodies retain their hashes.

The native attestation for this Change is generated after implementation freeze;
its retained original subjects and review conclusions are classified as historical
delivery evidence separately from this source-snapshot matrix.

| File | Residual count | Reasons |
|---|---:|---|
| .github/workflows/merge-gate.yml | 4 | import-or-environment-compatibility=3; legacy-console-or-trusted-base=1 |
| .github/workflows/test.yml | 6 | import-or-environment-compatibility=6 |
| .gitignore | 8 | stable-managed-identity-and-explanation=8 |
| .harness/attestations/2026-06-04-layer2-merge-gate.jsonl | 6 | historical=6 |
| .harness/attestations/2026-06-04-review-identity-substrate.jsonl | 5 | historical=5 |
| .harness/attestations/2026-06-08-decision-records-anchors.jsonl | 43 | historical=43 |
| .harness/attestations/2026-06-11-doc-leg-derivable-docs.jsonl | 8 | historical=8 |
| .harness/attestations/2026-06-15-decision-text-lock.jsonl | 3 | historical=3 |
| .harness/attestations/2026-06-16-decision-executable-checks.jsonl | 3 | historical=3 |
| .harness/attestations/2026-06-17-agents-md-decision-conformance.jsonl | 6 | historical=6 |
| .harness/attestations/2026-06-20-tier-2-reviewable-anchors.jsonl | 3 | historical=3 |
| .harness/attestations/2026-06-23-auto-review-hardening-slice2.jsonl | 5 | historical=5 |
| .harness/attestations/2026-06-23-auto-review-hardening.jsonl | 21 | historical=21 |
| .harness/attestations/2026-06-23-check-drafting-assist.jsonl | 2 | historical=2 |
| .harness/attestations/2026-06-25-doc-deadref-gate.jsonl | 5 | historical=5 |
| .harness/attestations/2026-06-26-arm-legacy-decisions.jsonl | 1 | historical=1 |
| .harness/attestations/2026-06-26-gate-escape-hatch-hardening.jsonl | 8 | historical=8 |
| .harness/attestations/2026-06-26-generalize-gate-bypass-wording.jsonl | 2 | historical=2 |
| .harness/attestations/2026-06-26-language-profile-doc-refs.jsonl | 2 | historical=2 |
| .harness/attestations/2026-06-27-architecture-fitness.jsonl | 1 | historical=1 |
| .harness/attestations/2026-06-30-core-sensors-decoupling.jsonl | 7 | historical=7 |
| .harness/attestations/2026-06-30-fix-stale-cycle-comment.jsonl | 3 | historical=3 |
| .harness/attestations/2026-07-01-authoring-conformance-feedback-v6.jsonl | 6 | historical=6 |
| .harness/attestations/2026-07-01-codex-stop-delivery.jsonl | 8 | historical=8 |
| .harness/attestations/2026-07-02-active-change-recency.jsonl | 7 | historical=7 |
| .harness/attestations/2026-07-02-authoring-parallel-checks.jsonl | 6 | historical=6 |
| .harness/attestations/2026-07-02-gitignore-daemon-runtime.jsonl | 1 | historical=1 |
| .harness/attestations/2026-07-02-p0-gate-soundness-v3.jsonl | 9 | historical=9 |
| .harness/attestations/2026-07-02-sync-check-engineering-move-v3.jsonl | 7 | historical=7 |
| .harness/attestations/2026-07-02-unified-shell-runner.jsonl | 6 | historical=6 |
| .harness/attestations/2026-07-03-gate-in-process-daemon-demotion-v2.jsonl | 16 | historical=16 |
| .harness/attestations/2026-07-03-parse-ts-and-encoding-debt.jsonl | 24 | historical=24 |
| .harness/attestations/2026-07-03-writer-flock-toctou.jsonl | 5 | historical=5 |
| .harness/attestations/2026-07-04-architecture-norm-discovery-skill.jsonl | 2 | historical=2 |
| .harness/attestations/2026-07-06-codex-coverage-caveat-wording.jsonl | 3 | historical=3 |
| .harness/attestations/2026-07-06-docs-ia-narrative-layer.jsonl | 5 | historical=5 |
| .harness/attestations/2026-07-06-plan-redeclare-cli-verb.jsonl | 3 | historical=3 |
| .harness/attestations/2026-07-06-quickstart-adapters-and-zh-readme.jsonl | 1 | historical=1 |
| .harness/attestations/2026-07-06-remove-custom-plugin-loading.jsonl | 12 | historical=12 |
| .harness/attestations/2026-07-15-review-cost-breakdown.jsonl | 66 | historical=66 |
| .harness/attestations/2026-07-16-per-severity-round-policy.jsonl | 374 | historical=374 |
| .harness/attestations/2026-07-29-claude-cli-schema-fix.jsonl | 28 | historical=28 |
| .harness/attestations/2026-07-29-gate-authoring-space-v2.jsonl | 439 | historical=439 |
| .harness/attestations/2026-07-29-lint-ruff-pin.jsonl | 1 | historical=1 |
| .harness/attestations/2026-07-30-pitfall-is-proposed-decision.jsonl | 184 | historical=184 |
| .harness/attestations/2026-07-30-scope-and-review-import-fixes.jsonl | 310 | historical=310 |
| .harness/attestations/2026-08-06-plan-review-round-budget.jsonl | 305 | historical=305 |
| .harness/attestations/2026-08-06-plan-scope-fail-open.jsonl | 81 | historical=81 |
| .harness/attestations/2026-08-08-hint-and-disclosure-sweep.jsonl | 85 | historical=85 |
| .harness/attestations/2026-08-08-model-alias-suffix.jsonl | 36 | historical=36 |
| .harness/attestations/2026-08-08-plan-review-prompt.jsonl | 51 | historical=51 |
| .harness/attestations/2026-08-09-authorization-channel.jsonl | 263 | historical=263 |
| .harness/attestations/2026-08-20-windows-file-locks.jsonl | 71 | historical=71 |
| .harness/attestations/2026-09-04-product-baseline.jsonl | 37 | historical=37 |
| .harness/attestations/2026-09-04-windows-verification.jsonl | 247 | historical=247 |
| .harness/attestations/2026-09-11-plan-authority.jsonl | 397 | historical=397 |
| .harness/attestations/2026-09-15-plan-authority-alignment.jsonl | 225 | historical=225 |
| .harness/attestations/2026-10-22-attestation-contract-recovery.jsonl | 32 | historical=32 |
| .harness/attestations/code-only-recovery.jsonl | 129 | historical=129 |
| .harness/attestations/codex-agent-adapter.jsonl | 18 | historical=18 |
| .harness/attestations/init-interactive-wizard.jsonl | 352 | historical=352 |
| .harness/attestations/init-wizard-cohesion.jsonl | 307 | historical=307 |
| .harness/attestations/init-wizard-progressive-disclosure.jsonl | 252 | historical=252 |
| .harness/attestations/multi-independent-reviewer-gate.jsonl | 96 | historical=96 |
| .harness/attestations/plan-authoring-gate-v2.jsonl | 22 | historical=22 |
| .harness/attestations/record-gate-blocks.jsonl | 91 | historical=91 |
| .harness/attestations/report-doc-accuracy.jsonl | 19 | historical=19 |
| .harness/attestations/review-contract-compiler.jsonl | 209 | historical=209 |
| .harness/attestations/value-report-stage1.jsonl | 270 | historical=270 |
| .harness/attestations/verification-env-scrub.jsonl | 2 | historical=2 |
| .harness/review-recognition.yaml | 1 | recognized-policy-digest-preserved=1 |
| .importlinter | 6 | import-or-environment-compatibility=6 |
| AGENTS.md | 11 | existing-repository-link=1; stable-protocol-or-managed-identity=9; system-shell=1 |
| LICENSE | 1 | copyright-attribution=1 |
| README.md | 1 | migration-explanation=1 |
| README.zh-CN.md | 1 | migration-explanation=1 |
| docs/ARCHITECTURE.md | 8 | import-or-environment-compatibility=7; stable-protocol-or-managed-identity=1 |
| docs/adapters/claude-code.md | 7 | import-or-environment-compatibility=1; stable-protocol-or-managed-identity=6 |
| docs/adapters/codex.md | 1 | stable-protocol-or-managed-identity=1 |
| docs/adapters/openspec.md | 5 | stable-protocol-or-managed-identity=5 |
| docs/adapters/plain.md | 4 | stable-protocol-or-managed-identity=4 |
| docs/adopting.md | 1 | existing-repository-link=1 |
| docs/architecture-fitness.md | 1 | system-shell=1 |
| docs/cli-reference.md | 2 | import-or-environment-compatibility=1; stable-protocol-or-managed-identity=1 |
| docs/decisions/d-core-is-base.md | 7 | historical=7 |
| docs/decisions/d-dangling-check.md | 1 | historical=1 |
| docs/decisions/d-decision-records.md | 1 | historical=1 |
| docs/decisions/d-events-append-only.md | 2 | historical=2 |
| docs/decisions/d-fixed-transition-matrix.md | 1 | historical=1 |
| docs/decisions/d-gate-governs-git-product.md | 1 | historical=1 |
| docs/decisions/d-gh-cli-not-rest.md | 1 | historical=1 |
| docs/decisions/d-identity-resolution-order.md | 2 | historical=2 |
| docs/decisions/d-merge-gate-pure-git.md | 3 | historical=3 |
| docs/decisions/d-no-backticked-nonexistent-identifiers.md | 1 | historical=1 |
| docs/decisions/d-no-recovery-from-awaiting-code-review.md | 6 | historical=6 |
| docs/decisions/d-pitfall-is-proposed-decision.md | 2 | historical=2 |
| docs/decisions/d-single-gate-policy.md | 2 | historical=2 |
| docs/decisions/d-state-pure-fold.md | 1 | historical=1 |
| docs/getting-started.md | 4 | existing-repository-link=1; stable-protocol-or-managed-identity=3 |
| docs/keepsail-migration.md | 26 | import-or-environment-compatibility=6; migration-explanation=18; system-shell=2 |
| docs/plans/2026-06-02-superpowers-framework-adapter-design.md | 5 | historical=5 |
| docs/plans/2026-06-02-superpowers-framework-adapter.md | 11 | historical=11 |
| docs/plans/2026-06-03-layer2-merge-gate-design.md | 7 | historical=7 |
| docs/plans/2026-06-03-self-host-hard-gate-design.md | 9 | historical=9 |
| docs/plans/2026-06-03-self-host-hard-gate.md | 42 | historical=42 |
| docs/plans/2026-06-03-sync-gitignore-refresh-design.md | 8 | historical=8 |
| docs/plans/2026-06-03-sync-gitignore-refresh.md | 34 | historical=34 |
| docs/plans/2026-06-04-layer2-merge-gate-plan.md | 69 | historical=69 |
| docs/plans/2026-06-04-review-identity-substrate-design.md | 5 | historical=5 |
| docs/plans/2026-06-04-review-identity-substrate-plan.md | 40 | historical=40 |
| docs/plans/2026-06-05-decision-conformance-harness-design.md | 6 | historical=6 |
| docs/plans/2026-06-08-decision-records-anchors-design.md | 5 | historical=5 |
| docs/plans/2026-06-08-decision-records-anchors-plan.md | 92 | historical=92 |
| docs/plans/2026-06-09-capability-retirement-design.md | 3 | historical=3 |
| docs/plans/2026-06-10-capability-retirement-plan.md | 16 | historical=16 |
| docs/plans/2026-06-11-doc-leg-derivable-docs-design.md | 13 | historical=13 |
| docs/plans/2026-06-11-doc-leg-derivable-docs.md | 63 | historical=63 |
| docs/plans/2026-06-12-decision-text-lock-design.md | 2 | historical=2 |
| docs/plans/2026-06-15-decision-text-lock-implementation.md | 27 | historical=27 |
| docs/plans/2026-06-16-decision-executable-checks-implementation.md | 48 | historical=48 |
| docs/plans/2026-06-17-agents-md-decision-conformance-design.md | 19 | historical=19 |
| docs/plans/2026-06-17-agents-md-decision-conformance-implementation.md | 75 | historical=75 |
| docs/plans/2026-06-20-tier-2-reviewable-anchors-implementation.md | 41 | historical=41 |
| docs/plans/2026-06-23-arm-decision-teeth-design.md | 8 | historical=8 |
| docs/plans/2026-06-23-arm-decision-teeth-implementation.md | 34 | historical=34 |
| docs/plans/2026-06-23-auto-review-hardening-slice1-implementation.md | 86 | historical=86 |
| docs/plans/2026-06-23-auto-review-hardening-slice2-design.md | 2 | historical=2 |
| docs/plans/2026-06-23-auto-review-hardening-slice2-implementation.md | 64 | historical=64 |
| docs/plans/2026-06-23-check-drafting-assist-design.md | 5 | historical=5 |
| docs/plans/2026-06-23-check-drafting-assist.md | 22 | historical=22 |
| docs/plans/2026-06-25-codex-agent-adapter-design.md | 23 | historical=23 |
| docs/plans/2026-06-25-codex-agent-adapter-implementation.md | 97 | historical=97 |
| docs/plans/2026-06-25-doc-deadref-gate-impl.md | 56 | historical=56 |
| docs/plans/2026-06-25-doc-lifecycle-research-reframe.md | 3 | historical=3 |
| docs/plans/2026-06-26-gate-escape-hatch-hardening-design.md | 17 | historical=17 |
| docs/plans/2026-06-26-gate-escape-hatch-hardening-implementation.md | 61 | historical=61 |
| docs/plans/2026-06-26-language-profile-doc-refs-design.md | 10 | historical=10 |
| docs/plans/2026-06-26-language-profile-doc-refs-implementation.md | 22 | historical=22 |
| docs/plans/2026-06-27-architecture-fitness-decisions-design.md | 8 | historical=8 |
| docs/plans/2026-06-27-architecture-fitness.md | 14 | historical=14 |
| docs/plans/2026-06-29-core-adapters-sensors-decoupling.md | 83 | historical=83 |
| docs/plans/2026-07-01-authoring-time-conformance-sensor-design.md | 3 | historical=3 |
| docs/plans/2026-07-01-authoring-time-conformance-sensor-plan.md | 55 | historical=55 |
| docs/plans/2026-07-01-codex-stop-delivery-design.md | 4 | historical=4 |
| docs/plans/2026-07-01-codex-stop-delivery.md | 67 | historical=67 |
| docs/plans/2026-07-01-verification-env-scrub-design.md | 29 | historical=29 |
| docs/plans/2026-07-01-verification-env-scrub.md | 37 | historical=37 |
| docs/plans/2026-07-02-active-change-recency-plan.md | 5 | historical=5 |
| docs/plans/2026-07-02-authoring-parallel-checks-design.md | 1 | historical=1 |
| docs/plans/2026-07-02-authoring-parallel-checks-plan.md | 4 | historical=4 |
| docs/plans/2026-07-02-gitignore-daemon-runtime-plan.md | 8 | historical=8 |
| docs/plans/2026-07-02-p0-gate-soundness-plan.md | 10 | historical=10 |
| docs/plans/2026-07-02-sync-check-engineering-move-design.md | 11 | historical=11 |
| docs/plans/2026-07-02-unified-shell-runner-design.md | 4 | historical=4 |
| docs/plans/2026-07-02-unified-shell-runner-plan.md | 16 | historical=16 |
| docs/plans/2026-07-03-gate-in-process-daemon-demotion-design.md | 3 | historical=3 |
| docs/plans/2026-07-03-gate-in-process-daemon-demotion-plan.md | 151 | historical=151 |
| docs/plans/2026-07-03-parse-ts-and-encoding-debt.md | 22 | historical=22 |
| docs/plans/2026-07-03-writer-flock-toctou-plan.md | 9 | historical=9 |
| docs/plans/2026-07-04-architecture-fitness-doc-design.md | 8 | historical=8 |
| docs/plans/2026-07-04-architecture-fitness-doc-plan.md | 25 | historical=25 |
| docs/plans/2026-07-04-architecture-norm-discovery-skill-design.md | 14 | historical=14 |
| docs/plans/2026-07-04-architecture-norm-discovery-skill-plan.md | 38 | historical=38 |
| docs/plans/2026-07-06-codex-coverage-caveat-wording-plan.md | 11 | historical=11 |
| docs/plans/2026-07-06-docs-ia-narrative-layer-design.md | 8 | historical=8 |
| docs/plans/2026-07-06-docs-ia-narrative-layer-plan.md | 53 | historical=53 |
| docs/plans/2026-07-06-plan-redeclare-cli-verb.md | 14 | historical=14 |
| docs/plans/2026-07-06-plugin-loading-removal-design.md | 13 | historical=13 |
| docs/plans/2026-07-06-plugin-loading-removal-implementation.md | 44 | historical=44 |
| docs/plans/2026-07-06-quickstart-adapters-and-zh-readme-design.md | 10 | historical=10 |
| docs/plans/2026-07-06-quickstart-adapters-and-zh-readme-plan.md | 39 | historical=39 |
| docs/plans/2026-07-09-multi-independent-reviewer-gate-plan.md | 49 | historical=49 |
| docs/plans/2026-07-11-review-contract-compiler.md | 42 | historical=42 |
| docs/plans/2026-07-15-review-cost-breakdown.md | 11 | historical=11 |
| docs/plans/2026-07-15-value-report-stage1.md | 29 | historical=29 |
| docs/plans/2026-07-16-per-severity-round-policy-plan.md | 13 | historical=13 |
| docs/plans/2026-07-16-plan-authoring-gate-design.md | 2 | historical=2 |
| docs/plans/2026-07-16-plan-authoring-gate.md | 43 | historical=43 |
| docs/plans/2026-07-16-record-gate-blocks.md | 24 | historical=24 |
| docs/plans/2026-07-16-report-doc-accuracy.md | 5 | historical=5 |
| docs/plans/2026-07-17-init-interactive-wizard-design.md | 17 | historical=17 |
| docs/plans/2026-07-17-init-interactive-wizard-implementation.md | 162 | historical=162 |
| docs/plans/2026-07-18-init-wizard-cohesion.md | 56 | historical=56 |
| docs/plans/2026-07-20-init-wizard-progressive-disclosure-design.md | 12 | historical=12 |
| docs/plans/2026-07-20-init-wizard-progressive-disclosure.md | 21 | historical=21 |
| docs/plans/2026-07-29-claude-cli-schema-fix.md | 1 | historical=1 |
| docs/plans/2026-07-29-gate-authoring-space-v2-implementation.md | 80 | historical=80 |
| docs/plans/2026-07-29-lint-ruff-pin.md | 2 | historical=2 |
| docs/plans/2026-07-30-pitfall-is-proposed-decision-design.md | 2 | historical=2 |
| docs/plans/2026-07-30-pitfall-is-proposed-decision-implementation.md | 41 | historical=41 |
| docs/plans/2026-07-30-scope-and-review-import-fixes-implementation.md | 18 | historical=18 |
| docs/plans/2026-08-06-plan-review-round-budget-implementation.md | 19 | historical=19 |
| docs/plans/2026-08-06-plan-scope-fail-open.md | 8 | historical=8 |
| docs/plans/2026-08-08-hint-and-disclosure-sweep.md | 3 | historical=3 |
| docs/plans/2026-08-08-model-alias-suffix.md | 4 | historical=4 |
| docs/plans/2026-08-08-plan-review-prompt.md | 6 | historical=6 |
| docs/plans/2026-08-09-authorization-channel-design.md | 4 | historical=4 |
| docs/plans/2026-08-11-code-only-recovery.md | 11 | historical=11 |
| docs/plans/2026-08-20-windows-file-locks.md | 9 | historical=9 |
| docs/plans/2026-09-04-windows-verification.md | 36 | historical=36 |
| docs/plans/2026-09-11-plan-authority-implementation.md | 60 | historical=60 |
| docs/plans/2026-09-11-plan-authority-spec.md | 8 | historical=8 |
| docs/plans/2026-09-15-plan-authority-alignment-implementation.md | 19 | historical=19 |
| docs/plans/2026-10-22-attestation-contract-recovery.md | 1 | historical=1 |
| docs/plans/2026-10-23-keepsail-brand-migration.md | 141 | historical=141 |
| docs/product-architecture-coverage.md | 21 | import-or-environment-compatibility=21 |
| docs/product-foundations.md | 6 | historical=6 |
| docs/state-machine.md | 1 | import-or-environment-compatibility=1 |
| examples/demo-openspec-claude/.harness/adapters.yaml | 1 | historical=1 |
| examples/demo-openspec-claude/.harness/events.jsonl | 1 | historical=1 |
| examples/demo-openspec-claude/.harness/policy.yaml | 1 | historical=1 |
| examples/demo-openspec-claude/.harness/state.yaml | 2 | historical=2 |
| examples/demo-openspec-claude/AGENTS.md | 11 | existing-repository-link=1; stable-protocol-or-managed-identity=9; system-shell=1 |
| examples/demo-openspec-claude/README.md | 2 | import-or-environment-compatibility=2 |
| pyproject.toml | 15 | existing-repository-link=3; import-or-environment-compatibility=9; legacy-console-or-trusted-base=3 |
| scripts/audit_brand_names.py | 11 | inventory-scanner-pattern=11 |
| scripts/gen_cli_reference.py | 1 | import-or-environment-compatibility=1 |
| scripts/gen_state_machine.py | 5 | import-or-environment-compatibility=5 |
| scripts/smoke-gate.sh | 4 | import-or-environment-compatibility=2; system-shell=2 |
| skills/discovering-architecture-norms/SKILL.md | 2 | existing-repository-link=2 |
| src/super_harness/__init__.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/adapters/__init__.py | 5 | import-or-environment-compatibility=5 |
| src/super_harness/adapters/agent/__init__.py | 0 | compatibility import/resource path only |
| src/super_harness/adapters/agent/_settings_merge.py | 6 | stable-protocol-or-managed-identity=6 |
| src/super_harness/adapters/agent/_stop_protocol.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/adapters/agent/claude_code.py | 9 | import-or-environment-compatibility=4; stable-protocol-or-managed-identity=2; system-shell=3 |
| src/super_harness/adapters/agent/codex.py | 6 | import-or-environment-compatibility=4; stable-protocol-or-managed-identity=2 |
| src/super_harness/adapters/framework/__init__.py | 0 | compatibility import/resource path only |
| src/super_harness/adapters/framework/openspec.py | 7 | import-or-environment-compatibility=5; stable-protocol-or-managed-identity=2 |
| src/super_harness/adapters/framework/plain.py | 4 | import-or-environment-compatibility=2; stable-protocol-or-managed-identity=2 |
| src/super_harness/adapters/framework/superpowers.py | 8 | import-or-environment-compatibility=6; stable-protocol-or-managed-identity=2 |
| src/super_harness/adapters/install.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/adapters/registry.py | 6 | import-or-environment-compatibility=6 |
| src/super_harness/adapters/reviewer/__init__.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/adapters/reviewer/base.py | 0 | compatibility import/resource path only |
| src/super_harness/adapters/reviewer/claude_cli.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/adapters/reviewer/codex_cli.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/adapters/reviewer/registry.py | 3 | import-or-environment-compatibility=3 |
| src/super_harness/cli/__init__.py | 25 | import-or-environment-compatibility=25 |
| src/super_harness/cli/adapter.py | 12 | import-or-environment-compatibility=12 |
| src/super_harness/cli/attest.py | 10 | import-or-environment-compatibility=10 |
| src/super_harness/cli/change.py | 15 | import-or-environment-compatibility=15 |
| src/super_harness/cli/decision.py | 11 | import-or-environment-compatibility=11 |
| src/super_harness/cli/doc.py | 6 | import-or-environment-compatibility=6 |
| src/super_harness/cli/done.py | 22 | import-or-environment-compatibility=21; stable-protocol-or-managed-identity=1 |
| src/super_harness/cli/errors.py | 1 | existing-repository-link=1 |
| src/super_harness/cli/event.py | 5 | import-or-environment-compatibility=5 |
| src/super_harness/cli/gate.py | 10 | import-or-environment-compatibility=10 |
| src/super_harness/cli/group_options.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/cli/implementation.py | 13 | import-or-environment-compatibility=13 |
| src/super_harness/cli/init.py | 26 | import-or-environment-compatibility=23; stable-protocol-or-managed-identity=3 |
| src/super_harness/cli/init_executor.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/cli/init_github.py | 5 | import-or-environment-compatibility=2; stable-protocol-or-managed-identity=3 |
| src/super_harness/cli/init_models.py | 0 | compatibility import/resource path only |
| src/super_harness/cli/init_plan.py | 5 | import-or-environment-compatibility=2; stable-protocol-or-managed-identity=3 |
| src/super_harness/cli/init_ui.py | 3 | import-or-environment-compatibility=3 |
| src/super_harness/cli/lazy_group.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/cli/observe.py | 6 | import-or-environment-compatibility=6 |
| src/super_harness/cli/on_merge.py | 10 | import-or-environment-compatibility=10 |
| src/super_harness/cli/output.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/cli/plan.py | 14 | import-or-environment-compatibility=14 |
| src/super_harness/cli/pr.py | 17 | import-or-environment-compatibility=17 |
| src/super_harness/cli/report.py | 7 | import-or-environment-compatibility=7 |
| src/super_harness/cli/review.py | 15 | import-or-environment-compatibility=15 |
| src/super_harness/cli/sensor.py | 5 | import-or-environment-compatibility=5 |
| src/super_harness/cli/state.py | 8 | import-or-environment-compatibility=8 |
| src/super_harness/cli/status.py | 14 | import-or-environment-compatibility=14 |
| src/super_harness/cli/sync.py | 14 | import-or-environment-compatibility=14 |
| src/super_harness/cli/verification.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/cli/verify.py | 15 | import-or-environment-compatibility=14; stable-protocol-or-managed-identity=1 |
| src/super_harness/cli/verify_render.py | 0 | compatibility import/resource path only |
| src/super_harness/core/__init__.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/core/_registry.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/active_change.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/anchor_scanner.py | 0 | compatibility import/resource path only |
| src/super_harness/core/approval.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/core/authoring_check.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/check_runner.py | 7 | import-or-environment-compatibility=5; system-shell=2 |
| src/super_harness/core/clock.py | 0 | compatibility import/resource path only |
| src/super_harness/core/decision_check.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/core/decisions.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/core/doc_check.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/doc_refs.py | 3 | import-or-environment-compatibility=3 |
| src/super_harness/core/emit_validation.py | 6 | import-or-environment-compatibility=6 |
| src/super_harness/core/events.py | 0 | compatibility import/resource path only |
| src/super_harness/core/file_lock.py | 0 | compatibility import/resource path only |
| src/super_harness/core/frontmatter.py | 0 | compatibility import/resource path only |
| src/super_harness/core/gate_blocks.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/identity.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/language_profile.py | 0 | compatibility import/resource path only |
| src/super_harness/core/parse_ts.py | 0 | compatibility import/resource path only |
| src/super_harness/core/paths.py | 0 | compatibility import/resource path only |
| src/super_harness/core/plan_paths.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/post_emit.py | 5 | import-or-environment-compatibility=5 |
| src/super_harness/core/reducer.py | 6 | import-or-environment-compatibility=6 |
| src/super_harness/core/review_bundle.py | 6 | import-or-environment-compatibility=6 |
| src/super_harness/core/review_checklist.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/core/review_verdict.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/scope_match.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/core/shell_runner.py | 15 | import-or-environment-compatibility=2; system-shell=13 |
| src/super_harness/core/slug.py | 0 | compatibility import/resource path only |
| src/super_harness/core/source_scope.py | 0 | compatibility import/resource path only |
| src/super_harness/core/state.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/core/state_snapshot.py | 3 | import-or-environment-compatibility=3 |
| src/super_harness/core/state_yaml.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/core/transitions.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/core/ulid.py | 0 | compatibility import/resource path only |
| src/super_harness/core/workspace.py | 0 | compatibility import/resource path only |
| src/super_harness/core/writer.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/daemon/__init__.py | 0 | compatibility import/resource path only |
| src/super_harness/daemon/framework_observer.py | 7 | import-or-environment-compatibility=7 |
| src/super_harness/daemon/hook_entry.py | 20 | import-or-environment-compatibility=20 |
| src/super_harness/daemon/server.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/daemon/supervisor.py | 0 | compatibility import/resource path only |
| src/super_harness/engineering/__init__.py | 0 | compatibility import/resource path only |
| src/super_harness/engineering/agents_md.py | 24 | stable-protocol-or-managed-identity=24 |
| src/super_harness/engineering/agents_md_render.py | 15 | existing-repository-link=1; import-or-environment-compatibility=9; stable-protocol-or-managed-identity=4; system-shell=1 |
| src/super_harness/engineering/attestation.py | 5 | import-or-environment-compatibility=5 |
| src/super_harness/engineering/gh.py | 0 | compatibility import/resource path only |
| src/super_harness/engineering/gitignore_injector.py | 6 | stable-protocol-or-managed-identity=6 |
| src/super_harness/engineering/operation_log.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/engineering/pr_metadata.py | 10 | import-or-environment-compatibility=5; stable-protocol-or-managed-identity=5 |
| src/super_harness/engineering/review_budget.py | 3 | import-or-environment-compatibility=3 |
| src/super_harness/engineering/review_contract.py | 7 | import-or-environment-compatibility=7 |
| src/super_harness/engineering/review_governance.py | 0 | compatibility import/resource path only |
| src/super_harness/engineering/review_profiles.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/engineering/review_runs.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/engineering/sync_check.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/engineering/value_report.py | 5 | import-or-environment-compatibility=5 |
| src/super_harness/engineering/verification_config.py | 6 | import-or-environment-compatibility=1; system-shell=5 |
| src/super_harness/exit_codes.py | 0 | compatibility import/resource path only |
| src/super_harness/gates/__init__.py | 2 | import-or-environment-compatibility=2 |
| src/super_harness/gates/decisions.py | 1 | import-or-environment-compatibility=1 |
| src/super_harness/gates/pre_tool_use.py | 7 | import-or-environment-compatibility=7 |
| src/super_harness/gates/registry.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/sensors/__init__.py | 8 | import-or-environment-compatibility=8 |
| src/super_harness/sensors/dispatcher.py | 6 | import-or-environment-compatibility=6 |
| src/super_harness/sensors/pr_decorator.py | 4 | import-or-environment-compatibility=4 |
| src/super_harness/sensors/registry.py | 3 | import-or-environment-compatibility=3 |
| src/super_harness/sensors/verification_runner.py | 17 | import-or-environment-compatibility=17 |
| src/super_harness/templates/__init__.py | 0 | compatibility import/resource path only |
| src/super_harness/templates/derived_docs_defaults.yaml | 0 | compatibility import/resource path only |
| src/super_harness/templates/pull_request_template.md | 2 | stable-protocol-or-managed-identity=2 |
| src/super_harness/templates/super_harness_workflow.yml | 5 | import-or-environment-compatibility=3; legacy-console-or-trusted-base=1; stable-protocol-or-managed-identity=1 |
| src/super_harness/templates/verification_defaults.yaml | 3 | system-shell=3 |
| src/super_harness/version.py | 0 | compatibility import/resource path only |
| tests/e2e/conftest.py | 8 | import-or-environment-compatibility=8 |
| tests/e2e/test_pre_tool_use_claude_code.py | 2 | import-or-environment-compatibility=2 |
| tests/integration/adapter/test_claude_code.py | 11 | import-or-environment-compatibility=1; legacy-compatibility-test=10 |
| tests/integration/adapter/test_openspec.py | 4 | import-or-environment-compatibility=1; legacy-compatibility-test=3 |
| tests/integration/adapter/test_superpowers_registered.py | 3 | import-or-environment-compatibility=3 |
| tests/integration/cli/test_adapter.py | 19 | import-or-environment-compatibility=3; legacy-compatibility-test=16 |
| tests/integration/cli/test_adapter_install.py | 1 | import-or-environment-compatibility=1 |
| tests/integration/cli/test_change.py | 2 | import-or-environment-compatibility=2 |
| tests/integration/cli/test_init.py | 102 | import-or-environment-compatibility=81; legacy-compatibility-test=21 |
| tests/integration/cli/test_init_setup_github.py | 119 | import-or-environment-compatibility=89; legacy-compatibility-test=30 |
| tests/integration/cli/test_init_windows_entrypoint.py | 37 | import-or-environment-compatibility=32; legacy-compatibility-test=5 |
| tests/integration/cli/test_keepsail_compatibility.py | 9 | import-or-environment-compatibility=1; legacy-compatibility-test=8 |
| tests/integration/cli/test_on_merge.py | 7 | import-or-environment-compatibility=7 |
| tests/integration/cli/test_pr_emit_opened.py | 11 | import-or-environment-compatibility=11 |
| tests/integration/cli/test_pr_validate.py | 14 | import-or-environment-compatibility=8; legacy-compatibility-test=6 |
| tests/integration/cli/test_status.py | 33 | import-or-environment-compatibility=33 |
| tests/integration/cli/test_sync.py | 22 | import-or-environment-compatibility=5; legacy-compatibility-test=17 |
| tests/integration/cli/test_verification.py | 2 | import-or-environment-compatibility=1; system-shell=1 |
| tests/integration/core/test_writer_concurrency.py | 10 | import-or-environment-compatibility=10 |
| tests/integration/daemon/test_daemonize.py | 2 | import-or-environment-compatibility=2 |
| tests/integration/daemon/test_framework_observer.py | 3 | import-or-environment-compatibility=3 |
| tests/integration/daemon/test_hook_entry.py | 8 | import-or-environment-compatibility=8 |
| tests/integration/daemon/test_observer_host.py | 3 | import-or-environment-compatibility=3 |
| tests/integration/lifecycle/test_plan_authority.py | 22 | import-or-environment-compatibility=21; system-shell=1 |
| tests/integration/lifecycle/test_state_commands.py | 3 | import-or-environment-compatibility=3 |
| tests/integration/test_authoring_parallel.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/adapters/framework/test_openspec.py | 8 | import-or-environment-compatibility=4; legacy-compatibility-test=4 |
| tests/unit/adapters/framework/test_plain.py | 5 | import-or-environment-compatibility=1; legacy-compatibility-test=4 |
| tests/unit/adapters/framework/test_superpowers.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/adapters/reviewer/test_claude_cli.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/adapters/reviewer/test_codex_cli.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/adapters/reviewer/test_registry.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/adapters/test_claude_code.py | 30 | import-or-environment-compatibility=23; legacy-compatibility-test=4; system-shell=3 |
| tests/unit/adapters/test_codex.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/adapters/test_install.py | 2 | import-or-environment-compatibility=1; legacy-compatibility-test=1 |
| tests/unit/adapters/test_protocol.py | 6 | import-or-environment-compatibility=6 |
| tests/unit/adapters/test_registry.py | 14 | import-or-environment-compatibility=14 |
| tests/unit/adapters/test_settings_merge.py | 33 | import-or-environment-compatibility=7; legacy-compatibility-test=22; system-shell=4 |
| tests/unit/adapters/test_stop_protocol.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/cli/test_attest.py | 9 | import-or-environment-compatibility=9 |
| tests/unit/cli/test_decision.py | 15 | import-or-environment-compatibility=7; system-shell=8 |
| tests/unit/cli/test_doc.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/cli/test_doc_refs_cli.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/cli/test_done.py | 23 | import-or-environment-compatibility=10; legacy-compatibility-test=8; system-shell=5 |
| tests/unit/cli/test_entrypoint.py | 10 | import-or-environment-compatibility=10 |
| tests/unit/cli/test_errors.py | 3 | existing-repository-link=2; import-or-environment-compatibility=1 |
| tests/unit/cli/test_gate.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/cli/test_gate_check.py | 4 | import-or-environment-compatibility=4 |
| tests/unit/cli/test_group_options.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/cli/test_implementation.py | 9 | import-or-environment-compatibility=9 |
| tests/unit/cli/test_init_executor.py | 4 | import-or-environment-compatibility=4 |
| tests/unit/cli/test_init_models.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/cli/test_init_plan.py | 7 | import-or-environment-compatibility=2; legacy-compatibility-test=5 |
| tests/unit/cli/test_init_ui.py | 12 | import-or-environment-compatibility=7; legacy-compatibility-test=5 |
| tests/unit/cli/test_lazy_group.py | 6 | import-or-environment-compatibility=6 |
| tests/unit/cli/test_observe.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/cli/test_output.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/cli/test_plan.py | 8 | import-or-environment-compatibility=8 |
| tests/unit/cli/test_plan_records_artifacts.py | 6 | import-or-environment-compatibility=6 |
| tests/unit/cli/test_report.py | 4 | import-or-environment-compatibility=4 |
| tests/unit/cli/test_review.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/cli/test_review_human.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/cli/test_review_prepare.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/cli/test_review_runs.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/cli/test_review_verdict_gate.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/cli/test_sensor.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/cli/test_sync.py | 8 | import-or-environment-compatibility=8 |
| tests/unit/cli/test_verify.py | 26 | import-or-environment-compatibility=10; legacy-compatibility-test=8; system-shell=8 |
| tests/unit/cli/test_verify_render.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_active_change.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_anchor_scanner.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_approval.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_authoring_check.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/core/test_check_runner.py | 20 | import-or-environment-compatibility=8; system-shell=12 |
| tests/unit/core/test_decision_check.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/core/test_decisions.py | 11 | import-or-environment-compatibility=11 |
| tests/unit/core/test_doc_check_engine.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_doc_check_loader.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_doc_refs.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_emit_validation.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_events.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_file_lock.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_frontmatter.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_gate_blocks.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_identity.py | 16 | import-or-environment-compatibility=16 |
| tests/unit/core/test_language_profile.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_no_plugin_exec.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/core/test_parse_ts.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_paths.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_paths_canonical_relpath.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_plan_paths.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_post_emit.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/core/test_reducer.py | 6 | import-or-environment-compatibility=6 |
| tests/unit/core/test_reducer_plan_artifacts.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/core/test_review_bundle.py | 10 | import-or-environment-compatibility=10 |
| tests/unit/core/test_review_checklist.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_review_verdict.py | 18 | import-or-environment-compatibility=18 |
| tests/unit/core/test_scope_match.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/core/test_shell_runner.py | 6 | import-or-environment-compatibility=5; system-shell=1 |
| tests/unit/core/test_slug.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_source_scope.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_state.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_state_snapshot.py | 4 | import-or-environment-compatibility=4 |
| tests/unit/core/test_state_yaml.py | 4 | import-or-environment-compatibility=4 |
| tests/unit/core/test_transitions.py | 6 | import-or-environment-compatibility=6 |
| tests/unit/core/test_ulid.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/core/test_workspace.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/core/test_writer.py | 8 | import-or-environment-compatibility=8 |
| tests/unit/daemon/test_framework_observer.py | 8 | import-or-environment-compatibility=8 |
| tests/unit/daemon/test_hook_entry.py | 4 | import-or-environment-compatibility=4 |
| tests/unit/daemon/test_hook_entry_decide.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/engineering/test_agents_md.py | 27 | import-or-environment-compatibility=1; legacy-compatibility-test=26 |
| tests/unit/engineering/test_agents_md_render.py | 38 | existing-repository-link=1; import-or-environment-compatibility=18; legacy-compatibility-test=19 |
| tests/unit/engineering/test_attestation.py | 9 | import-or-environment-compatibility=9 |
| tests/unit/engineering/test_gh.py | 42 | import-or-environment-compatibility=42 |
| tests/unit/engineering/test_gitignore_injector.py | 16 | import-or-environment-compatibility=5; legacy-compatibility-test=11 |
| tests/unit/engineering/test_operation_log.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/engineering/test_pr_metadata.py | 21 | import-or-environment-compatibility=7; legacy-compatibility-test=14 |
| tests/unit/engineering/test_review_budget.py | 21 | import-or-environment-compatibility=21 |
| tests/unit/engineering/test_review_contract.py | 4 | import-or-environment-compatibility=4 |
| tests/unit/engineering/test_review_governance.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/engineering/test_review_observations.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/engineering/test_review_profiles.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/engineering/test_review_runs.py | 6 | import-or-environment-compatibility=6 |
| tests/unit/engineering/test_sync_check.py | 9 | import-or-environment-compatibility=9 |
| tests/unit/engineering/test_value_report.py | 6 | import-or-environment-compatibility=6 |
| tests/unit/engineering/test_verification_config.py | 13 | import-or-environment-compatibility=2; system-shell=11 |
| tests/unit/gates/test_decisions.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/gates/test_pre_tool_use.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/gates/test_protocol.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/gates/test_registry.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/scripts/test_gen_cli_reference.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/scripts/test_gen_state_machine.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/sensors/test_dispatcher.py | 5 | import-or-environment-compatibility=5 |
| tests/unit/sensors/test_pr_decorator.py | 24 | import-or-environment-compatibility=23; legacy-compatibility-test=1 |
| tests/unit/sensors/test_protocol.py | 1 | import-or-environment-compatibility=1 |
| tests/unit/sensors/test_registry.py | 3 | import-or-environment-compatibility=3 |
| tests/unit/sensors/test_verification_runner.py | 22 | import-or-environment-compatibility=18; system-shell=4 |
| tests/unit/templates/test_super_harness_workflow.py | 2 | import-or-environment-compatibility=2 |
| tests/unit/test_smoke.py | 2 | import-or-environment-compatibility=2 |

