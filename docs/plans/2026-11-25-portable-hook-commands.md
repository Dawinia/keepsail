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

Reproduction (Git Bash on this machine, 2026-11-26):
`bash -c 'E:\Work\keepsail\.venv\Scripts\keepsail.EXE --version'` prints
`bash: line 1: E:Workkeepsail.venvScriptskeepsail.EXE: command not found` (exit 127).

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
  unknown. Hooks fire "wherever it runs: sessions in the terminal, IDE extensions,
  the Desktop app, and cloud sessions"; those surfaces read the same settings file
  but may run a different Claude Code version than the `claude` CLI on PATH.
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
  runtime rule. It refuses install when the `claude` CLI is below the minimum
  (commitment 3); it cannot verify other surfaces, and states that boundary at install
  and in the docs instead of claiming it. The merge gate remains the authoritative
  floor for any edit made while the authoring-time gate was inactive.

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
target OS (injectable, so that both branches are tested on every platform). Users do not pass a shell option, and install does not probe for a shell: what
the install-time environment can see is not what the host uses when it runs the hook
(for example, Claude Code's Git Bash discovery and `CLAUDE_CODE_GIT_BASH_PATH`). The
preference order is: no shell (exec) > a shell keepsail names explicitly (wrapper) >
host-documented POSIX shell.

## Commitments

1. **model and transports** — add `src/keepsail/adapters/agent/_hook_invocation.py`
   with `HookInvocation` and three transports:
   - `EXEC_ARGV`: handler `{"type": "command", "command": <exe>, "args": [...]}`. No
     quoting, no path rewriting.
   - `POWERSHELL_WRAPPED`: the existing Codex wrapper moved verbatim (forward
     slashes, `'`-doubling), refusing any path containing `"`, `%`, `!`, `$`, a
     backtick, CR or LF: the current refusal set plus the characters `cmd` (`%`, `!`)
     or an outer PowerShell (`$`, backtick) could expand inside the double-quoted
     `-Command` argument, since Codex's Windows shell is unknown. `&` and `^` are
     allowed: literal inside double quotes for `cmd` and inside single quotes for
     PowerShell.
   - `POSIX_SH`: `shlex.quote` on every token; `\`→`/` in the executable and path
     items only when the target OS is Windows (on POSIX a backslash is a legal path
     character and is preserved).

   Every `encode` is checked by its own `decode` (exact round trip, with the
   Windows-only separator normalization applied to both sides) and raises before anything is written if it fails.
2. **Claude Code uses exec form on every OS**, in both modes and for every hook it
   writes (PreToolUse, SessionStart, Stop, UserPromptSubmit, PostToolUse). On Windows,
   install fails before writing if a resolved executable is not a `.exe`. No
   shell-form fallback is kept.
3. **Claude Code host preflight and support boundary** — minimum supported Claude Code
   is **2.1.332** (the acceptance target of this change; the version on the owner's
   machine). Before writing hooks, `adapter install claude-code` and `init`'s Claude
   Code integration plan resolve `claude` and run `claude --version` (5-second
   timeout). If `claude` cannot be found, does not answer in time, its version cannot
   be parsed, or it is below 2.1.332, install refuses with a clear error stating the
   minimum version and that an older host would run the gate without its arguments;
   nothing is written. `init` reports this as the existing per-integration plan error
   (`init_plan.py:383`) rather than partially writing; the error and
   `docs/getting-started.md` name the recovery (upgrade Claude Code, or choose other
   integrations with `--integrations`/`--no-agent`). The version lookup is one
   module-level function, injectable for tests. Uninstall performs no version check.
   **Boundary:** the check verifies the `claude` CLI only. A successful install prints
   the verified CLI version and states that every other Claude Code surface using the
   workspace (IDE extension, Desktop, cloud) must also be at least 2.1.332, which
   keepsail does not verify. `docs/adapters/claude-code.md` states the same, and that
   downgrading below the minimum after install is unsupported.
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
   fallback takes the text before the current marker substring, trims whitespace and
   one pair of surrounding `'` or `"`, and requires its Windows-aware basename
   (`ntpath.basename`, which accepts both separators and spaces; no `shlex` parsing)
   to be one of those names; so existing installs — including the broken one observed on
   2026-11-25 — are recognized, replaced and uninstalled, while a user hook such as
   `othertool change resume` is no longer treated as keepsail's. One detector
   replaces `_context_hook_installed` and `_context_installed`; permission prose and
   user hooks never opt in.
7. **unchanged handlers where nothing is broken** — for the same resolved paths, Codex
   on Windows in `--knowledge-context` mode produces handler objects identical to
   today's (the whole entry including `matcher` and `timeout`, not only `command`),
   pinned by a test whose fixture embeds the exact entries of the owner's current
   `.codex/hooks.json` (that file is gitignored, so it is copied into the test, not
   read); therefore no `/hooks` re-trust is
   expected (inference, see host facts). Codex default mode on Windows changes form
   and needs re-trust once; stated in `docs/adapters/codex.md`.
8. **reinstall repairs broken installs** — installing over the exact broken file
   observed on 2026-11-25 replaces all three entries with working handlers and leaves
   no duplicates.
9. **extension contract documented** — `docs/adapters/` gains a short section on how
   a new agent adapter declares its transport, encoder and host preflight, as a
   checklist with how each is tested (round trip, real execution, preflight refusal,
   legacy recognition). No `dsh` or `pi` adapter is implemented here.

## Tests

The full `pytest` suite and `keepsail verify` must pass on the frozen implementation.

**How existing tests keep working.** Two seams, so that tests do not each need to
know about the preflight:

- `tests/conftest.py` gets an autouse fixture that replaces the Claude Code version
  lookup with one returning `2.1.332` for in-process tests. Preflight tests opt out
  with a marker and inject their own lookup. This covers every in-process install
  path, including tests that monkeypatch `shutil.which` for all names (for example
  `tests/integration/cli/test_sync.py:53-57`).
- Tests that run the installed `keepsail` binary in a subprocess
  (`tests/e2e/test_pre_tool_use_claude_code.py`,
  `tests/e2e/openspec_claude_code/test_full_lifecycle.py`) put a fake `claude` that
  prints `2.1.332 (Claude Code)` on PATH for the install step (as the lifecycle test
  already does for `gh`), so the real preflight runs.

Any other existing test that fails only because of the handler shape or the preflight
is updated under commitments 1-3; that is a test adjustment within this approval, not
a scope change.

- New `tests/unit/adapters/test_hook_invocation.py`: encode/decode round trips for
  each transport on POSIX paths, Windows drive and UNC paths, paths with spaces, `'`,
  `&`, `^`, and (POSIX) a backslash that must be preserved; `POWERSHELL_WRAPPED`
  refusal of `"`, `%`, `!`, `$`, backtick, CR, LF; path items vs literals; the
  commitment 7 whole-entry identity case from the embedded fixture.
- **Real execution tests** (same file), using a directory whose name contains a
  space: `EXEC_ARGV` spawns the real `sys.executable` with a stub script in that
  directory as a path item and asserts the exact argv the script receives (no copied
  or compiled `.exe` is needed on Windows); `POSIX_SH` runs the same through
  `bash -c` (skipped only when no `bash` is on PATH); `POWERSHELL_WRAPPED` runs it
  through `powershell.exe` on Windows, and through `cmd /c` as well, since either may
  be Codex's host shell.
- Updated for the structured handler / exec form, with Windows-path cases for every
  hook in both modes and the OS injected both ways:
  `tests/unit/adapters/test_claude_code.py`, `tests/unit/adapters/test_codex.py`,
  `tests/unit/adapters/test_settings_merge.py`, `tests/unit/adapters/test_install.py`,
  `tests/integration/adapter/` (all files), `tests/integration/cli/test_adapter.py`,
  `tests/integration/cli/test_adapter_install.py`,
  `tests/integration/cli/test_keepsail_installation.py`,
  `tests/integration/cli/test_init.py`, `tests/unit/cli/test_init_plan.py`,
  `tests/e2e/test_pre_tool_use_claude_code.py`,
  `tests/e2e/openspec_claude_code/test_full_lifecycle.py`, and
  `tests/integration/cli/test_sync.py` (only if the autouse seam is not enough).
- New cases: commitment 3 (below-minimum, missing, unparsable and timed-out `claude`
  refuse and write nothing; at-minimum installs on a machine with no real `claude`
  via the injected lookup; the success message states the verified CLI version and
  the other-surfaces boundary; init reports the plan error with the recovery hint;
  uninstall needs no `claude`); commitment 4 refusals and their
  `--no-knowledge-context` hint; commitment 6 legacy recognition for (a) the exact
  broken file, (b) a raw executable path containing spaces such as
  `C:\Program Files\keepsail\keepsail-hook.EXE --agent claude-code`, (c) a quoted
  executable path, (d) the negative `othertool change resume` case, and exec-form
  uninstall; commitment 8 repair.
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
  (only to pass the injectable version lookup and surface the refusal),
  `tests/conftest.py`, the tests above, `.github/workflows/test.yml`, `docs/adapters/claude-code.md`,
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
- Candidate `plan:ae5995b7…` (commit `ed4c00d`) was rejected on 2026-11-26 (evidence
  `dsh-plan-ae5995b7c723-ed4c00d-20261126`); it confirmed B1 and B2 resolved. New
  blocking findings: the preflight would break the unlisted
  `tests/integration/cli/test_sync.py` (B3; addressed by the two test seams and the
  general test-adjustment rule in Tests); the first-token legacy fallback missed raw
  paths with spaces or quotes (B4; commitment 6 and its tests); the preflight checks
  only the CLI while the plan claimed all surfaces (B5; commitment 3 boundary, host
  facts, install message, docs). Non-blocking N1-N12 addressed: `$`/backtick refusal
  (commitment 1), fixture source (commitment 7), reproduction (Problem), POSIX
  backslashes (commitment 1), init recovery (commitment 3), `&`/`^` rationale
  (commitment 1), Stop hook acceptance (Validation), Windows exec real-execution
  construction (Tests), preflight timeout (commitment 3), whole-entry identity
  (commitment 7), docs checklist (commitment 9), `which` monkeypatches (Tests).

## Validation

`keepsail decision check --changed`, `keepsail doc check`, and the full
`keepsail verify` on the frozen implementation. Acceptance on this Windows machine
with the Claude Code 2.1.332 CLI in a terminal session (the surface exercised; other
surfaces are not accepted here): reinstall into this workspace, start a new session
and confirm no SessionStart hook error, confirm the PreToolUse gate blocks a source
`Edit` in a state that forbids it, and confirm the Stop hook runs without a hook
error at turn end. Codex on Windows: confirm the context-mode
handlers are identical and that default-mode hooks run after `/hooks` trust.
Obtain and import recognized reviews for the exact frozen plan and code subjects.
No merge is authorized by this plan.
