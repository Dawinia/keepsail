# Direct migration to Keepsail

Keepsail is the new name of this unpublished project. The runtime switches
directly: the Python package is `keepsail`; the commands are `keepsail`,
`keepsail-hook` and `keepsail-daemon`; environment variables use `KEEPSAIL_*`.
There are no old-name import shims, console aliases or environment fallbacks.

The product remains the [product-work control layer across agent harnesses](product-architecture.md).
The [dated coverage audit](product-architecture-coverage.md) is a historical
assessment; renaming does not implement its missing capabilities.

## Install from source

No package is published by this change. Record the previous installation source
and back up local settings before uninstalling it and installing Keepsail:

```bash
python -m pip show super-harness
python -m pip uninstall super-harness
python -m pip install /path/to/keepsail-checkout
python -m pip check
keepsail --version
keepsail --help
```

For development use `python -m pip install -e '.[dev]'` in a dedicated environment.
For pipx uninstall the former distribution, then `pipx install .` from the
selected source. Do not rely on a registry install before a release exists.
Bundled workflow release pins describe the eventual release installation;
local consumers of this unpublished revision must pin its actual source commit.

## Local workspace cutover

Keep `.harness/`, append-only events, derived state, change slugs, approvals,
subjects and attestation schemas intact. These are workspace authority.
Historical plans, evidence, fixture records and locked decision bodies retain
their original spelling. Namespace-bound decisions have ratified successors;
old bodies remain hash-locked. The recognition policy and its digest are unchanged.

Current generated ownership markers, metadata's `keepsail version` field,
backup/lock suffixes and the workflow filename `keepsail.yml` use the new name.
Existing workspaces need a one-time local conversion of old owned regions before
canonical regeneration. Back up originals and preserve text outside managed
regions. Use the original native injector to replace its owned region with
output from the new renderer. This is local maintenance: Keepsail does not ship
an old-marker reader or a migration compatibility layer.

After conversion use `keepsail sync --agents-md --gitignore --yes`, then refresh
each installed adapter with `keepsail adapter install <name>` and inspect
`keepsail status`. Adapter installation preserves unrelated hooks. Inspect
settings and required hook trust in the agent UI. Move the old workflow to
`keepsail.yml`; update current scripts, imports, environment variables and source
pins together. Preserve backups outside tracked product files. Active project
gates and review rules still apply; a local tool upgrade does not approve source edits.

Trusted-base CI derives the baseline distribution, import namespace and command
from the baseline's own committed `pyproject.toml`. It installs that trusted
revision, excludes candidate PYTHONPATH and checks installed module hashes.
The cutover PR can therefore use its older base verifier without shipping a
legacy runtime interface in the candidate.

## Boundaries and rollback

The canonical repository is [Dawinia/keepsail](https://github.com/Dawinia/keepsail).
The runtime migration merged in PR127; the subsequent repository cutover updates
current package, documentation and skill links to that address. Historical plans,
locked records and original evidence retain their contemporaneous URLs.

The local main checkout moved to `E:/Work/keepsail`. Reinstall editable packages
after a directory move and rebuild virtual environments whose launchers contain
absolute paths. Use native `git worktree repair` to repair linked worktree pointers
after moving the main checkout; older Git versions may not provide that command.
Back up and verify ignored authority/private data and untracked user files too.

Close or update applications that hold the old directory open. Saved project
configuration and the current application's cached workspace are separate:
update the project's name and primary folder through its supported UI, rather
than racing a live settings file or rewriting historical chat records. An empty
old directory held open by an application is not a runtime compatibility alias.

Local consumer workflow URLs use the canonical repository and immutable source
commits. Consumer edits remain local and preserve unrelated work and records.
Package publication, source-PR merge and POSIX daemon platform support are unchanged
by the repository-name operation.

Uninstall adapters through Keepsail before removing its distribution. To roll
back, restore backed-up generated settings and install the recorded old source;
never rewrite lifecycle history.
