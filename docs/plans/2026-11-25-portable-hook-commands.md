---
change: 2026-11-25-portable-hook-commands
stage: plan
---

# Install agent hooks as structured invocations with a per-host transport

## Problem

On the owner's Windows machine every Claude Code hook keepsail installed in
`.claude/settings.local.json` fails. The installed commands carry raw Windows paths:

```text
E:\Work\keepsail\.venv\Scripts\keepsail.EXE change resume
```

Claude Code ran them through Git Bash, which treats `\` as an escape, so it executed
`E:Workkeepsail.venvScriptskeepsail.EXE` (observed at SessionStart on 2026-11-25:
`/usr/bin/bash: line 1: E:Workkeepsail.venvScriptskeepsail.EXE: command not found`).
The PreToolUse gate and the Stop hook use the same form, so **the edit gate has not
run in this workspace since the file was rewritten on 2026-11-22**. The command that
rewrote it is not recorded; its content matches a non-context install.

Reproduction: `bash -c 'echo E:\\Work\\keepsail\\.venv'` prints `E:Workkeepsail.venv`.

## Root cause

Hook commands are built as strings in four separate ad hoc ways, and only two of
them make the path safe for the shell that will interpret them:

| Adapter / mode | Where | Rendering | Result |
|---|---|---|---|
| Claude Code, default | `claude_code.py:239-257` | raw `f"{path} ..."` | breaks on Windows (backslashes) and on any OS for paths with spaces |
| Claude Code, `--knowledge-context` | `claude_code.py:259-270` | `/` + `shlex.quote` | works under bash; breaks if Claude Code falls back to PowerShell |
| Codex, default | `codex.py:204-212`, `:230-235` | raw `f"{path} ..."` | breaks on any OS for paths with spaces |
| Codex, `--knowledge-context` | `codex.py:219-227` | `powershell.exe -Command "& '<path>' ..."` | works on Windows; written on every OS, including where it cannot run |

`shutil.which()` returns `/…/bin/keepsail` on macOS/Linux, which survives the raw
form; on Windows it returns `E:\…\keepsail.EXE`, which does not. The tests pin the raw
form with POSIX-style fake paths (`tests/integration/adapter/test_claude_code.py:67`,
`tests/unit/adapters/test_claude_code.py:30-37`, and the files listed under Tests),
so the macOS/Linux CI matrix could not see it. Mode detection
(`_context_hook_installed`, `_context_installed`) and hook ownership
(`_settings_merge._command_contains` substring markers) each re-interpret command
strings with their own rules.

The underlying design fault: a hook is modelled as a shell string, so correctness
depends on guessing which shell the host will use.

## Host facts this plan relies on

- **Claude Code** (https://code.claude.com/docs/en/hooks, read 2026-11-26): a command
  hook's `command` string runs under `sh -c` on macOS/Linux and Git Bash on Windows,
  or PowerShell when Git Bash is not installed. When `args` is present ("exec form"),
  Claude Code "spawns it directly with `args` as the argument vector. There is no
  shell"; on Windows `command` must be a real executable such as a `.exe`. `timeout`
  is a common field. The version that introduced `args` is not stated in the docs or
  in the visible changelog, and what an older host does with an `args` field is
  unknown.
- **Codex** (https://learn.chatgpt.com/docs/hooks and the config reference, read
  2026-11-26): `command` is a string; the docs do not state how it is executed on any
  platform and document no argv form. A Windows-only `commandWindows` override exists.
  Codex's hook shell on Windows is therefore unknown; the PowerShell wrapper above is
  proven on this machine's Codex desktop. On macOS/Linux the documented examples use
  `$(...)`, which implies a POSIX shell (inference, not a documented fact). Codex
  trust is keyed to the hook's hash; exactly which fields the hash covers is not
  documented (so "no re-trust" below is an inference).
- The Codex knowledge-context retrieval protocol is pinned to the
  `powershell-exit/v1` return transport (`src/keepsail/core/knowledge.py:38`), used
  by `core/context.py` and `daemon/codex_context_hook.py`.
- `keepsail-hook` with an empty argv exits 0 (allow) by design
  (`src/keepsail/daemon/hook_entry.py:122-127`, "harness must not block tools it
  doesn't understand"). A host that ran an exec-form handler's `command` without its
  `args` would therefore disable the gate silently. This plan does not change that
  runtime rule; it prevents such hosts at install time (commitment 3).

## Design

Three layers, so that adding a host later (for example DeepSeek Harness `dsh` or
`pi`) means writing one encoder and choosing a transport, without touching other
adapters:

| Layer | Owns | Agent-specific? |
|---|---|---|
| `HookInvocation` | what to run: event, executable path, and an argument list in which each item is explicitly either a literal or a path (structured, never a shell string) | no |
| `HookTransport` | how a host executes it: `encode(invocation) -> handler fields`, `decode(handler) -> HookInvocation or None` | no; reusable, chosen per host |
| adapter encoder | where and in what file format the handler is persisted, and any host preflight | yes |

Path-ness is declared by the adapter when it builds the invocation (`--cli <path>` is
a path item); transports never infer it from token text.

The transport is chosen by the adapter from the host's documented contract and the
OS. Users do not pass a shell option, and install does not probe for a shell: what
the install-time environment can see is not what the host uses when it runs the hook
(for example, Claude Code's Git Bash discovery and `CLAUDE_CODE_GIT_BASH_PATH`). The
OS is an injectable input so that both branches are tested on every platform. The
preference order is: no shell (exec) > a shell keepsail names explicitly (wrapper) >
host-documented POSIX shell.

## Commitments

1. **model and transports** — add `src/keepsail/adapters/agent/_hook_invocation.py`
   with `HookInvocation` and three transports:
   - `EXEC_ARGV`: handler `{"type": "command", "command": <exe>, "args": [...]}`. No
     quoting, no path rewriting.
   - `POWERSHELL_WRAPPED`: the existing Codex wrapper moved verbatim (forward
     slashes, `'`-doubling), refusing any path containing `"`, `%`, `!`, CR or LF
     (the current refusal set plus the `cmd` expansion characters).
   - `POSIX_SH`: `\`→`/` in the executable and path items, `shlex.quote` on every
     token.

   Every `encode` is checked by its own `decode` (round trip, executable and path
   items compared after `\`→`/`) and raises before anything is written if it fails.
2. **Claude Code uses exec form on every OS**, in both modes and for every hook it
   writes (PreToolUse, SessionStart, Stop, UserPromptSubmit, PostToolUse). On Windows,
   install fails before writing if a resolved executable is not a `.exe`. No
   shell-form fallback is kept.
3. **Claude Code host preflight** — minimum supported Claude Code is **2.1.332** (the
   acceptance target of this change; the version on the owner's machine). Before
   writing hooks, `adapter install claude-code` and `init`'s Claude Code integration
   plan resolve `claude` and parse `claude --version`. If `claude` cannot be found,
   its version cannot be parsed, or it is below 2.1.332, install refuses with a clear
   error stating the minimum version and that an older host would run the gate
   without its arguments; nothing is written. `init` reports this as the existing
   per-integration plan error (`init_plan.py:383`) rather than partially writing.
   The version lookup is injectable for tests. Uninstall performs no version check.
   Documented in `docs/adapters/claude-code.md` and `docs/getting-started.md`,
   including that downgrading Claude Code below the minimum after install is
   unsupported.
4. **Codex transport by OS** — Windows: `POWERSHELL_WRAPPED` in both modes. Other OS:
   `POSIX_SH` in default mode. Codex `--knowledge-context` on a non-Windows OS is
   refused before writing, whether requested explicitly or carried over from an
   existing context install; the error names the `powershell-exit/v1` limitation and
   the existing `--no-knowledge-context` option as the way to install default hooks.
   The Codex minimum version is unchanged: no new Codex field is used.
5. **settings merge takes structured handlers** — `_settings_merge.plan_settings_merge`
   and its entry builders take handler dicts produced by a transport instead of
   command strings. Lock, backup, atomic replace and symlink rules are unchanged.
6. **ownership and mode detection via decode** — whether a handler belongs to
   keepsail, and whether context mode is installed, is decided by decoding it with
   the adapter's transports and matching the executable basename (`keepsail-hook`,
   `keepsail`, with or without `.exe`, with either path separator) and the argument
   signature. For legacy string-form handlers that no transport decodes, the
   fallback requires both that basename on the first token and the current marker
   substring, so existing installs — including the broken one observed on
   2026-11-25 — are recognized, replaced and uninstalled, while a user hook such as
   `othertool change resume` is no longer treated as keepsail's. One detector
   replaces `_context_hook_installed` and `_context_installed`; permission prose and
   user hooks never opt in.
7. **unchanged handlers where nothing is broken** — for the same resolved paths, Codex
   on Windows in `--knowledge-context` mode produces handler objects identical to
   today's (every field, not only `command`), pinned by a test using the exact
   entries in the current `.codex/hooks.json`; therefore no `/hooks` re-trust is
   expected (inference, see host facts). Codex default mode on Windows changes form
   and needs re-trust once; stated in `docs/adapters/codex.md`.
8. **reinstall repairs broken installs** — installing over the exact broken file
   observed on 2026-11-25 replaces all three entries with working handlers and leaves
   no duplicates.
9. **extension contract documented** — `docs/adapters/` gains a short section on how
   a new agent adapter declares its transport, encoder and host preflight. No `dsh`
   or `pi` adapter is implemented here.

## Tests

The full `pytest` suite and `keepsail verify` must pass on the frozen implementation.

- New `tests/unit/adapters/test_hook_invocation.py`: encode/decode round trips for
  each transport on POSIX paths, Windows drive and UNC paths, paths with spaces, `'`,
  `$`, `&`; `POWERSHELL_WRAPPED` refusal of `"`, `%`, `!`, CR, LF; path items vs
  literals; the commitment 7 handler-identity case.
