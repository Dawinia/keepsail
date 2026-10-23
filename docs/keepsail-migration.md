# Migrating to Keepsail

Keepsail is the new name of super-harness. Its product definition remains the
[product-work control layer across agent harnesses](product-architecture.md).
The [dated coverage report](product-architecture-coverage.md) still records gaps;
renaming does not implement those missing capabilities.

## Install, upgrade and uninstall

This source change does not publish a package. Until a Keepsail release is actually
available, install from a checkout containing this migration:

```bash
pipx install .
# Development, inside a dedicated virtual environment:
python -m pip install -e '.[dev]'
keepsail --version
keepsail --help
```

After a release has been published, registry installation is `pipx install keepsail`
or `python -m pip install keepsail` inside a virtual environment. Bundled workflow
templates pin keepsail==0.1.0 and require that release to be published before use;
source installation alone does not make those registry jobs runnable.

Both distributions own the same Python files and legacy console entry points.
Do not install super-harness and keepsail together in one environment. For an
existing pip installation, record its source/version, back up local hook settings,
uninstall super-harness first, then install Keepsail from the selected source:

```bash
python -m pip show super-harness
python -m pip uninstall super-harness
python -m pip install /path/to/keepsail-checkout
python -m pip check
keepsail --version
super-harness --version
```

For pipx use `pipx uninstall super-harness` followed by `pipx install .` from the
selected checkout. This removes old hook executable paths: perform installation
and hook refresh together while no agent work is active. Keep the previous source
and its dependency/version record for rollback. To roll back, uninstall keepsail,
install the recorded old source/version and refresh adapters using the old CLI.
For ordinary Keepsail upgrades use `pipx upgrade keepsail` after publication, or
reinstall from the selected source. Uninstall adapters before removing Keepsail:
`keepsail adapter uninstall claude-code` / `keepsail adapter uninstall codex`, then
`pipx uninstall keepsail` (or `python -m pip uninstall keepsail`). Preserve the
workspace history unless its owner deliberately chooses otherwise.

## Existing workspaces and hook refresh

Keep the existing .harness directory in place. No ledger/state conversion, slug
change, subject rehash or historical review rewrite is required. Run Keepsail in
the same workspace and inspect `keepsail status` and `keepsail change resume`.
Existing SUPER_HARNESS environment variables retain their names and precedence.

After the new binaries are available on PATH, run `keepsail adapter install
claude-code` or `keepsail adapter install codex` for each installed agent. Installation
replaces managed hook commands using their stable ownership markers and backs up
changed settings; unrelated hooks remain. Inspect generated settings and, for
Codex, trust the updated hooks through /hooks. Absolute hook paths must be refreshed
after a pipx environment changes. Configured hooks alone do not prove active trust.

Use `keepsail sync --agents-md --gitignore --yes` for generated guidance. For GitHub
workflow/template upgrades, review `keepsail init --setup-github --force` in the
target workspace; existing-file overwrite choices and repository setting changes
remain visible. The generated workflow filename stays super-harness.yml so upgrades
replace one workflow rather than introducing a second set of jobs. Required branch
checks and trusted-base verifier installation must be inspected separately.

## Supported compatibility names

| Retained name | Reason |
|---|---|
| super_harness Python package and source filenames | One implementation; stable imports, locked decision checks and import-graph contracts. No separate keepsail Python namespace is promised. |
| super-harness, super-harness-hook, super-harness-daemon | Console aliases to the same functions as keepsail, keepsail-hook, keepsail-daemon; old callers keep working after installing Keepsail. |
| .harness/ and its config/event/state/receipt/attestation layout | Existing workspace identity and authority remain readable. |
| SUPER_HARNESS_* variables | Existing actor precedence, change overrides, verification scrubbing and test controls remain unchanged. |
| HTML section/framework/agent and PR metadata markers with super-harness | Stable ownership/deduplication and old PR parsing. Generate contents through the CLI. |
| super-harness version metadata field | Required machine key used by old and new PR validators. |
| super-harness gitignore markers, backup suffixes and settings lock suffix | Safe update/uninstall recognition and concurrent ownership across versions. |
| super_harness logger names and serialized schemas/keys | Machine consumer continuity; human-facing command text uses Keepsail. |
| super_harness_workflow.yml resource and super-harness.yml target | Stable resource/managed-file identity, independent of workflow display name. |
| Existing repository URLs | GitHub repository has not been renamed by this change; links continue to the real repository. |
| Historical plans, decision bodies, evidence and seeded demo records | Preserve the contemporaneous subject and original meaning. New branding never turns past skips into approvals. |
| sh shell executable/code fences, .sh scripts, superpowers | Shell/framework names, unrelated to the former product shorthand. Current product prose spells out Keepsail. |

JSON envelope keys, event types, review schema/process/policy digest, exit codes,
subject identities and verification authority are unchanged. Human-facing prefixes
and help text change to Keepsail; consumers should use the machine interface rather
than parsing prose. The observer daemon remains POSIX-only; the rename does not
extend platform support.

## External actions and name observations

On 2026-10-23 PyPI and npm exact Keepsail package endpoints returned HTTP404.
GitHub repository search returned only keepsail/keepsail.github.io. Broad public-web
search was unavailable (HTTP403). No serious same-domain conflict was established
by these bounded checks; they do not establish name ownership, trademark/domain
availability or a future right to publish.

This migration does not rename the GitHub repository, modify its description,
move E:/Work/super-harness, change the global editable installation, edit dependent
projects or relocate a saved Codex project. The current repository description
still uses the old positioning; the proposed description is “Product-work control
layer across agent harnesses”. Repository rename, redirects, links, required checks,
release settings and publishing credentials need a separate owner-controlled
cutover. No npm package/MCP server/plugin publication is introduced where this
Python repository has no such product. No placeholder package is published.

Local inventory found the global super-harness editable installation pointing to
E:/Work/super-harness and a saved Codex project entry for that path. Root local
Claude/Codex hook configuration files were absent when checked. Other projects
can retain old executable/import references through the supported aliases; they
need their own explicit update and installed-behavior verification before removing
compatibility names. Package release, repository rename, active hooks, deployed CI
and local external cutover are separate completion claims.

## Local validation evidence

The isolated migration worktree used a dedicated virtual environment. An initial
old-distribution editable install was uninstalled before installing Keepsail there;
the global old editable installation was left pointing at the daily main checkout.
The package build produced keepsail-0.1.0.tar.gz and a wheel built from that sdist.
Wheel metadata declares Keepsail and all six primary/legacy console entries, while
the sdist excludes local environments and scratch review evidence.

A separate temporary environment installed the wheel and imported super_harness
from site-packages outside the checkout. Eight installed-entrypoint/init/legacy-hook
tests passed with UTF-8 enabled, empty PYTHONPATH and that environment's Scripts
directory on PATH. Both installed CLI families returned identical JSON for the
existing main workspace, and Keepsail resume succeeded without changing event/state
bytes. The retained old l1_update_completed event warning remained readable as a
historical unknown-event warning; the rename does not add support for that event.

Affected adapter/init/sync/generator regression tests passed (156); a separate
focused portable/generator set passed (94). Initial whole-suite verification found
ten marker-assertion/generated-doc failures; those were corrected and rechecked.
The final exact-subject verification, review and attestation verdicts are lifecycle
evidence, separate from these local package observations. Native Windows does not
validate execution of the POSIX observer daemon; its console entry mapping is
checked, and Linux/macOS runtime evidence remains a separate layer.
