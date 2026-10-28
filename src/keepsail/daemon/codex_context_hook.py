"""Codex-specific actual startup and tool-return boundary; no agent runtime."""
import json
import sys
from pathlib import Path
from typing import Any

from keepsail.core.approval import digest_record, load_json_record
from keepsail.core.context import (
    callback_matches_workspace,
    capture_codex_startup,
    codex_root_turn,
    context_invocation,
    context_path,
    entry_command,
    observed_pages,
    project_context,
    read_manifest,
    save_codex_root_turn,
    save_context_record,
    session_entry,
    validate_return,
)
from keepsail.core.file_lock import exclusive_file_lock
from keepsail.core.knowledge import KnowledgeError


def start_session(root: Path, payload: dict[str, Any], *, cli_executable: str) -> dict[str, Any]:
    return capture_codex_startup(root, payload, cli_executable)


def record_prompt(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    session, turn = payload.get("session_id"), payload.get("turn_id")
    if (payload.get("hook_event_name") != "UserPromptSubmit" or payload.get("agent_id")
            or not callback_matches_workspace(root, payload.get("cwd"))
            or not isinstance(session, str) or not session
            or not isinstance(turn, str) or not turn):
        raise KnowledgeError("root prompt identity unavailable")
    with exclusive_file_lock(context_path(root, "sessions", digest_record(session) + ".lock")):
        pointer = load_json_record(context_path(root, "sessions", digest_record(session) + ".json"))
        startup = pointer.get("startup_id", pointer.get("entry_id"))
        if not isinstance(startup, str):
            raise KnowledgeError("root prompt startup unavailable")
        original = load_json_record(context_path(root, "startups", startup + ".json"))
        if (original.get("session_id") != session
                or original.get("root") != root.resolve().as_posix()):
            raise KnowledgeError("root prompt startup identity mismatch")
        value = {"session_id": session, "turn_id": turn, "startup_id": startup,
                 "attribution": "user-prompt", "callback": {k: payload[k] for k in (
                     "hook_event_name", "session_id", "turn_id", "cwd",
                 )}}
        save_codex_root_turn(root, value)
    return value


def observe_return(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    from keepsail.daemon.context_hook import observe_return as observe

    entry = session_entry(root, payload.get("session_id", ""))
    if entry.get("harness") != "codex":
        raise KnowledgeError("Codex session entry unavailable")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict) or not context_invocation(entry, tool_input.get("command")):
        return {"ignored": True}
    try:
        codex_root_turn(root, entry["entry_id"], payload)
    except (ValueError, KeyError, OSError) as exc:
        receipt = {k: payload[k] for k in ("hook_event_name", "session_id", "turn_id", "cwd",
                   "tool_name", "tool_use_id", "tool_input", "tool_response", "agent_id")
                   if k in payload}
        save_context_record(root, (entry["entry_id"], "rejected", digest_record(receipt) + ".json"),
                            {"receipt": receipt, "error": str(exc)})
        raise
    return observe(root, payload)


def _hint(root: Path, session: str) -> dict[str, Any] | None:
    pointer = load_json_record(context_path(root, "sessions", digest_record(session) + ".json"))
    if "entry_id" not in pointer:
        startup = load_json_record(context_path(root, "startups", pointer["startup_id"] + ".json"))
        provisional = {**startup, "entry_id": startup["startup_id"], "change_id": "<CHANGE_ID>"}
        return {"startup_id": startup["startup_id"], "session_id": session,
                "next_command": entry_command(provisional, bind=True),
                "instructions": "Replace <CHANGE_ID> with the task's explicitly intended Change. "
                                "Bind once, then retrieve every returned next_command. "
                                "Declare adoption/challenge separately. Supply is not acquisition."}
    entry = session_entry(root, session)
    projection = project_context(root, entry["change_id"])
    try:
        manifest = read_manifest(root, entry)
        if (manifest["authority_digest"] == projection["authority_digest"]
                and len({validate_return(root, entry, manifest, r) for r in
                         observed_pages(root, entry, manifest)}) == len(manifest["chunks"])):
            return None
    except (ValueError, KeyError, OSError):
        pass
    return {"entry_id": entry["entry_id"], "change_id": entry["change_id"],
            "state": projection["identity"]["current_state"],
            "approval_id": (projection["authorization"] or {}).get("approval_id"),
            "next_command": entry_command(entry),
            "instructions": "Retrieve all current pages before product edits; retain old grounds. "
                            "Declare adoption/challenge explicitly; statements are not checks."}


def run_context_hook(event: str, cli: str | None) -> None:
    from keepsail.core.paths import find_harness_root
    from keepsail.daemon.hook_entry import decide_codex_patch
    from keepsail.gates import GateDecision

    names = {"session-start": "SessionStart", "user-prompt-submit": "UserPromptSubmit",
             "post-tool-use": "PostToolUse", "pre-tool-use": "PreToolUse"}
    if event not in names:
        return
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        payload = json.load(sys.stdin)
        root = find_harness_root(Path.cwd())
        if (not isinstance(payload, dict) or payload.get("hook_event_name") != names[event]
                or not callback_matches_workspace(root, payload.get("cwd"))):
            raise KnowledgeError("Codex callback identity unavailable")
        if event == "session-start":
            if not cli:
                raise KnowledgeError("installed startup hook must pin --cli")
            start_session(root, payload, cli_executable=cli)
            result = _hint(root, payload["session_id"])
        elif event == "user-prompt-submit":
            record_prompt(root, payload)
            result = _hint(root, payload["session_id"])
        elif event == "post-tool-use":
            if payload.get("tool_name") != "Bash":
                return
            result = observe_return(root, payload)
            if result.get("ignored"):
                return
        else:
            if payload.get("tool_name") not in {"apply_patch", "Edit", "Write"}:
                return
            if payload.get("agent_id"):
                raise KnowledgeError("subagent cannot borrow the root entry")
            tool_input = payload.get("tool_input")
            if not isinstance(tool_input, dict):
                raise KnowledgeError("patch input unavailable")
            patch = tool_input.get("command")
            if not isinstance(patch, str):
                raise KnowledgeError("patch text unavailable")
            decision, _ = decide_codex_patch(root, payload.get("session_id", ""),
                                            payload.get("turn_id", ""), patch)
            if decision.decision is GateDecision.ALLOW:
                return
            raise KnowledgeError(decision.reason + "; " + (decision.suggested_action or ""))
        if result is not None:
            content = json.dumps(result, ensure_ascii=False)
            if len(content.encode("utf-8")) > 7 * 1024:
                raise KnowledgeError("Codex entry hint exceeds budget")
            print(json.dumps({"hookSpecificOutput": {"hookEventName": names[event],
                              "additionalContext": content}}, ensure_ascii=False))
    except Exception as exc:
        if event == "pre-tool-use":
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": "Keepsail context unavailable: " + str(exc),
            }}, ensure_ascii=False))
        else:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": names[event],
                              "additionalContext": "Keepsail context unavailable: " + str(exc)}},
                             ensure_ascii=False))