- **Real execution tests** (same file): a stub executable in a directory whose name
  contains a space; assert it receives the exact argv when the handler is executed
  the way the host does — direct spawn for `EXEC_ARGV`, `bash -c` for `POSIX_SH`
  (skipped only when no `bash` is on PATH), `powershell.exe` for `POWERSHELL_WRAPPED`
  on Windows.
- Updated for the structured handler / exec form, with Windows-path cases for every
  hook in both modes and the OS injected both ways:
  `tests/unit/adapters/test_claude_code.py`, `tests/unit/adapters/test_codex.py`,
  `tests/unit/adapters/test_settings_merge.py`, `tests/unit/adapters/test_install.py`,
  `tests/integration/adapter/` (all files), `tests/integration/cli/test_adapter.py`,
  `tests/integration/cli/test_adapter_install.py`,
  `tests/integration/cli/test_keepsail_installation.py`,
  `tests/integration/cli/test_init.py`, `tests/unit/cli/test_init_plan.py`,
  `tests/e2e/test_pre_tool_use_claude_code.py`,
  `tests/e2e/openspec_claude_code/test_full_lifecycle.py`.
- New cases: commitment 3 (below-minimum, missing and unparsable `claude` refuse and
  write nothing; at-minimum installs; init reports the plan error; uninstall needs no
  `claude`); commitment 4 refusals and their `--no-knowledge-context` hint; commitment
  6 legacy recognition including the negative `othertool change resume` case and
  exec-form uninstall; commitment 8 repair.
