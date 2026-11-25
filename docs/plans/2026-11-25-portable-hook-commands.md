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
`tests/unit/adapters/test_claude_code.py:30-37`), so the macOS/Linux CI matrix could
not see it. Mode detection (`_context_hook_installed`, `_context_installed`) and hook
ownership (`_settings_merge._command_contains` substring markers) each re-interpret
command strings with their own rules.

The underlying design fault: a hook is modelled as a shell string, so correctness
depends on guessing which shell the host will use.

## Host facts this plan relies on

- **Claude Code** (https://code.claude.com/docs/en/hooks, read 2026-11-26): a command
  hook's `command` string runs under `sh -c` on macOS/Linux and Git Bash on Windows,
  or PowerShell when Git Bash is not installed. When `args` is present ("exec form"),
  Claude Code "spawns it directly with `args` as the argument vector. There is no
  shell"; on Windows `command` must be a real executable such as a `.exe`. `timeout`
  is a common field. The version that introduced `args` is not stated in the docs or
  in the visible changelog.
- **Codex** (https://learn.chatgpt.com/docs/hooks and the config reference, read
  2026-11-26): `command` is a string; the docs do not state how it is executed on any
  platform and document no argv form. A Windows-only `commandWindows` override exists.
  Codex's hook shell on Windows is therefore unknown; the PowerShell wrapper above is
  proven on this machine's Codex desktop and is valid whether the string reaches
  `cmd` or PowerShell. On macOS/Linux the documented examples use `$(...)`, which
  implies a POSIX shell (inference, not a documented fact).
- The Codex knowledge-context retrieval protocol is pinned to the
  `powershell-exit/v1` return transport (`src/keepsail/core/knowledge.py:38`), used
  by `core/context.py` and `daemon/codex_context_hook.py`.

## Design

Three layers, so that adding a host later (for example DeepSeek Harness `dsh` or
`pi`) means writing one encoder and choosing a transport, without touching other
adapters:

| Layer | Owns | Agent-specific? |
|---|---|---|
| `HookInvocation` | what to run: event, executable path, argument list (structured, never a shell string) | no |
| `HookTransport` | how a host executes it: `encode(invocation) -> handler fields`, `decode(handler) -> HookInvocation or None` | no; reusable, chosen per host |
| adapter encoder | where and in what file format the handler is persisted | yes |

The transport is chosen by the adapter from the host's documented contract and
`os.name` only. Users do not pass a shell option, and install does not probe for a
shell: what the install-time environment can see is not what the host uses when it
runs the hook (for example, Claude Code's Git Bash discovery and
`CLAUDE_CODE_GIT_BASH_PATH`). The preference order is: no shell (exec) > a shell
keepsail names explicitly (wrapper) > host-documented POSIX shell.

## Commitments

1. **model and transports** — add `src/keepsail/adapters/agent/_hook_invocation.py`
   with `HookInvocation` and three transports:
   - `EXEC_ARGV`: handler `{"type": "command", "command": <exe>, "args": [...]}`. No
     quoting, no path rewriting.
   - `POWERSHELL_WRAPPED`: the existing Codex wrapper moved verbatim (forward
     slashes, `'`-doubling, refusal of `"`/CR/LF in paths).
   - `POSIX_SH`: `\`→`/` in the executable and path-valued arguments, `shlex.quote` on
     every token.

   Every `encode` is checked by its own `decode` (round trip, executable compared
   after `\`→`/`) and raises before anything is written if it fails.
2. **Claude Code uses exec form on every OS**, in both modes and for every hook it
   writes (PreToolUse, SessionStart, Stop, UserPromptSubmit, PostToolUse). On Windows,
   install fails before writing if a resolved executable is not a `.exe`. Minimum
   supported Claude Code version: **2.1.332**, the version validated by this change;
   older versions are not supported and no shell-form fallback is kept. Documented in
   `docs/adapters/claude-code.md` and `docs/getting-started.md`.
3. **Codex transport by OS** — Windows: `POWERSHELL_WRAPPED` in both modes. Other OS:
   `POSIX_SH` in default mode. Codex `--knowledge-context` on a non-Windows OS is
   refused by install with a clear error naming the `powershell-exit/v1` limitation,
   before anything is written, instead of writing hooks that cannot run. The Codex
   minimum version is unchanged: no new Codex field is used.
4. **settings merge takes structured handlers** — `_settings_merge.plan_settings_merge`
   and its entry builders take handler dicts produced by a transport instead of
   command strings. Lock, backup, atomic replace and symlink rules are unchanged.
5. **ownership and mode detection via decode** — whether a handler belongs to
   keepsail, and whether context mode is installed, is decided by decoding it with
   the adapter's transports and matching the executable basename (`keepsail-hook`,
   `keepsail`, with or without `.exe`) and the argument signature. The current
   substring markers remain only as a legacy fallback on string-form handlers, so
   existing installs — including the broken one observed on 2026-11-25 — are still
   recognized, replaced and uninstalled. One detector replaces
   `_context_hook_installed` and `_context_installed`; permission prose and user hooks
   still never opt in.
6. **unchanged bytes where nothing is broken** — for the same resolved paths, Codex on
   Windows in `--knowledge-context` mode produces byte-identical commands to today
   (pinned by a test using the exact strings in the current `.codex/hooks.json`), so
   no `/hooks` re-trust and no change to its retained evidence. Codex default mode on
   Windows changes form and needs re-trust once; stated in `docs/adapters/codex.md`.
7. **reinstall repairs broken installs** — installing over the exact broken file
   observed on 2026-11-25 replaces all three entries with working handlers and leaves
   no duplicates.
8. **extension contract documented** — `docs/adapters/` gains a short section on how
   a new agent adapter declares its transport and encoder. No `dsh` or `pi` adapter is
   implemented here.

## Tests

- `tests/unit/adapters/test_hook_invocation.py` (new): encode/decode round trips for
  each transport on POSIX paths, Windows drive and UNC paths, paths with spaces, `'`
  and `$`; refusal cases; the commitment 6 byte-identity case.
- **Real execution tests**: a stub executable in a directory whose name contains a
  space; assert it receives the exact argv when the handler is executed the way the
  host does — direct spawn for `EXEC_ARGV`, `bash -c` for `POSIX_SH` (skipped only
  when no `bash` is on PATH), `powershell.exe` for `POWERSHELL_WRAPPED` on Windows.
- `tests/unit/adapters/test_claude_code.py`, `tests/unit/adapters/test_codex.py`,
  `tests/unit/adapters/test_settings_merge.py`, `tests/integration/adapter/` tests:
  expected handlers come from the transports; Windows-path cases for every hook in
  both modes; ownership/uninstall of exec-form handlers; legacy string handlers still
  replaced; the commitment 3 refusal; the commitment 7 repair.
- Add `tests/unit/adapters/test_hook_invocation.py` to the existing
  `verification-cross-platform` job in `.github/workflows/test.yml` (already runs on
  `windows-latest`). No other workflow change.

## Boundaries

- Scope: `src/keepsail/adapters/agent/_hook_invocation.py` (new),
  `src/keepsail/adapters/agent/_settings_merge.py`,
  `src/keepsail/adapters/agent/claude_code.py`, `src/keepsail/adapters/agent/codex.py`,
  `src/keepsail/adapters/__init__.py` (only if the base class needs the transport
  hook), the tests above, `.github/workflows/test.yml`, `docs/adapters/claude-code.md`,
  `docs/adapters/codex.md`, `docs/getting-started.md`, and this plan.
- Not changed: the gate (`src/keepsail/gates/`) and its allowances; review recognition
  and delivery policy; the `powershell-exit/v1` and `claude-bash-output/v1` return
  transports and their evidence; `docs/limitations.md`'s "Windows support — v0.2+".
  If implementation finds that the Claude Code knowledge-context flow depends on its
  hook being shell-form, stop and submit a new plan candidate.
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
  stated here as commitments, not left as implementation details.
- `d-gate-governs-git-product`: `.claude/settings.local.json` and `.codex/hooks.json`
  are never hand-edited. After merge the owner regenerates them with
  `keepsail adapter install claude-code` (and `codex` if desired). Whether to reinstall
  Claude Code with `--knowledge-context` is the owner's choice.
- The gate was inactive from 2026-11-22 until reinstall. This is a disclosure fact,
  not a bypass decision; it is recorded here and will be stated in the PR.

## Validation

`keepsail decision check --changed`, `keepsail doc check`, and the full
`keepsail verify` on the frozen implementation. Acceptance on this Windows machine
with Claude Code 2.1.332: reinstall into this workspace, start a new session and
confirm no SessionStart hook error, and confirm the PreToolUse gate blocks a source
`Edit` in a state that forbids it. Codex on Windows: confirm the context-mode
commands are byte-identical and that default-mode hooks run after `/hooks` trust.
Obtain and import recognized reviews for the exact frozen plan and code subjects.
No merge is authorized by this plan.
