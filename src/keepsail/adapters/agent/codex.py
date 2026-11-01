"""AgentAdapter for OpenAI Codex CLI (portability axis B).

Registers a PreToolUse hook (deny via stdout `permissionDecision`), a
SessionStart hook (stdout = developer context), and a Stop hook (turn-end
authoring-conformance advisory) into `<repo>/.codex/hooks.json`, reusing the
agent-neutral `_settings_merge`. Codex's hooks.json has the same shape as
Claude's settings.json hooks block; only the matcher + marker differ.

Trust caveat: Codex skips new/changed hooks until a human runs `/hooks` to trust
them — the gate is INACTIVE until then. See design 2026-06-25 §4.3.

API stability: experimental (v0.1).
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from keepsail.adapters import AgentAdapter
from keepsail.adapters.agent import _stop_protocol
from keepsail.adapters.agent._settings_merge import (
    SettingsMergePlan,
    apply_settings_merge_plan,
    plan_settings_merge,
    restore_or_remove_managed_hooks,
)

if TYPE_CHECKING:
    from keepsail.core.authoring_check import Verdict

__all__ = ["CodexAdapter"]

_HOOK_BINARY = "keepsail-hook"
_CLI_BINARY = "keepsail"
_CODEX_MATCHER = "^(apply_patch|Edit|Write)$"
_CODEX_MARKER = "--agent codex"
# Codex-specific Stop marker: merge_stop_hook defaults to the CLAUDE pair
# (`_STOP_OURS_MARKER`), so passing this explicitly is what makes a Codex reinstall
# REPLACE the prior Stop entry instead of appending a duplicate (two objects on stdout
# → Codex "Stop Failed"). Mirrors the PreToolUse `_CODEX_MARKER` pattern.
_CODEX_STOP_MARKER = "--agent codex --event stop"
_CONTEXT_MARKERS = {event: f"--agent codex --event {name}" for event, name in (
    ("SessionStart", "session-start"), ("UserPromptSubmit", "user-prompt-submit"),
    ("PostToolUse", "post-tool-use"),
)}


def _context_installed(raw: bytes | None) -> bool:
    for group in json.loads(raw or b"{}").get("hooks", {}).get("SessionStart", []):
        for hook in group.get("hooks", []) if isinstance(group, dict) else []:
            command = hook.get("command", "") if isinstance(hook, dict) else ""
            if not isinstance(command, str) or _CONTEXT_MARKERS["SessionStart"] not in command:
                continue
            tokens = shlex.split(command)
            if tokens[:4] != ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"]:
                continue
            inner = shlex.split(tokens[4]) if len(tokens) == 5 else []
            if (len(inner) == 9 and inner[0] == "&"
                    and Path(inner[1]).name.lower() in {"keepsail-hook", "keepsail-hook.exe"}
                    and inner[2:8] == ["--agent", "codex", "--event", "session-start",
                                       "--context", "--cli"]):
                return True
    return False

_AGENTS_MD_BEGIN = "<!-- keepsail agent: codex -->"
_AGENTS_MD_END = "<!-- /keepsail agent: codex -->"
_AGENTS_MD_SUBSECTION = f"""{_AGENTS_MD_BEGIN}
### keepsail (Codex)

A **PreToolUse** hook gates this workspace. `apply_patch` edits are blocked by
keepsail when the current change state forbids the mutation (deterministic
gate enforcement). `Bash` is never gated (see the coverage caveat below).