- `.github/workflows/test.yml`: add `tests/unit/adapters/test_hook_invocation.py`,
  `tests/unit/adapters/test_claude_code.py` and `tests/unit/adapters/test_codex.py`
  to the existing `verification-cross-platform` job (runs on `windows-latest`). No
  other workflow change.

## Boundaries

- Scope: `src/keepsail/adapters/agent/_hook_invocation.py` (new),
  `src/keepsail/adapters/agent/_settings_merge.py`,
  `src/keepsail/adapters/agent/claude_code.py`, `src/keepsail/adapters/agent/codex.py`,
  `src/keepsail/adapters/__init__.py` and `src/keepsail/adapters/install.py` (host
  preflight hook), `src/keepsail/cli/init_plan.py` and `src/keepsail/cli/adapter.py`
  (only to pass the injectable version lookup and surface the refusal), the tests
  above, `.github/workflows/test.yml`, `docs/adapters/claude-code.md`,
  `docs/adapters/codex.md`, `docs/adapters/README.md` (new, commitment 9),
  `docs/getting-started.md`, and this plan.
- Not changed: the gate (`src/keepsail/gates/`) and its allowances; `hook_entry.py`'s
  empty-argv allow rule; review recognition and delivery policy; the
  `powershell-exit/v1` and `claude-bash-output/v1` return transports and their
  evidence. If implementation finds that the Claude Code knowledge-context flow
  depends on its hook being shell-form, stop and submit a new plan candidate.
