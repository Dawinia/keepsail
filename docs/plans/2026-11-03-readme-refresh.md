---
change: 2026-11-03-readme-refresh
stage: plan
---

# Refresh the open-source project introduction

## Objective and authority

The user requested updates to the README following the preceding assessment,
with conventions appropriate for an open-source project. Refresh README.md,
README.zh-CN.md and their linked docs/overview.md against the normative
docs/product-architecture.md and current implementation at 7f5de5e.

## Commitments

- R1: Explain the product's purpose and benefits through approved work,
  long-lived knowledge, change impacts, continuity and evidence. Distinguish
  product scope from implemented integration coverage; retain the architecture.
- R2: Provide equivalent English and Chinese introductions using familiar
  open-source README sections: purpose, capabilities, installation, quickstart,
  documentation, help/contributing and license. Use relative repository links.
- R3: Make source installation and quickstart actionable: Python >=3.10, Git
  and pipx prerequisites; clone/install/version commands; gh only for optional
  GitHub setup. Describe selected-tool gate behavior and required host trust,
  without claiming arbitrary manual/shell/MCP writes are intercepted.
- R4: Describe current knowledge/context features with explicit single-repository,
  matching and host-integration limits. Link the opt-in context guide; do not
  present it as default behavior or equate retrieval with understanding.
- R5: Bring Overview into agreement with the README and architecture. Avoid
  unsupported comparisons to third-party products, invented badges, publication,
  adoption, CI or production claims. Preserve MIT attribution and migration links.

## Scope and implementation

Only the three introduction documents and this plan are intended tracked changes.
Rewrite the introductions concisely; keep protocol schemas and detailed internal
governance in their existing linked guides. Contribution guidance points to
existing Issues, project conventions and development checks without inventing
a new contribution policy. Preserve unrelated untracked files and all historical
evidence. Native lifecycle commands may retain required governance facts.

No runtime, normative architecture, recognition policy, ratified decision, hook
installation or trust changes. No push, PR, merge or release is part of this task.
Local commits may freeze the exact review subjects required by AGENTS.md.

## Validation and review

Obtain the independent Codex subagent plan review recognized by the repository
and import its exact conclusion before product edits. Check every local Markdown
link and changed whitespace, compare bilingual content and claims against source,
and inspect the resulting diff. Run decision check --changed and doc check.
Do not add runtime tests for a prose-only change. If completing the lifecycle
through done, run its required verification and obtain the exact-subject external
code review. Keep failures and unavailable evidence distinct from approval.

Reference for README organization: GitHub's About READMEs guidance
(https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes).
This is a convention guide, not a mandatory README schema.