**REQUIRED trust step:** after `adapter install codex`, the gate is INACTIVE
until you run `/hooks` in Codex and trust the keepsail hook. Codex skips
new/changed hooks until trusted (trust is keyed to the hook's hash); if you
reinstall or relocate the binary, re-trust it. On a pre-existing repo also run
`keepsail sync --gitignore` so `.codex/hooks.json` is ignored.

**Coverage caveat:** keepsail selects `apply_patch` edits for this adapter's gate.
It does not gate arbitrary shell, MCP or other local writes. Current host hook
capability and keepsail's selected coverage are separate; CI/check evidence also
has its own scope and does not prove every action was observed. Hosted WebSearch
is outside this integration's observation boundary.

**Authoring-space caveat:** keepsail also allows the change's plan document in
`INTENT_DECLARED` (any path matching `.harness/plan-paths.yaml`) and scratch notes in
`.harness/scratch/<slug>/` in every state — but both key off the edited file's path,
and the legacy Codex shim passes no resolved file path. In that legacy mode those
carve-outs cannot fire. The optional context mode parses all native patch paths
and applies the same lawful allowances to each path; it requires a bound task.

#### Optional session-bound context (Windows local desktop)

When installed with `adapter install codex --knowledge-context`, follow the real
SessionStart hint: bind its startup once to the task's explicit Change and retrieve
every returned context command before product edits. New resume/compact entries
require fresh retrieval. Declare adoption or challenge explicitly. Never borrow a
root entry for an unverified subagent. See [context delivery](docs/knowledge-context.md)
for current transport limits, declarations, refresh and native opt-out.

When a tool call is blocked:
- Run `keepsail status` to see the change, its state, and the next step.
- Resume context with `keepsail change resume <change_id>`.
- If the gate blocks a tool call, stop and surface the block plus the next valid
  step (`keepsail status`) to the human. Do **not** try to disable or work
  around the gate yourself — overriding it is a **human-only** decision, and any
  bypass is recorded and disclosed at the merge gate. Whether to override is the
  human's call.

#### Review protocol

keepsail does NOT start, spawn, or host reviewers. It records the exact
conclusion from an external or human process. The active recognition contract is
`.harness/review-recognition.yaml`; `.harness/review-governance.yaml` and the
gitignored `.harness/review-profiles.local.yaml` are historical data and do not
select a reviewer or explicit model.

For each review epoch:

1. Commit the exact in-scope change and preserve the complete plan/code subject.
2. Obtain a conclusion from the owner-recognized external process. The conclusion
   must identify the current subject, explicit decision, provenance, and retained
   original evidence; the core does not infer approval from a model, failed call,
   empty result, or skip.
3. Import that exact record with `keepsail review import <change>
   --evidence -` using JSON on stdin (or a workspace file). Review execution,
   retries, and judgment stay outside keepsail.
4. Batch code-only fixes after `implementation reopen <change> --reason "<why>"`;
   if approved commitments change or explicit restrictions are relaxed, require a
   new plan candidate and review. Within-approval file additions and implementation
   adjustments update assessment/coverage with `implementation record` instead.
   A skipped review is disclosure, not approval.

The imported evidence must cover the exact frozen subject. A reviewer may read
unchanged repository material as supporting context, but a finding never widens
the target implicitly. Do not edit while an external review is pending.

Use stdin for review/assessment/knowledge/entry-statement JSON. Import the necessary
facts once; temporary input files and copied tool returns are not deliverables.
For implementation record, omit coverage to enumerate the full Git/workspace diff;
git add intended new files or name --include-path. Supply the semantic reasons and
commitment links explicitly. See docs/knowledge.md for the input and export formats.

#### Turn-end authoring check

A **Stop** hook runs a turn-end authoring-time conformance check: when you finish a
turn, any ratified decision that opted in (`authoring_time: true`) has its check run
once; a failure is fed back as a non-blocking advisory so you self-correct next turn.
Like the PreToolUse gate, the Stop hook is INACTIVE until you `/hooks`-trust it.
{_AGENTS_MD_END}"""


class CodexAdapter(AgentAdapter):
    def __init__(self, knowledge_context: bool | None = None) -> None:
        self.knowledge_context = knowledge_context
    name: ClassVar[str] = "codex"
    version: ClassVar[str] = "0.1.0"
    capabilities: ClassVar[dict[str, bool]] = {
        "pre_tool_use_hook": True,
        "post_tool_use_hook": True,  # spike-verified: fires under `codex exec` (2026-07-01)
        "session_start_hook": True,
        "session_end_hook": False,
        "pre_commit_hook": False,
        "rules_file_injection": True,
        "mcp_server": True,
        "subprocess_execution": True,
        "turn_end_feedback_hook": True,  # Codex Stop hook (cut-2)
    }

    def detect(self, workspace: Path) -> bool:
        return (workspace / ".codex").is_dir()

    def install_hooks(self, workspace: Path) -> None:
        resolved_hook = shutil.which(_HOOK_BINARY)
        if resolved_hook is None:
            raise RuntimeError(
                f"{_HOOK_BINARY} not found on PATH; reinstall keepsail "
                f"(e.g. `pipx reinstall keepsail`) before installing the "
                f"Codex adapter."
            )
        resolved_cli = shutil.which(_CLI_BINARY)
        if resolved_cli is None:
            raise RuntimeError(
                f"{_CLI_BINARY} not found on PATH; reinstall keepsail "
                f"(e.g. `pipx reinstall keepsail`) before installing the "
                f"Codex adapter."
            )

        plan = self.plan_hook_install(
            workspace, hook_executable=resolved_hook, cli_executable=resolved_cli
        )
        assert plan is not None
        apply_settings_merge_plan(plan)

    def plan_hook_install(
        self, workspace: Path, *, hook_executable: str, cli_executable: str
    ) -> SettingsMergePlan:
        legacy = plan_settings_merge(
            workspace / ".codex" / "hooks.json",
            workspace_root=workspace,
            pre_tool_use_command=f"{hook_executable} --agent codex",
            session_start_command=f"{cli_executable} change resume",
            stop_command=f"{hook_executable} --agent codex --event stop",
            pre_tool_use_matcher=_CODEX_MATCHER,
            pre_tool_use_marker=_CODEX_MARKER,
            stop_marker=_CODEX_STOP_MARKER,
        )
        enabled = self.knowledge_context
        if enabled is None:
            enabled = _context_installed(legacy.original_bytes)
        if not enabled and self.knowledge_context is not False:
            return legacy

        def command(arguments: str) -> str:
            hook, cli = (p.replace("\\", "/") for p in (hook_executable, cli_executable))
            if any('"' in p or "\n" in p or "\r" in p for p in (hook, cli)):
                raise ValueError("unsupported quote/newline in Codex hook executable path")
            invocation = "& '" + hook.replace("'", "''") + "' --agent codex " + arguments
            if "--event session-start" in arguments:
                invocation += " --cli '" + cli.replace("'", "''") + "'"
            return 'powershell.exe -NoProfile -NonInteractive -Command "' + invocation + '"'

        return plan_settings_merge(
            workspace / ".codex/hooks.json", workspace_root=workspace,
            pre_tool_use_command=command("--context") if enabled else (
                f"{hook_executable} --agent codex"),
            session_start_command=command("--event session-start --context") if enabled else (
                f"{cli_executable} change resume"),
            stop_command=command("--event stop") if enabled else (
                f"{hook_executable} --agent codex --event stop"),
            pre_tool_use_matcher=_CODEX_MATCHER, pre_tool_use_marker=_CODEX_MARKER,
            stop_marker=_CODEX_STOP_MARKER, context_markers=_CONTEXT_MARKERS,
            context_commands={
                "UserPromptSubmit": command("--event user-prompt-submit --context"),
                "PostToolUse": command("--event post-tool-use --context"),
            } if enabled else {},
        )

    def inject_context(self, change_id: str) -> str:
        result = subprocess.run(
            [_CLI_BINARY, "change", "resume", change_id],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout or ""

    def stop_should_check(self, payload: dict[str, Any]) -> bool:
        """Skip the continuation turn a prior block created (loop-safety). Codex's Stop
        payload carries `stop_hook_active`, spiked identical to Claude Code's."""
        return not _stop_protocol.is_continuation(payload)

    def format_stop_feedback(self, verdict: Verdict) -> str:
        """Codex Stop feedback = the shared Claude-Code-hook family envelope
        (`{"decision":"block","reason": ...}`). Spike-verified under `codex exec`:
        `reason` is the ONLY channel that reaches the model; adding systemMessage /
        additionalContext makes Codex report "Stop Failed" and drop the continuation."""
        return _stop_protocol.block_feedback(verdict)

    def agents_md_subsection(self) -> str:
        return _AGENTS_MD_SUBSECTION

    def local_config_relpath(self) -> str:
        return ".codex/hooks.json"

    def installed_detail(self) -> str:
        if self.knowledge_context is True:
            return ("Codex session-bound context hooks registered in .codex/hooks.json; "
                    "review and trust the exact hooks in the current Codex desktop before use")
        return (
            "PreToolUse + SessionStart + Stop hooks registered in .codex/hooks.json — "
            "run `/hooks` in Codex to trust the hooks before the gate is active"
        )

    def on_uninstall(self, workspace: Path) -> None:
        hooks_path = workspace / ".codex" / "hooks.json"
        restore_or_remove_managed_hooks(
            hooks_path,
            pre_tool_use_marker=_CODEX_MARKER,
            stop_marker=_CODEX_STOP_MARKER,
            workspace_root=workspace,
            context_events=(_context_installed(hooks_path.read_bytes())
                            if hooks_path.exists() else False),
            context_markers=_CONTEXT_MARKERS,
        )