- `docs/limitations.md` "Windows support — v0.2+" stays: that limitation is about the
  optional observer host's POSIX `os.fork`/`fcntl.flock` (same line), which this
  change does not address; correct hook installation on Windows does not amount to
  Windows support.
- Considered and dropped: Codex `commandWindows`. Hook files are per-machine (they pin
  absolute paths), so one file serving two OSes has no use; choosing the transport by
  OS at install achieves the same, without depending on an override whose minimum
  Codex version is undocumented.
- Not in this change: making Codex `--knowledge-context` work on macOS/Linux (needs a
  new return transport in the knowledge evidence contract); removing the unused
  non-atomic `merge_*_hook` writers in `_settings_merge.py`.

## Product-foundation and decision check

- Foundation 1 (plan approval before implementation): no product code is written
  before this plan is approved by the recognized process.
- Foundation 3 (agent cannot change commitments): the Claude Code minimum version
  (owner in chat on 2026-11-26: no compatibility with older versions; a minimum
  supported version is acceptable) and the Codex non-Windows context refusal
  (proposed by the author; the owner asked to include the Codex cross-OS improvement
  in this change, and this is its reduced form, see "Considered and dropped") are
  stated here as commitments, not left as implementation details. The install-time
  preflight implements that support boundary without changing the runtime
  allow-on-unknown rule.
- `d-gate-governs-git-product`: `.claude/settings.local.json` and `.codex/hooks.json`
  are never hand-edited. After merge the owner regenerates them with
  `keepsail adapter install claude-code` (and `codex` if desired). Whether to reinstall
  Claude Code with `--knowledge-context` is the owner's choice.
- The gate was inactive from 2026-11-22 until reinstall. This is a disclosure fact,
  not a bypass decision; it is recorded here and will be stated in the PR.

## Revision history

- Candidate `plan:46d5bdfd…` (commit `1c015d8`) was rejected by the recognized DSH
  plan review on 2026-11-26 (evidence `dsh-plan-46d5bdfd0443-1c015d8-20261126`).
  Blocking findings: existing tests asserting the string form were not in scope (B1;
  addressed in Tests and Boundaries); the minimum Claude Code version was not
  enforced and an older host could silently disable the gate (B2; commitment 3).
  Non-blocking findings addressed: path items (Design, commitment 1), legacy
  fallback narrowed (commitment 6), whole-handler identity and inference wording
  (commitment 7), `--no-knowledge-context` hint (commitment 4), Windows CI placement
  and injectable OS (Tests, Design), limitations rationale (Boundaries), acceptance
  target wording (commitment 3), `cmd` metacharacters (commitment 1).

## Validation

`keepsail decision check --changed`, `keepsail doc check`, and the full
`keepsail verify` on the frozen implementation. Acceptance on this Windows machine
with Claude Code 2.1.332: reinstall into this workspace, start a new session and
confirm no SessionStart hook error, and confirm the PreToolUse gate blocks a source
`Edit` in a state that forbids it. Codex on Windows: confirm the context-mode
handlers are identical and that default-mode hooks run after `/hooks` trust.
Obtain and import recognized reviews for the exact frozen plan and code subjects.
No merge is authorized by this plan.
