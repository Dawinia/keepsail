# Adapters

Framework adapters ([OpenSpec](openspec.md), [plain](plain.md)) tell keepsail where
a change's spec and plan artifacts live. Agent adapters ([Claude Code](claude-code.md),
[Codex](codex.md)) install keepsail's hooks into a coding agent's own configuration.

## Adding an agent adapter

A hook is never modelled as a shell string. Shell strings made correctness depend
on which shell the host happened to use: raw Windows paths broke under Git Bash,
and paths with spaces broke everywhere. An agent adapter instead declares three
things, each with a matching test.

### 1. Invocations

Build each hook as a `HookInvocation`
(`src/keepsail/adapters/agent/_hook_invocation.py`): the absolute executable
(resolved at install time) and an argument list in which every item is explicitly
`lit(...)` or `path(...)`. Path-ness is declared here, never inferred from text.

*Test:* the planned settings contain one entry per hook event with the expected
executable and arguments, for both values of the target OS.

### 2. Transport

Choose a transport from the host's documented contract, preferring in this order:

| Transport | Use when | Notes |
|---|---|---|
| `ExecArgv` | the host spawns `command` + `args` with no shell | no quoting at all; Claude Code |
| `PowerShellWrapped` | Windows host whose shell is undocumented | keepsail names the interpreter; Codex on Windows |
| `PosixSh` | the host documents a POSIX shell | `windows_target=True` forward-slashes paths |

Select by the host's contract and the target OS only. Do not ask the user for a
shell and do not probe for one at install time: the install environment is not
the environment the host runs hooks in. Keep the target OS injectable
(`target_os`) so both branches are tested on every platform. A new host with a
different execution model gets a new transport implementing `encode` / `decode`.

*Test:* `encode` → `decode` round trips (every `encode` already checks itself and
raises before writing); a real-execution test runs the handler the way the host
does, against a stub in a directory whose name contains a space.

### 3. Encoder, ownership and host preflight

- **Encoder** — write the transport's handler fields into the host's configuration
  format. For JSON hook files shaped like Claude Code's, pass `ManagedHook`
  entries and an ownership predicate to `plan_settings_merge`; other formats
  (for example a plugin configuration) need their own encoder.
- **Ownership** — build the predicate with `owner_predicate(...)`: structured
  handlers are recognized by decoding them; older string handlers by a
  `keepsail`/`keepsail-hook` executable before a keepsail marker. User hooks must
  never match.
- **Host preflight** — if the chosen transport needs a minimum host version,
  override `AgentAdapter.preflight_host` to refuse before any write, with the
  recovery in the message, and state what cannot be verified.

*Test:* reinstall over an older install replaces entries without duplicates; a
user hook with a similar command survives install and uninstall; the preflight
refuses below the minimum and writes nothing.
