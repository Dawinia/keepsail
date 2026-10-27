"""Claude-specific context delivery and actual native CLI-return observation."""
from __future__ import annotations

import json
import os
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

from keepsail.cli.knowledge import _submit, deliver_knowledge
from keepsail.core.approval import digest_record, load_json_record
from keepsail.core.context import (
    context_path,
    entry_command,
    make_manifest,
    new_entry,
    observed_pages,
    page_data,
    project_context,
    read_entry,
    read_manifest,
    save_context_record,
    session_entry,
    validate_return,
)
from keepsail.core.knowledge import (
    PROTOCOL,
    TRIGGER_EVENT,
    KnowledgeError,
    load_ledger,
    load_policy,
)


def _summary(root: Path, entry: dict[str, Any], projection: dict[str, Any]) -> str:
    approval = projection["authorization"] or {}
    knowledge = projection["knowledge"]
    summary = {
        "change": entry["change_id"], "state": projection["identity"]["current_state"],
        "session": entry["session_id"], "entry": entry["entry_id"],
        "approval": approval.get("approval_id"), "complete_context_required": True,
        "constraints": [{"id": v["knowledge_id"], "version": v["version_digest"]}
                        for v in (knowledge["constraints"] or [])[:10]],
        "constraint_count": len(knowledge["constraints"] or []),
        "pending_impacts": sum(i["status"] != "resolved" for i in knowledge["impacts"] or []),
        "problems": projection["problems"][:5],
        "next_command": entry_command(entry),
        "instructions": (
            "Run this exact command through Bash, then retrieve every next_page in this entry. "
            "Read the returned approved commitments/restrictions, conventions and knowledge before "
            "editing. Supply is not acquisition; declare adoption or challenge explicitly. "
            "Checks and action-local authorization remain separate; "
            "no understanding/compliance claim."
        ),
    }
    text = json.dumps(summary, ensure_ascii=False)
    if len(text.encode("utf-8")) > 7 * 1024:
        summary["constraints"] = []
        summary["problems"] = ["Details require the complete context pages."]
        text = json.dumps(summary, ensure_ascii=False)
    if len(text.encode("utf-8")) > 7 * 1024:
        raise KnowledgeError("entry hint exceeds context budget")
    return text


def run_context_hook(event: str, cli: str | None) -> None:
    """Explicit opt-in dispatch; read/diagnostic hooks never block the whole turn."""
    from keepsail.core.paths import find_harness_root
    from keepsail.daemon.hook_entry import _decide, _format_block
    from keepsail.gates.decisions import CONTEXT_EDIT_TOOLS

    names = {"session-start": "SessionStart", "user-prompt-submit": "UserPromptSubmit",
             "post-tool-use": "PostToolUse", "pre-tool-use": "PreToolUse"}
    if event not in names:
        return
    try:
        payload = json.load(sys.stdin)
        root = find_harness_root(Path.cwd())
        if (not isinstance(payload, dict) or payload.get("hook_event_name") != names[event]
                or Path(payload.get("cwd", "")).resolve() != root.resolve()):
            raise KnowledgeError("context callback identity unavailable")
        change = os.environ.get("KEEPSAIL_CHANGE_ID", "")
        if event == "pre-tool-use":
            tool = payload.get("tool_name")
            if tool not in CONTEXT_EDIT_TOOLS:
                return
            if (not isinstance(payload.get("session_id"), str) or not payload["session_id"]
                    or payload.get("agent_id")):
                raise KnowledgeError("current executor session identity unavailable")
            tool_input = payload.get("tool_input")
            if not isinstance(tool_input, dict):
                raise KnowledgeError("selected edit input unavailable")
            file = tool_input.get("file_path", tool_input.get("notebook_path"))
            if not isinstance(file, str):
                raise KnowledgeError("selected edit path unavailable")
            decision, reason, next_step = _decide(
                tool, file, context_session=payload.get("session_id", ""), context_change=change,
            )
            if decision == "block":
                sys.stderr.write(_format_block(reason, next_step) + "\n")
                raise SystemExit(2)
            return
        if event == "post-tool-use":
            result = observe_return(root, payload)
            if result.get("ignored"):
                return
            text = json.dumps(result, ensure_ascii=False)
        else:
            if event == "session-start":
                if not cli:
                    raise KnowledgeError("installed context hook must pin --cli")
                entry = start_session(root, payload, cli_executable=cli, change=change)
            else:
                entry = session_entry(root, payload.get("session_id", ""))
                if entry["change_id"] != change:
                    raise KnowledgeError("session Change binding changed; restart the task session")
            projection = project_context(root, change)
            announced_path = context_path(root, entry["entry_id"], "announced.json")
            announced = {"authority_digest": projection["authority_digest"]}
            if event != "session-start" and announced_path.exists():
                from keepsail.core.approval import load_json_record
                if load_json_record(announced_path) == announced:
                    try:
                        manifest = read_manifest(root, entry)
                        pages = {validate_return(root, entry, manifest, receipt)
                                 for receipt in observed_pages(root, entry, manifest)}
                        if len(pages) == len(manifest["chunks"]):
                            return
                    except (ValueError, KeyError, TypeError, OSError):
                        pass  # A prepared hint is not proof that the session received it.
            text = _summary(root, entry, projection)
            save_context_record(root, (entry["entry_id"], "announced.json"),
                                announced, pointer=True)
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": names[event], "additionalContext": text,
        }}, ensure_ascii=False) + "\n")
    except Exception as exc:
        # Claude treats an uncaught exception's exit 1 as nonblocking. This
        # selected boundary must translate unavailable edit prerequisites to 2.
        message = "Keepsail context unavailable: " + str(exc)
        if event == "pre-tool-use":
            sys.stderr.write(message + "\n")
            raise SystemExit(2) from exc
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": names[event], "additionalContext": message,
        }}, ensure_ascii=False) + "\n")


