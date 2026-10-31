"""Claude-specific context delivery and actual native CLI-return observation."""
from __future__ import annotations

import json
import os
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

from keepsail.cli.knowledge import _submit, deliver_knowledge
from keepsail.core.approval import digest_record
from keepsail.core.context import (
    acquired_versions,
    callback_matches_workspace,
    cleanup_context_returns,
    compact_context_observation,
    context_invocation,
    context_path,
    entry_command,
    make_manifest,
    new_entry,
    observed_pages,
    page_data,
    project_context,
    read_entry,
    read_manifest,
    receipt_parts,
    returned_stdout,
    save_context_record,
    session_entry,
    validate_return,
)
from keepsail.core.knowledge import (
    ACQUISITION_OBSERVATION_SCHEMA,
    CLAUDE_RETURN_TRANSPORT,
    CONTEXT_OBSERVATION_SCHEMA,
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
        "unresolved_project_declarations": len(projection["recovery"]["unresolved_declarations"]),
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
                or not callback_matches_workspace(root, payload.get("cwd"))):
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
                        ledger, _ = load_ledger(root / ".harness/events.jsonl", load_policy(root))
                        compact = compact_context_observation(ledger, entry, manifest)
                        complete = compact is not None or len({
                            validate_return(root, entry, manifest, receipt)
                            for receipt in observed_pages(root, entry, manifest)
                        }) == len(manifest["chunks"])
                        required = {v["version_digest"]
                                    for v in projection["knowledge"]["constraints"]}
                        if (manifest["authority_digest"] == projection["authority_digest"]
                                and complete
                                and (compact is not None or manifest.get("observation_schema")
                                     != CONTEXT_OBSERVATION_SCHEMA)
                                and required.issubset(
                                    acquired_versions(ledger, entry, manifest))):
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
            or not callback_matches_workspace(root, payload.get("cwd"))):
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
            cleanup_context_returns(root, entry, manifest, reason="invalidated")
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


def _record_observer_fact(root: Path, entry: dict[str, Any], operation: str,
                          record: dict[str, Any]) -> None:
    policy = load_policy(root)
    if not policy or "keepsail-cli-observer" not in policy["observation_issuers"]:
        raise KnowledgeError("CLI observer is not recognized", exit_code=3)
    for _ in range(3):
        ledger, revision = load_ledger(root / ".harness/events.jsonl", policy)
        prior = ledger["operations"].get(operation)
        if prior and prior["request"]["record"] != record:
            raise KnowledgeError("observation operation identity conflict; retry", exit_code=5)
        request = prior["request"] if prior else {
            "schema_version": PROTOCOL, "operation_id": operation,
            "expected_revision": revision, "change_id": entry["change_id"],
            "record": record,
        }
        try:
            _submit(root, TRIGGER_EVENT, request)
            return
        except KnowledgeError as exc:
            if exc.exit_code != 5:
                raise
    raise KnowledgeError("acquisition revision conflict; retrieve again", exit_code=5)


def _record_context_acquisition(
    root: Path, entry: dict[str, Any], manifest: dict[str, Any],
    receipts: list[dict[str, Any]], versions: list[dict[str, Any]],
) -> str:
    policy = load_policy(root)
    ledger, _ = load_ledger(root / ".harness/events.jsonl", policy)
    prior = compact_context_observation(ledger, entry, manifest)
    if prior:
        return str(prior["observation_id"])
    assert policy is not None
    identifier = "context-observation-" + digest_record([
        entry["entry_id"], manifest["manifest_id"],
    ])
    record = {
        "schema_version": CONTEXT_OBSERVATION_SCHEMA, "kind": "context-acquisition",
        "observation_id": identifier, "producer": "keepsail-cli-observer",
        "observer_version": "native-cli-observer/v2", "product_id": policy["product_id"],
        "repository_id": policy["repository_id"], "change_id": entry["change_id"],
        "entry_id": entry["entry_id"], "session_id": entry["session_id"],
        "delivery_id": manifest["delivery_id"], "manifest_id": manifest["manifest_id"],
        "authority_digest": manifest["authority_digest"],
        "context_digest": manifest["context_digest"],
        "harness": entry.get("harness", "claude-code"),
        "return_transport": entry.get("return_transport", CLAUDE_RETURN_TRANSPORT),
        "pages": [{"page": i, "total_pages": len(receipts),
                   "content_digest": sha256(manifest["chunks"][i - 1].encode("utf-8")).hexdigest(),
                   "tool_use_id": receipt["tool_use_id"],
                   "root_turn_id": (receipt.get("turn_id")
                                    if entry.get("harness") == "codex" else None)}
                  for i, receipt in enumerate(receipts, 1)],
        "versions": [{"version_digest": v["version_digest"],
                      "returned_content_digest": sha256(v["body"].encode("utf-8")).hexdigest()}
                     for v in sorted(versions, key=lambda v: v["version_digest"])],
        "status": "complete", "limits": ["local-observer-trust", "not-understanding-or-compliance"],
    }
    _record_observer_fact(root, entry, identifier, record)
    return identifier


