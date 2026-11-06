# Keepsail

An open-source control layer for product work across agent harnesses.

**English** | [简体中文](README.zh-CN.md)

With Keepsail, a product owner can approve what an agent should deliver, set the
limits of its authority, and later check what was actually reviewed and verified.
The agent can choose how to implement the plan within those limits. If the work
calls for a change to an agreed requirement, the change needs its own approval.

It works alongside your agent and development workflow through a CLI, agent
hooks and CI checks. Integrations include Claude Code, Codex (experimental),
OpenSpec, Superpowers and a plain CLI workflow.

**Status: alpha.** See [current limits](#current-limits) for integration coverage.

## Why Keepsail?

- **Give agents room to implement.** An agent can add a missing test fixture under
  an approved plan and record why. Dropping the acceptance test changes what the
  owner agreed to and requires a new plan review.
- **Catch departures from the plan.** Local hooks check selected editing actions.
  Before merge, configured checks can flag missing verification or a review that
  covers an earlier version of the code.
- **Hand work to the next session.** Recover the approved plan, applicable
  constraints and unresolved questions so another session can pick up the work.
- **Track changes to product knowledge.** When a recognized constraint changes,
  see which work received the earlier version and record how each affected change
  should proceed.

See the [Overview](docs/overview.md) for a worked scenario and the
[product architecture](docs/product-architecture.md) for the product's responsibilities.

## Install

Keepsail requires **Python 3.10+**. For the source installation below, you also
need Git and pipx on your `PATH`. Installing the current version of pipx requires
**Python 3.11+**. See the [pipx installation guide](https://pipx.pypa.io/stable/how-to/install-pipx.html).

```sh
git clone https://github.com/Dawinia/keepsail.git
cd keepsail
pipx install .
keepsail --version
```

To use the optional GitHub integration, install the [GitHub CLI](https://cli.github.com/)
and run `gh auth login`.

Upgrading from **super-harness**? Read the [migration guide](docs/keepsail-migration.md).

## Quickstart

Try the local lifecycle gate in a Git repository. First initialize Keepsail:

```sh
cd path/to/your-repo
keepsail init
```

Choose the agent integration during setup, or install one explicitly:

```sh
keepsail adapter install claude-code
# Alternatively:
keepsail adapter install codex
```

Open a new agent session in that repository and complete its hook trust steps.
For Codex, review and trust the Keepsail hooks using `/hooks` before proceeding.
See the [Claude Code](docs/adapters/claude-code.md) and
[Codex](docs/adapters/codex.md) setup guides for host-specific details.

Declare a change from your terminal:

```sh
keepsail change start my-change
keepsail status my-change
```

The change is now `INTENT_DECLARED`. With the hook active, an attempt to edit a
source file through a covered agent tool is blocked because the plan has not
been approved. This demonstrates the local gate; manual editor changes, shell
commands and MCP writes are outside this interception boundary.

To proceed, follow [Getting started](docs/getting-started.md) to configure the
owner-recognized review process, submit a plan and import its conclusion. The
normal path is:

```text
Declare → Plan review → Implement → Verify → Code review → Merge and archive
```

Keepsail imports review conclusions from your chosen process; it does not run
reviewers. Once approved, the agent can record implementation adjustments within
the plan's bounds. Changing those commitments requires appropriate new approval.

### Knowledge and session context

The [knowledge guide](docs/knowledge.md) covers policy activation, versioned
constraints, delivery and impact handling. These require explicit configuration.
For session-bound delivery and observed retrieval, follow the optional
[context integration guide](docs/knowledge-context.md), including the selected
Windows local Codex desktop setup. The basic quickstart does not enable that mode.

## Current limits

- Local hooks cover selected tools and require actual host activation. CI checks
  protect merges only when installed and required by branch protection.
- Knowledge delivery operates within one repository. It selects constraints through
  explicit rules and recognized applicability judgments.
- Recorded retrieval does not prove understanding; an agent's adoption statement
  does not prove compliance. Review quality remains the responsibility of the
  recognized process.

See [implementation coverage](docs/product-architecture-coverage.md) for dated
evidence and [Limitations & FAQ](docs/limitations.md) for operational details.

## Documentation

| Goal | Guide |
|---|---|
| Complete a change | [Getting started](docs/getting-started.md) · [Concepts](docs/concepts.md) |
| Manage knowledge and session continuity | [Knowledge](docs/knowledge.md) · [Session context](docs/knowledge-context.md) |
| Check architecture decisions | [Adopting](docs/adopting.md) |
| Configure integrations | [Agent and framework adapters](docs/adapters/) |
| Look up commands | [CLI reference](docs/cli-reference.md) |
| Understand the design | [Product architecture](docs/product-architecture.md) · [Implementation architecture](docs/implementation-architecture.md) |

Browse the [documentation index](docs/README.md) for the full set of guides.

## Help and contributing

Report bugs or propose improvements in [GitHub Issues](https://github.com/Dawinia/keepsail/issues).
For a bug report, include your OS, Keepsail version, agent integration, steps to
reproduce and relevant output with secrets removed.

Before making changes, read [AGENTS.md](AGENTS.md) for the repository's plan,
review and verification workflow. For development, create and activate a Python
virtual environment, then install from the repository root:

```sh
python -m pip install -e ".[dev]"
```

The project uses Ruff, mypy and pytest. Its configured checks run through
`keepsail verify`; see the [CLI reference](docs/cli-reference.md).

## License

[MIT](LICENSE).