def start_session(root: Path, payload: dict[str, Any], *, cli_executable: str,
                  change: str) -> dict[str, Any]:
    if (payload.get("hook_event_name") != "SessionStart" or payload.get("agent_id")
            or Path(payload.get("cwd", "")).resolve() != root.resolve()):
        raise KnowledgeError("invalid session-start callback", code="entry_unbound")
    entry = new_entry(root, change, payload.get("session_id", ""),
                       payload.get("source", ""), cli_executable)
    save_context_record(root, (entry["entry_id"], "session-start.json"), {
        "boundary": "session-start-callback-required-fields",
        "callback": {k: payload[k] for k in (
            "hook_event_name", "session_id", "cwd", "source", "model", "agent_type",
        ) if k in payload},
        "not_collected": ["full-transcript", "user-prompts", "credentials"],
    })
    return entry


def retrieve_context(root: Path, change: str, entry_id: str, page: int) -> dict[str, Any]:
    entry = read_entry(root, entry_id)
    if entry["change_id"] != change:
        raise KnowledgeError("entry belongs to another Change", code="entry_unbound")
    for _ in range(3):
        projection = project_context(root, change)
        selected = context_path(root, entry_id, "current.json")
        if selected.exists():
            manifest = read_manifest(root, entry)
            if manifest["authority_digest"] == projection["authority_digest"]:
                return page_data(manifest, page)
        if page != 1:
            raise KnowledgeError("context changed; retrieve page 1", code="context_stale")
        if projection["knowledge"]["coverage"] == "not_recorded":
            raise KnowledgeError("no owner-activated knowledge policy", exit_code=3)
        operation = "context-" + entry_id + "-" + projection["authority_digest"]
        ledger, revision = load_ledger(root / ".harness/events.jsonl", load_policy(root))
        prior = ledger["operations"].get(operation)
        expected = prior["request"]["expected_revision"] if prior else revision
        try:
            delivered = deliver_knowledge(root, change, operation, expected)
        except KnowledgeError as exc:
            if exc.exit_code == 5:
                continue
            raise
        current = project_context(root, change)
        if delivered["stale"] or current["authority_digest"] != projection["authority_digest"]:
            continue
        manifest = make_manifest(current, entry, delivered["delivery_id"])
        save_context_record(root, (entry_id, manifest["manifest_id"] + ".json"), manifest)
        read_entry(root, entry_id)  # A concurrent SessionStart must not revive the old epoch.
        save_context_record(root, (entry_id, "current.json"),
                            {"manifest_id": manifest["manifest_id"]}, pointer=True)
        return page_data(manifest, page)
    raise KnowledgeError("context changed during supply; retry page 1", exit_code=5,
                         code="context_stale")


def _record_acquisition(root: Path, entry: dict[str, Any], manifest: dict[str, Any],
                        version: dict[str, Any], receipts: list[dict[str, Any]]) -> None:
    policy = load_policy(root)
    if not policy or "keepsail-cli-observer" not in policy["observation_issuers"]:
        raise KnowledgeError("CLI observer is not recognized", exit_code=3)
    operation = "acquisition-" + digest_record([
        entry["entry_id"], manifest["manifest_id"], version["version_digest"],
    ])
    for _ in range(3):
        ledger, revision = load_ledger(root / ".harness/events.jsonl", policy)
        prior = ledger["operations"].get(operation)
        request = prior["request"] if prior else {
            "schema_version": PROTOCOL, "operation_id": operation,
            "expected_revision": revision, "change_id": entry["change_id"],
            "record": {
                "kind": "acquisition", "producer": "keepsail-cli-observer",
                "delivery_id": manifest["delivery_id"], "version_digest": version["version_digest"],
                "session_id": entry["session_id"], "entry_id": entry["entry_id"],
                "returned_content_digest": sha256(version["body"].encode("utf-8")).hexdigest(),
                "original_receipt": {
                    "boundary": "claude-code-native-cli-tool-return",
                    "manifest_id": manifest["manifest_id"],
                    "returned_context_digest": manifest["context_digest"], "callbacks": receipts,
                    "limits": ["local-observer-trust", "not-understanding-or-compliance"],
                },
            },
        }
        try:
            _submit(root, TRIGGER_EVENT, request)
            return
        except KnowledgeError as exc:
            if exc.exit_code != 5:
                raise
    raise KnowledgeError("acquisition revision conflict; retrieve again", exit_code=5)


