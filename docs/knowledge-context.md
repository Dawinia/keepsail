# Session-bound knowledge context

This integration connects existing approval and knowledge records to one harness.
The [product architecture](product-architecture.md) remains normative. The executor
performs the work and semantic reasoning; Keepsail supplies and checks recorded
relationships. [Coverage](product-architecture-coverage.md) distinguishes source,
activation and real-session acceptance.

## Selected entry: Windows Codex desktop revision

The confirmed revision selects the current **local Codex desktop** for real
acceptance. The earlier Claude candidate remains historical source/test evidence;
Claude A/B acceptance did not occur. This is one selected integration effort, not
a new cross-harness framework. The PATH CLI can differ from the desktop's bundled
runtime; the audited versions were 0.46.0 and 0.164.0-alpha.11.1 respectively.

```console
keepsail adapter install codex --knowledge-context
```

Review and trust the exact new hooks using the current host's hook review UI.
Installation does not trust or prove activation. Keep the pinned repository `.venv`
CLI/hook executables. This Windows transport uses PowerShell; arbitrary platform
or cloud orchestration compatibility is not claimed.

SessionStart retains only required callback identity and issues an unbound startup
hint. In a task explicitly identifying the Change, run its command with that slug:

```console
keepsail --json change context your-change --bind-startup STARTUP_FROM_ACTUAL_HINT
```

Use the **full exact command from the hint**, including pinned paths and transport
settings; the short example only names the interface. Bind once; another Change
requires another startup. No environment variable from a separate terminal is
assumed to reach an already-running desktop. Retrieve every `next_command` and
then use the explicit declaration schema below. No automatic latest-Change choice
or adoption is performed.

The final page's `next_command` runs `--finalize-acquisition` outside the fixed
10-second hook budget. The hook first retains and validates the actual complete
returns; the CLI reconstructs them and performs the slower native per-version
writes. Missing pages, stale authority or another entry cannot be acknowledged.
Until those writes succeed, prompts keep the finalization command and selected
edits remain unready. Retry uses native operation identity/CAS and does not reread
unchanged pages or duplicate observations. No background worker is introduced.
An empty set retains outer receipt evidence without inventing a native version.

Current approval context also supplies referenced prior frozen approvals, preserving
unreplaced restrictions. The current adopted revision defines precedence; retaining
an old body does not reinstate an explicitly replaced harness target.

Codex observations preserve the raw native callback and its root turn identity.
The current candidate decoder accepts an explicit completed `output`/`exit_code`
object; an unknown, running, truncated or failed native shape remains unobserved.
This wire contract still requires actual desktop acceptance. Callback fixtures and
PowerShell process tests cannot establish that the host delivered this shape.
UserPromptSubmit records root turn identity without collecting prompt content;
unverified subagent/other-turn callbacks cannot use that entry. Actual attribution
is an acceptance requirement, not a cryptographic identity guarantee.
An automatic compact may continue the same observed root turn without another
prompt. Its actual startup callback retains the prior attribution reference;
only root-turn continuity carries forward, while the new entry still reacquires
every page and version. Old turn/entry records remain immutable.

The selected edit gate extracts all add/update/delete/move paths from a native
patch. Every path uses the same current context and pure lifecycle gate. An entire
patch waits if any dependent edit waits; another proven-independent patch may
continue. Malformed/unknown paths cannot become independent by omission. CLI
diagnostics use the same complete-action seam:

```console
keepsail --json gate check pre-tool-use --agent codex --session-id SESSION --turn-id TURN --change-id your-change --patch-file candidate.patch
keepsail adapter install codex --no-knowledge-context
```

Native opt-out withdraws this context boundary, retains history and restores the
legacy adapter hooks while preserving unrelated settings. Hook trust/timeout/skip
behavior, actual A/B development and separately recognized Codex v1/v2 evolution
remain pending until retained real evidence says otherwise. The separately
recognized Claude knowledge is delivered with its original conditional body;
it is not silently rewritten into Codex authority.

