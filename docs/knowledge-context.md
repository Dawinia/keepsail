# Session-bound Claude Code context

This integration connects existing approval and knowledge records to one harness.
The [product architecture](product-architecture.md) remains normative. Claude
performs the work and semantic reasoning; Keepsail supplies and checks recorded
relationships. [Coverage](product-architecture-coverage.md) distinguishes source,
activation and real-session acceptance.

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