def _record_acquisition(root: Path, entry: dict[str, Any], manifest: dict[str, Any],
                        version: dict[str, Any], observation_id: str) -> None:
    operation = "acquisition-v2-" + digest_record([
        entry["entry_id"], manifest["manifest_id"], version["version_digest"],
    ])
    _record_observer_fact(root, entry, operation, {
        "schema_version": ACQUISITION_OBSERVATION_SCHEMA, "kind": "acquisition",
        "producer": "keepsail-cli-observer", "observation_id": observation_id,
        "delivery_id": manifest["delivery_id"], "version_digest": version["version_digest"],
        "session_id": entry["session_id"], "entry_id": entry["entry_id"],
        "returned_content_digest": sha256(version["body"].encode("utf-8")).hexdigest(),
    })


def record_statement(root: Path, change: str, entry_id: str, path: str) -> dict[str, Any]:
    """Record only the executor's explicit statement; never infer adoption."""
    entry = read_entry(root, entry_id)
    manifest = read_manifest(root, entry)
    from keepsail.core.approval import load_json_input

    if path == "-":
        statement = load_json_input(path)
    else:
        source = (root / path).resolve()
        source.relative_to(root.resolve())
        statement = load_json_input(source)
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
    tool_input = payload.get("tool_input")
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not context_invocation(entry, command):
        return {"ignored": True}
    policy = load_policy(root)
    if not policy or "keepsail-cli-observer" not in policy["observation_issuers"]:
        raise KnowledgeError("CLI observer is not recognized", exit_code=3)
    manifest = read_manifest(root, entry)
    # Retain only the necessary callback fields, not prompts or full transcripts.
    receipt: dict[str, Any] = {k: payload[k] for k in (
        "hook_event_name", "session_id", "cwd", "tool_name", "tool_use_id",
        "tool_input", "tool_response", "agent_id", "turn_id",
    ) if k in payload}
    try:
        page = validate_return(root, entry, manifest, receipt)
    except (ValueError, KeyError, TypeError) as exc:
        rejected = ((entry["entry_id"], "rejected-v2", manifest["manifest_id"])
                    if manifest.get("observation_schema") == CONTEXT_OBSERVATION_SCHEMA
                    else (entry["entry_id"], "rejected"))
        save_context_record(root, (*rejected, digest_record(receipt) + ".json"),
                            {"receipt": receipt, "error": str(exc),
                             "error_code": getattr(exc, "code", "page_incomplete")})
        raise
    save_context_record(root, (*receipt_parts(entry, manifest),
                        digest_record(receipt["tool_use_id"]) + ".json"), receipt)
    ledger, _ = load_ledger(root / ".harness/events.jsonl", policy)
    compact = compact_context_observation(ledger, entry, manifest)
    required = {v["version_digest"] for v in json.loads("".join(manifest["chunks"]))[
        "knowledge"]["constraints"]}
    if compact and required.issubset(acquired_versions(ledger, entry, manifest)):
        cleanup_context_returns(root, entry, manifest)
        return {"observed_page": page, "complete": True, "native_acquisition": "recorded"}
    observed = observed_pages(root, entry, manifest)
    by_page = {validate_return(root, entry, manifest, r): r for r in observed}
    if len(by_page) != len(manifest["chunks"]):
        return {"observed_page": page, "complete": False}
    if entry.get("harness") == "codex":
        # Never perform slow ledger transactions within the fixed hook budget.
        # The CLI consumes these actual immutable returns, not a self-reported hash.
        return {"observed_page": page, "complete": True, "native_acquisition": "pending",
                "next_command": entry_command(entry, finalize=True)}
    _record_complete_returns(root, entry, manifest, by_page)
    return {"observed_page": page, "complete": True, "boundary": "cli-tool-return",
            "empty_set_observed": not json.loads("".join(manifest["chunks"]))[
                "knowledge"]["constraints"]}