The [official hook contract](https://learn.chatgpt.com/docs/hooks) informs this
adapter. Test actual callback connectivity and failure behavior before claiming
protection. Raw complete-return acquisition remains separate from executor
declarations, native checks and substantive code review.

## Earlier Claude candidate

## Install and select the task

Use the intended Keepsail environment on PATH, then opt in explicitly:

```console
keepsail adapter install claude-code --knowledge-context
```

Installation pins absolute CLI/hook paths in the local settings transaction. It
adds SessionStart, UserPromptSubmit and PostToolUse context handling while retaining
the editor gate and Stop check. Unrelated settings/hooks are preserved. Default
installations and Codex retain their existing contracts; reinstallation without
either flag preserves the selected mode.

Set `KEEPSAIL_CHANGE_ID` to the intended existing Change before starting Claude:

```powershell
$env:KEEPSAIL_CHANGE_ID = 'your-change'
claude
```

Use a valid project Git Bash installation on Windows and complete the host's project
trust requirements yourself. Registration, installation and an actual host callback
are separate facts. Keepsail does not open user sessions.

## Start, continue and recover

SessionStart supplies a small hint with an entry identity and an exact Bash command.
Run it unchanged, then retrieve every `next_page` of that manifest before product
edits. Each response is bounded to 24 KiB of actual UTF-8 CLI output; the hint is
bounded to 8 KiB. Token counts are labelled heuristics, not measured model usage.
Full context contains Change/state, effective approval with frozen commitment and
restriction text, ratified decision identities/body hashes/text, applicable
knowledge versions/bodies/recognition, historical grounds, pending revisions,
impacts/challenges, recognized dispositions and explicit missing observations.

Recovery never guesses the most recently active historical Change as task identity.
Startup/resume/clear/compact create a fresh epoch even if the session ID is unchanged.
History remains available; this epoch retrieves current authority again.
UserPromptSubmit announces authority changes without reinjecting all history. The
editor gate rechecks before the action, including changes within the same turn.
Until complete tool returns are observed, prompts repeat the bounded retrieval
hint: a printed SessionStart hint alone cannot justify suppressing recovery help.

Supply uses native `knowledge deliver`. Replay reuses its original request/CAS
revision. Changed authority requires page 1 of a new manifest; observer/declaration
appends alone do not invalidate it. Repeated historical supplies are grouped by
version and approval epoch in the operational projection. `knowledge show` retains
every original delivery/context and the complete unabridged trace.

Approval/convention/empty-set declarations retain their original entry and manifest
in the context trace, including after session replacement or compaction. Reported
challenges with no linked recognized conclusion remain labelled unresolved in
that carrier; the label does not confer authority or globally block independent
work. A later declaration cannot erase the original fact or substitute for a
recognized disposition. Native knowledge trace remains available through
`knowledge show`; outer declarations retain their operation-log locators.

## Four separate facts

| Fact | Evidence and limit |
|---|---|
| Prepared supply | Native delivery and manifest; printing a hint is not acquisition. |
| Observable acquisition | Actual Claude Bash PostToolUse callback, exact pinned CLI invocation, correct session/entry/root, complete returned pages and matching digests. |
| Executor declaration | Explicit adopt/reject/challenge, target, actor and reason; never inferred from retrieval. |
| Check result | Actual check/review evidence with its own coverage. Retrieval/declarations do not prove understanding or compliance. |

Altered, missing, background, interrupted, persisted/truncated or mismatched returns
cannot become complete acquisition. The observer reconstructs returned text and
computes version-body hashes from that text. Partial pages are not whole-version
acquisition. An empty set has an outer context receipt, not an invented knowledge
version or native acquisition row. The policy must recognize `keepsail-cli-observer`;
this is local observer trust, not cryptographic authentication or private reasoning.

An explicit declaration file has this shape, using IDs from the returned packet:

```json
{
  "schema_version": "entry-statement/v1",
  "entry_id": "ENTRY_FROM_SESSIONSTART",
  "manifest_id": "MANIFEST_FROM_RETRIEVAL",
  "actor": "executor-identity",
  "decision": "adopt",
  "reason": "How this context applies to the approved work",
  "knowledge_versions": ["EXACT_SUPPLIED_VERSION_DIGEST"],
  "project_context": true
}
```

```console
keepsail --json change context your-change --entry ENTRY --statement declaration.json
```

For an empty set, use an empty version list and explicit project context. Outer
context declarations do not grant authority; knowledge declarations also use native
records. A challenge declares dependent paths or `dependency: global` and does not
release the constraint or commitment.

## Blocking, independent work and diagnostics

The selected editor gate separately evaluates exact current supply, this epoch's
complete returns, local knowledge dependence and original lifecycle authority.
Unknown/global dependence stays unresolved; a path-dependent challenge can wait
while an independent approved action continues. Existing legitimate plan/scratch
authoring remains available. Missing/corrupt selected context cannot become ready.
Reads and diagnostic commands remain usable.

An action outside estimated scope can expose another explicit constraint. Record
that path through an approval-bound implementation assessment, then refresh. An
in-bound file addition does not itself require plan approval again. Changed
commitments/restrictions still require the recognized plan process.

```console
keepsail --json change context your-change --preview
keepsail --json gate check pre-tool-use --agent claude-code --session-id SESSION --change-id your-change --tool Edit --file src/example.py
```

Preview is read-only and explicitly not supplied/not observed. The gate query uses
the hook's same current inputs and pure gate. It is an action-bound mechanical
result, not proof of semantic commitment compliance. `knowledge check --paths`
alone still does not establish full supply.

Content-addressed manifests/pages, required raw callbacks, rejected attempts and
outer declarations use the existing ignored operation-log area. They are not
approval/knowledge authority. Lost/corrupt required receipts require reacquisition,
normally a fresh SessionStart epoch. Full prompts, credentials and unrelated Bash
output are not collected. Native observations retain self-contained original
receipts; acceptance exports bind them to identity, hashes and actual check subjects.

## Opt out and acceptance boundaries

```console
keepsail adapter install claude-code --no-knowledge-context
```

Opt-out removes managed context callbacks and restores legacy resume, preserving
unrelated current settings. History remains. Context-mode full adapter uninstall
restores managed entries while retaining unrelated settings added after installation.
Removal withdraws the new entry preconditions and must be disclosed.

Real acceptance requires actual development, actual Claude A/B sessions, new-epoch
retrieval and separately recognized v1/v2 evolution/disposition. Process fixtures,
configuration and executor self-report cannot replace that evidence. This does not
intercept arbitrary Bash/MCP/external writes, own the agent loop, guarantee semantic
recall or implement shared cross-repository authority/distribution. Verification,
exact external review and pure-Git attestation retain separate floors.

The process can translate its own selected-edit failures into a deny response.
It cannot control hooks the host skips, kills or times out; the existing 10-second
hook budgets remain. Actual activation and latency must therefore be observed,
and absent callbacks cannot be reported as successful checks or acquisition.
