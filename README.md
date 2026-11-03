# Keepsail

Keep decisions and product knowledge effective across AI coding sessions.

**English** | [简体中文](README.zh-CN.md)

Keepsail is an open-source product-work control layer for developers and product
owners working with coding agents. It records what has been approved, which
product constraints apply, and what evidence supports completion, so agents can
work autonomously within agreed bounds and resume with the recorded context.

It works alongside your agent and development workflow through a CLI, agent
hooks and CI checks. Integrations include Claude Code, Codex (experimental),
OpenSpec, Superpowers and a plain CLI workflow.

**Status: alpha.** Knowledge delivery currently operates within one repository
using explicit rules and recognized applicability judgments. Integration coverage
varies by agent and mode; see [current limits](#current-limits).

## Why Keepsail?

Long-running agent work needs more than the current conversation:

- **Carry approvals forward.** Preserve objectives, acceptance obligations and
  restrictions. An approved plan permits implementation adjustments within those
  bounds, including added files, without restarting approval for every discovery.
- **Evolve product knowledge.** Retain versioned constraints and their rationale.
  When a constraint changes, record its impact on ongoing work and the decision
  to continue, adjust or seek renewed approval.
- **Resume with the recorded basis.** Recover approvals, supplied knowledge and
  unresolved matters across sessions. Optional context integration tracks what
  was supplied and what retrieval actually returned.
- **Make completion inspectable.** Bind review and verification evidence to the
  corresponding plan or code, and check configured rules on supported surfaces.

See the [Overview](docs/overview.md) for a worked scenario and the
[product architecture](docs/product-architecture.md) for the product's responsibilities.

## Install

Requirements: **Python 3.10+**, **Git** and **pipx**. Install from source:

```sh
git clone https://github.com/Dawinia/keepsail.git
cd keepsail
pipx install .
keepsail --version
```

If pipx is not installed, follow its [installation guide](https://pipx.pypa.io/stable/installation/).
GitHub integration additionally needs the [GitHub CLI](https://cli.github.com/)
and `gh auth login`; it is optional for the local quickstart.

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
- Knowledge selection uses explicit rules and recognized judgments. Shared
  cross-repository knowledge authority and complete semantic recall are not implemented.
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
| Understand the design | [Product architecture](docs/product-architecture.md) · [Internals](docs/ARCHITECTURE.md) |

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