def record_statement(root: Path, change: str, entry_id: str, path: str) -> dict[str, Any]:
    """Record only the executor's explicit statement; never infer adoption."""
    entry = read_entry(root, entry_id)
    manifest = read_manifest(root, entry)
    source = (root / path).resolve()
    source.relative_to(root.resolve())
    statement = load_json_record(source)
    if (entry["change_id"] != change or statement.get("schema_version") != "entry-statement/v1"
            or statement.get("entry_id") != entry_id
            or statement.get("manifest_id") != manifest["manifest_id"]
            or statement.get("decision") not in {"adopt", "reject", "challenge"}
            or not isinstance(statement.get("actor"), str) or not statement["actor"].strip()
            or not isinstance(statement.get("reason"), str) or not statement["reason"].strip()):
        raise KnowledgeError("statement must explicitly identify entry, actor, decision and reason")
    selected = statement.get("knowledge_versions", [])
    content = json.loads("".join(manifest["chunks"]))
    supplied = {v["version_digest"] for v in content["knowledge"]["constraints"]}
    if (not isinstance(selected, list) or any(not isinstance(v, str) for v in selected)
            or not set(selected).issubset(supplied)
            or (not selected and statement.get("project_context") is not True)):
        raise KnowledgeError("statement must identify supplied versions or project context")
    statement_id = digest_record(statement)
    for version in sorted(set(selected)):
        operation = "statement-" + digest_record([entry_id, statement_id, version])
        for _ in range(3):
            ledger, revision = load_ledger(root / ".harness/events.jsonl", load_policy(root))
            prior = ledger["operations"].get(operation)
            request = prior["request"] if prior else {
                "schema_version": PROTOCOL, "operation_id": operation,
                "expected_revision": revision, "change_id": change,
                "record": {
                    "kind": "challenge" if statement["decision"] == "challenge" else "statement",
                    "delivery_id": manifest["delivery_id"], "version_digest": version,
                    "session_id": entry["session_id"], "entry_id": entry_id,
                    **{str(k): statement[k] for k in (
                        "decision", "reason", "actor", "dependent_paths", "dependency",
                    ) if k in statement},
                },
            }
            try:
                _submit(root, TRIGGER_EVENT, request)
                break
            except KnowledgeError as exc:
                if exc.exit_code != 5:
                    raise
        else:
            raise KnowledgeError("statement revision conflict", exit_code=5)
    save_context_record(root, (entry_id, "statements", statement_id + ".json"), statement)
    return {"schema_version": "entry-statement/v1", "statement_id": statement_id,
            "recorded": True, "authority_effect": "unchanged", "check_result": "not_recorded"}


def observe_return(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Only recognized context invocations are retained; unrelated Bash is ignored."""
    entry = session_entry(root, payload.get("session_id", ""))
    prefix = entry_command(entry).rsplit(" ", 1)[0] + " "
    tool_input = payload.get("tool_input")
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not re.fullmatch(
        re.escape(prefix) + r"[1-9][0-9]*", command,
    ):
        return {"ignored": True}
    policy = load_policy(root)
    if not policy or "keepsail-cli-observer" not in policy["observation_issuers"]:
        raise KnowledgeError("CLI observer is not recognized", exit_code=3)
    manifest = read_manifest(root, entry)
    # Retain only the necessary callback fields, not prompts or full transcripts.
    receipt: dict[str, Any] = {k: payload[k] for k in (
        "hook_event_name", "session_id", "cwd", "tool_name", "tool_use_id",
        "tool_input", "tool_response", "agent_id",
    ) if k in payload}
    try:
        page = validate_return(root, entry, manifest, receipt)
    except (ValueError, KeyError, TypeError) as exc:
        save_context_record(root, (entry["entry_id"], "rejected",
                            digest_record(receipt) + ".json"),
                            {"receipt": receipt, "error": str(exc)})
        raise
    save_context_record(root, (entry["entry_id"], "receipts", manifest["manifest_id"],
                        digest_record(receipt["tool_use_id"]) + ".json"), receipt)
    observed = observed_pages(root, entry, manifest)
    by_page = {validate_return(root, entry, manifest, r): r for r in observed}
    if len(by_page) != len(manifest["chunks"]):
        return {"observed_page": page, "complete": False}
    ordered = [by_page[i] for i in range(1, len(manifest["chunks"]) + 1)]
    returned = "".join(json.loads(r["tool_response"]["stdout"])["data"]["content"] for r in ordered)
    if sha256(returned.encode("utf-8")).hexdigest() != manifest["context_digest"]:
        raise KnowledgeError("incomplete returned context", code="page_incomplete")
    content = json.loads(returned)
    for version in content["knowledge"]["constraints"]:
        _record_acquisition(root, entry, manifest, version, ordered)
    return {"observed_page": page, "complete": True, "boundary": "cli-tool-return",
            "empty_set_observed": not content["knowledge"]["constraints"]}