def _record_complete_returns(root: Path, entry: dict[str, Any], manifest: dict[str, Any],
                             by_page: dict[int, dict[str, Any]]) -> int:
    if set(by_page) != set(range(1, len(manifest["chunks"]) + 1)):
        raise KnowledgeError("complete actual tool returns required", code="page_incomplete")
    ordered = [by_page[i] for i in range(1, len(manifest["chunks"]) + 1)]
    returned = "".join(json.loads(returned_stdout(entry, r))["data"]["content"] for r in ordered)
    if sha256(returned.encode("utf-8")).hexdigest() != manifest["context_digest"]:
        raise KnowledgeError("incomplete returned context", code="page_incomplete")
    content = json.loads(returned)
    versions = content["knowledge"]["constraints"]
    ledger, _ = load_ledger(root / ".harness/events.jsonl", load_policy(root))
    acquired = acquired_versions(ledger, entry, manifest)
    # Complete legacy acquisitions remain idempotent and keep their original raw.
    if manifest.get("observation_schema") != CONTEXT_OBSERVATION_SCHEMA and versions and (
        {v["version_digest"] for v in versions}.issubset(acquired)
    ):
        return len(versions)
    current = project_context(root, entry["change_id"])
    if current["authority_digest"] != manifest["authority_digest"]:
        raise KnowledgeError("current authority requires context refresh", code="context_stale")
    observation_id = _record_context_acquisition(root, entry, manifest, ordered, versions)
    for version in versions:
        if version["version_digest"] not in acquired:
            _record_acquisition(root, entry, manifest, version, observation_id)
    read_entry(root, entry["entry_id"])
    current = project_context(root, entry["change_id"])
    if current["authority_digest"] != manifest["authority_digest"]:
        raise KnowledgeError("authority changed during acquisition; refresh", code="context_stale")
    cleanup_context_returns(root, entry, manifest)
    return len(versions)


def finalize_acquisition(root: Path, change: str, entry_id: str) -> dict[str, Any]:
    """Native writes outside Codex's hook deadline; preserved raw returns are mandatory."""
    entry = read_entry(root, entry_id)
    if entry.get("harness") != "codex" or entry["change_id"] != change:
        raise KnowledgeError("finalization requires the selected Codex entry")
    manifest = read_manifest(root, entry)
    if project_context(root, change)["authority_digest"] != manifest["authority_digest"]:
        raise KnowledgeError("current authority requires context refresh", code="context_stale")
    ledger, _ = load_ledger(root / ".harness/events.jsonl", load_policy(root))
    compact = compact_context_observation(ledger, entry, manifest)
    if compact and {v["version_digest"] for v in compact["versions"]}.issubset(
        acquired_versions(ledger, entry, manifest)
    ):
        count = len(compact["versions"])
        cleanup_context_returns(root, entry, manifest)
    else:
        by_page = {validate_return(root, entry, manifest, r): r
                   for r in observed_pages(root, entry, manifest)}
        count = _record_complete_returns(root, entry, manifest, by_page)
    read_entry(root, entry_id)
    if project_context(root, change)["authority_digest"] != manifest["authority_digest"]:
        raise KnowledgeError("authority changed during acquisition; refresh", code="context_stale")
    return {"entry_id": entry_id, "manifest_id": manifest["manifest_id"],
            "native_acquisition": "recorded" if count else "not_applicable",
            "version_count": count, "empty_set_observed": count == 0,
            "boundary": "retained-cli-tool-returns",
            "understanding": "not_observed", "compliance": "not_checked"}
