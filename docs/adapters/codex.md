# Codex adapter

## Selected Windows desktop context revision (2026-10-28)

The current Change selects local Codex desktop for actual context acceptance because
Claude is unavailable to the owner. Optional `--knowledge-context` adds explicit
startup binding, complete-return observation and a multi-path patch prerequisite.
See [session context](../knowledge-context.md) for the exact workflow, current
candidate wire contract, declarations and native opt-out. Default installation
retains the legacy behavior described below. Historical desktop A/B facts and the
current compact observer's acceptance have separate scopes; see the
[acceptance note](../harness-context-acceptance.md). Process fixtures do not
establish actual host activation.

Current host capabilities must be distinguished from the adapter's declared edit
surface. Historical statements below about Codex exposing only shell/MCP tools are
not a current host capability verdict. The context revision selects native
`apply_patch`, parses all file/move paths and uses the same lifecycle allowances;
the legacy shim still passes no resolved path.

The Codex adapter wires the OpenAI Codex CLI to keepsail. It is the second
agent adapter in v0.1 and is **experimental** (API stability may change). Claude
Code remains the reference adapter — see [Claude Code adapter](claude-code.md).

It registers three hooks into `<repo>/.codex/hooks.json` (the same shape as
Claude's settings.json hooks block; only the matcher + marker differ): a
**PreToolUse** gate, a **SessionStart** context hook, and a turn-end **Stop**
authoring-conformance advisory.

## Installed hooks

- **PreToolUse gate** — blocks `apply_patch` (and `Edit` / `Write`) edits when the
  current lifecycle state forbids the mutation, via stdout `permissionDecision`.
- **SessionStart** — emits developer context at the start of a session.
- **Stop (turn-end feedback)** — runs the authoring-time conformance check for any
  ratified decision that opted in (`authoring_time: true`) and feeds a failure back
  as a non-blocking advisory.

## Install

```bash
keepsail adapter install codex
```

This writes all three hooks into `.codex/hooks.json` as one settings
transaction. Before the first write, keepsail freezes the original and
desired bytes plus the resolved `keepsail-hook` and `keepsail`
executable paths. Apply revalidates those inputs; settings or PATH drift stops
the install before a backup or write and asks you to review again.

Backup behavior reflects the final transaction, not each hook:

- A fresh `.codex/hooks.json` creates no backup.
- A changed existing file creates exactly one sibling
  `hooks.json.keepsail-backup.<time_ns>` containing the exact original
  bytes.
- An already-current file is not rewritten and creates no backup.

Writes and uninstall use the same exclusive sibling lock and atomic replace.
A concurrent live writer is refused; a lock whose owner process is no longer
alive is reclaimed, while a fresh corrupt lock is left alone until it is old
enough to be safely treated as stale. Symlinked settings files are refused so a
replace cannot unexpectedly modify or detach a linked target. These paths use
stdlib platform checks, including native Windows process-liveness handling.

> **Required trust step.** After `adapter install codex` the gate is **INACTIVE**
> until you run `/hooks` in Codex and trust the keepsail hook. Codex skips
> new or changed hooks until a human trusts them (trust is keyed to the hook's
> hash); if you reinstall or relocate the `keepsail-hook` binary, re-trust it.

On a pre-existing repo, also run `keepsail sync --gitignore` so
`.codex/hooks.json` is ignored by git.

**Coverage caveat.** The PreToolUse gate is registered for the edit tools
`apply_patch` / `Edit` / `Write` (in practice `apply_patch`, Codex's patch
primitive). It does not gate Bash / shell commands or non-shell tools such as
WebSearch, so real-time coverage is narrower than Claude Code's. The CI cold-path
gates back the gap: even an edit the hot path misses is caught before merge.

## What it injects into AGENTS.md

`adapter install codex` injects a keepsail (Codex) subsection into
`AGENTS.md` telling the agent the conventions: a PreToolUse hook gates the
workspace; when a tool call is blocked, run `keepsail status` for the next
step and `keepsail change resume <change_id>` to restore context; never work
around the gate (overriding is a human-only decision, recorded and disclosed at
the merge gate); recognized external plan/code evidence; approval-bound
implementation assessments/coverage; and the turn-end authoring check.

The owner configures `.harness/review-recognition.yaml`. An external process
produces a conclusion with exact subject, explicit approve/reject, original
evidence and provenance. Import JSON directly using
`review import <change> --evidence -`, or use a workspace file.
The core does not spawn Codex, select models, prepare invocations, authorize
retries or confirm human nonces. Failure, empty output and skip do not approve.

Wait for pending review before edits. Code fixes use `implementation reopen`
and fresh verification/code evidence. File additions within approved commitments
update assessment/coverage; changed commitments or relaxed restrictions require
new plan approval. Review can read unchanged repository context while retaining
an exact subject. See [Getting started](../getting-started.md) and
[Report semantics](../reporting.md) for usage and evidence limits.

## Common issues

- **Edits aren't blocked** — you haven't `/hooks`-trusted the hook yet, or you
  reinstalled/moved the binary and need to re-trust it. The gate is INACTIVE until
  trusted.
- **`.codex/hooks.json` shows up in `git status`** — run `keepsail sync
  --gitignore`.
- **Install says the settings or executable plan is stale** — another process or
  PATH update changed an input after review. Rerun init or `adapter install
  codex`; do not copy the old reviewed plan forward.
- **Install reports an update already in progress or an unsafe symlink** — let
  the other settings update finish, or replace the symlinked settings file or
  parent directory with a regular workspace-local path, then retry. Planning,
  apply, and uninstall reject symlinks from the workspace root through
  `.codex/hooks.json`. Stale owner locks are reclaimed automatically.

## Uninstall

```bash
keepsail adapter uninstall codex
```

Uninstall uses the same lock and atomic-write path as install. If a pristine
pre-install backup exists, it restores the earliest one. If installation began
with no settings file and therefore made no backup, uninstall removes only the
marker-owned PreToolUse, SessionStart, and Stop hooks. Unrelated settings and
hooks are preserved, empty hook scaffolding is pruned, and the settings file is
removed only when nothing user-owned remains. The `.codex/` directory itself is
not deleted.

## See also

- [Claude Code adapter](claude-code.md) — the reference agent adapter.
- [Getting started](../getting-started.md) — the full lifecycle walkthrough.
- [Limitations & FAQ](../limitations.md) — v0.1 boundaries.
