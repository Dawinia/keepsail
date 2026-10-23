# Keepsail

> A product-work control layer across agent harnesses.

**English** | [简体中文](README.zh-CN.md)

## What is Keepsail?

Keepsail keeps effective human commitments and long-lived product knowledge
consequential across continuous agent work. It supports autonomy within approved
bounds, knowledge evolution, continuity and traceability across agent harnesses.
Read the normative [product architecture](docs/product-architecture.md) and the
separate dated [implementation coverage](docs/product-architecture-coverage.md):
existing CLI, hooks and CI implement parts of these responsibilities.

Keepsail was named super-harness. The [migration guide](docs/keepsail-migration.md)
explains installation, compatibility identifiers and pending external actions.

See the [Overview](docs/overview.md) for the problem it solves, what v0.1 ships,
and how it relates to neighboring tools like Spec Kit, OpenSpec, and Superpowers.

## Install

```bash
# From a checkout containing this migration (registry publication is pending):
pipx install .
brew install gh && gh auth login   # gh is a prerequisite for init --setup-github
```

## Quickstart

Bootstrap a repo and watch the gate block an out-of-lifecycle edit — the whole
point of the tool:

```bash
# Install from the Keepsail checkout first: pipx install .
cd your-repo && keepsail init            # create the .harness/ data plane
keepsail adapter install claude-code     # wire your agent (auto-done by init if .claude/ exists)
#   or, for Codex:  keepsail adapter install codex   → then run /hooks in Codex to trust it
keepsail change start "my-change"        # → INTENT_DECLARED
# now have your agent (or you) try to edit code → the gate blocks it,
# because no plan review has happened yet. This demonstrates one control surface.
```

That is the shortest path to *seeing* keepsail work. The full arc — install
a framework adapter, get the plan reviewed, implement, verify, review, merge — is
the 10-minute [Getting started](docs/getting-started.md) walkthrough. To inspect a
pre-seeded non-trivial `.harness/` state without running anything, see the in-tree
demo [`examples/demo-openspec-claude/`](examples/demo-openspec-claude/). The
walkthrough shows the active review contract: the owner recognizes an external
process in `.harness/review-recognition.yaml`; the process supplies an explicit
plan/code conclusion, original evidence and provenance for the exact subject.
Import it with `keepsail review import`. Approved commitments authorize
implementation adjustments, with assessments and actual file coverage recorded
before completion. Review execution and retries belong to the external process.
Historical configuration and event records remain readable; the demo is historical
sample data, not an executable current-review recipe.

## Links

- [Documentation index](docs/README.md)
- [Overview](docs/overview.md) — what it is, what v0.1 ships, neighboring tools
- [Getting started](docs/getting-started.md) — full end-to-end walkthrough
- [Concepts](docs/concepts.md) — lifecycle, and what the harness does *not* do
- [Adopting](docs/adopting.md) — lock architecture rules in your own project
- [Limitations & FAQ](docs/limitations.md)
- [Agent adapters](docs/adapters/) — [Claude Code](docs/adapters/claude-code.md) · [Codex](docs/adapters/codex.md) (experimental)
- [CLI reference](docs/cli-reference.md)
- [Architecture](docs/ARCHITECTURE.md)

## License

MIT — see [`LICENSE`](LICENSE).
