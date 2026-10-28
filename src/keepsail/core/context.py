"""Bounded projections of existing authority; never a second approval source."""
from __future__ import annotations

import json
import os
import re
import shlex
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from keepsail.core.approval import (
    canonical_json,
    digest_record,
    load_json_record,
    resolve_contract_base,
    validate_approval,
)
from keepsail.core.decisions import compute_body_hash, load_decisions
from keepsail.core.events import EventSchemaError, effective_event_lines, parse_event_line
from keepsail.core.file_lock import exclusive_file_lock
from keepsail.core.knowledge import KnowledgeError, check, load_ledger, load_policy, report
from keepsail.core.paths import HarnessNotInitialized, canonical_relpath, find_harness_root
from keepsail.core.reducer import derive_state
from keepsail.core.scope_match import resolve_commit
from keepsail.core.slug import validate_slug
from keepsail.core.state import ChangeState
from keepsail.core.ulid import new_event_id

SCHEMA = "agent-context/v1"
PAGE_BYTES = 24 * 1024
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_AUTHORITY_FIELDS = (
    "identity", "authorization", "policy_digest", "pending_revision",
    "authorization_lineage", "conventions", "knowledge", "problems",
)


@dataclass(frozen=True)
class EntryReadiness:
    blocking_reasons: tuple[str, ...]
    next_command: str


def callback_matches_workspace(root: Path, cwd: Any) -> bool:
    """Bind a callback to its nearest workspace, including valid subdirectories."""
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return False
    try:
        return find_harness_root(Path(cwd)) == root.resolve()
    except (HarnessNotInitialized, ValueError, OSError):
        return False


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise KnowledgeError("duplicate context JSON key")
        result[key] = value
    return result


def context_path(root: Path, *parts: str) -> Path:
    """Only the existing operation-log area; refuse links/reparse-point escapes."""
    path = root.resolve()
    for part in (".harness", "operation-logs", "context", *parts):
        if part in {".", ".."} or "/" in part or "\\" in part:
            raise KnowledgeError("invalid context path")
        path = path / part
        if path.exists() or path.is_symlink():
            stat = path.lstat()
            if path.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
                raise KnowledgeError("linked context path", code="context_unavailable")
    return path


def save_context_record(root: Path, parts: tuple[str, ...], value: dict[str, Any], *,
                        pointer: bool = False) -> None:
    """Receipts are immutable. Only reconstructible current pointers are replaced."""
    path = context_path(root, *parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    context_path(root, *parts)
    body = canonical_json(value).encode("utf-8")
    if not pointer:
        try:
            with path.open("xb") as stream:
                stream.write(body)
        except FileExistsError:
            if path.read_bytes() != body:
                raise KnowledgeError("immutable context record conflict", exit_code=5) from None
        return
    descriptor, name = tempfile.mkstemp(prefix=".pointer-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(body)
        context_path(root, *parts)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_entry(root: Path, entry_id: str) -> dict[str, Any]:
    if not _ID.fullmatch(entry_id):
        raise KnowledgeError("invalid entry identity", code="entry_unbound")
    entry = load_json_record(context_path(root, entry_id, "entry.json"))
    if entry.get("root") != root.resolve().as_posix() or entry.get("entry_id") != entry_id:
        raise KnowledgeError("entry belongs to another workspace", code="entry_unbound")
    session = entry.get("session_id")
    if not isinstance(session, str) or not _ID.fullmatch(session):
        raise KnowledgeError("invalid session identity", code="entry_unbound")
    pointer = load_json_record(context_path(root, "sessions", digest_record(session) + ".json"))
    if pointer != {"entry_id": entry_id}:
        raise KnowledgeError("entry was replaced by a new session epoch", code="context_stale")
    return entry


def new_entry(root: Path, change: str, session: str, source: str, cli: str, *,
              entry_id: str | None = None, harness: str = "claude-code") -> dict[str, Any]:
    validate_slug(change)
    if not _ID.fullmatch(session) or source not in {
        "startup", "resume", "clear", "compact", "fork",
    }:
        raise KnowledgeError("invalid session-start identity", code="entry_unbound")
    # Validate the selected Change and current authority before binding a session.
    project_context(root, change)
    entry = {"entry_id": entry_id or new_event_id(), "change_id": change, "session_id": session,
             "source": source, "root": root.resolve().as_posix(), "cli": cli.replace("\\", "/")}
    if harness == "codex":
        entry["harness"] = harness
    save_context_record(root, (entry["entry_id"], "entry.json"), entry)
    save_context_record(root, ("sessions", digest_record(session) + ".json"),
                        {"entry_id": entry["entry_id"]}, pointer=True)
    return entry


def capture_codex_startup(root: Path, payload: dict[str, Any], cli: str) -> dict[str, Any]:
    session, source = payload.get("session_id"), payload.get("source")
    if (payload.get("hook_event_name") != "SessionStart" or payload.get("agent_id")
            or not callback_matches_workspace(root, payload.get("cwd"))
            or not isinstance(session, str) or not _ID.fullmatch(session)
            or source not in {"startup", "resume", "clear", "compact", "fork"}):
        raise KnowledgeError("invalid Codex startup", code="entry_unbound")
    startup = {"startup_id": new_event_id(), "session_id": session, "source": source,
               "root": root.resolve().as_posix(), "cli": cli.replace("\\", "/"),
               "harness": "codex", "callback": {k: payload[k] for k in (
                   "hook_event_name", "session_id", "source", "cwd", "model",
               ) if k in payload}}
    with exclusive_file_lock(context_path(root, "sessions", digest_record(session) + ".lock")):
        continuing = None
        pointer_path = context_path(root, "sessions", digest_record(session) + ".json")
        turn_path = context_path(root, "sessions", digest_record(session) + "-turn.json")
        if source == "compact" and pointer_path.exists() and turn_path.exists():
            prior_pointer = load_json_record(pointer_path)
            prior_turn = load_json_record(turn_path)
            prior_startup = prior_pointer.get("startup_id", prior_pointer.get("entry_id"))
            try:
                if not isinstance(prior_startup, str):
                    raise KnowledgeError("prior startup unavailable")
                codex_root_turn(root, prior_startup, prior_turn)
                continuing = prior_turn
                startup["continuing_root_turn"] = prior_turn
            except (ValueError, KeyError, TypeError, OSError):
                pass  # Missing attribution cannot be repaired by assuming a root turn.
        save_context_record(root, ("startups", startup["startup_id"] + ".json"), startup)
        save_context_record(root, ("sessions", digest_record(session) + ".json"),
                            {"startup_id": startup["startup_id"]}, pointer=True)
        if continuing:
            save_codex_root_turn(root, {**continuing, "startup_id": startup["startup_id"],
                                        "attribution": "compact-continuation"})
    return startup


def bind_startup(root: Path, change: str, startup_id: str) -> dict[str, Any]:
    if not _ID.fullmatch(startup_id):
        raise KnowledgeError("invalid startup identity", code="entry_unbound")
    startup = load_json_record(context_path(root, "startups", startup_id + ".json"))
    if (startup.get("root") != root.resolve().as_posix()
            or startup.get("startup_id") != startup_id or startup.get("harness") != "codex"):
        raise KnowledgeError("startup workspace mismatch", code="entry_unbound")
    session = startup["session_id"]
    with exclusive_file_lock(context_path(root, "sessions", digest_record(session) + ".lock")):
        pointer = load_json_record(context_path(root, "sessions", digest_record(session) + ".json"))
        if pointer == {"entry_id": startup_id}:
            entry = read_entry(root, startup_id)
            if entry["change_id"] != change:
                raise KnowledgeError("startup already bound to another Change",
                                     code="entry_unbound")
            return entry
        if pointer != {"startup_id": startup_id}:
            raise KnowledgeError("startup was replaced", code="context_stale")
        return new_entry(root, change, session, startup["source"], startup["cli"],
                         entry_id=startup_id, harness="codex")


def session_entry(root: Path, session: str) -> dict[str, Any]:
    if not isinstance(session, str) or not _ID.fullmatch(session):
        raise KnowledgeError("missing session identity", code="entry_unbound")
    value = load_json_record(context_path(root, "sessions", digest_record(session) + ".json"))
    return read_entry(root, value["entry_id"])


def entry_command(entry: dict[str, Any], page: int = 1, *, bind: bool = False) -> str:
    args = (
        entry["cli"], "--workspace", entry["root"], "--json", "change", "context",
        entry["change_id"], *( ("--bind-startup", entry["entry_id"]) if bind
                            else ("--entry", entry["entry_id"], "--page", page)),
    )
    if entry.get("harness") == "codex":
        quoted = " ".join("'" + str(arg).replace("'", "''") + "'" for arg in args)
        return "$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & " + quoted
    return " ".join(shlex.quote(str(arg)) for arg in args)


def context_invocation(entry: dict[str, Any], command: Any) -> bool:
    prefix = entry_command(entry).rsplit(" ", 1)[0] + " "
    return isinstance(command, str) and bool(
        re.fullmatch(re.escape(prefix) + r"'?[1-9][0-9]*'?", command)
        or (entry.get("harness") == "codex" and command == entry_command(entry, bind=True))
    )


def save_codex_root_turn(root: Path, value: dict[str, Any]) -> None:
    """Caller holds the session lock; retain each epoch's attribution separately."""
    key = digest_record([value["session_id"], value["turn_id"], value["startup_id"]])
    save_context_record(root, ("turns", key + ".json"), value)
    save_context_record(root, ("sessions", digest_record(value["session_id"]) + "-turn.json"),
                        value, pointer=True)


def codex_root_turn(root: Path, startup_id: str, payload: dict[str, Any], *,
                     current: bool = True) -> None:
    session, turn = payload.get("session_id"), payload.get("turn_id")
    if (not isinstance(turn, str) or not _ID.fullmatch(turn) or payload.get("agent_id")
            or not isinstance(session, str) or not _ID.fullmatch(session)):
        raise KnowledgeError("Codex root turn unavailable")
    key = digest_record([session, turn, startup_id])
    record = load_json_record(context_path(root, "turns", key + ".json"))
    if any(record.get(k) != v for k, v in {
        "session_id": session, "turn_id": turn, "startup_id": startup_id,
    }.items()):
        raise KnowledgeError("Codex turn belongs to another startup")
    callback = record.get("callback", {})
    if (not isinstance(callback, dict) or callback.get("hook_event_name") != "UserPromptSubmit"
            or callback.get("session_id") != session or callback.get("turn_id") != turn
            or not callback_matches_workspace(root, callback.get("cwd"))):
        raise KnowledgeError("Codex root prompt provenance unavailable")
    if current and load_json_record(context_path(root, "sessions",
                                                digest_record(session) + "-turn.json")) != record:
        raise KnowledgeError("Codex callback is not the current observed root turn")


def returned_stdout(entry: dict[str, Any], payload: dict[str, Any]) -> str:
    response = payload.get("tool_response")
    if entry.get("harness") == "codex":
        # Candidate wire contract. Unknown native output remains not_observed;
        # actual desktop callback/transport acceptance is separately required.
        if (not isinstance(response, dict)
                or not set(response).issubset({"output", "exit_code", "chunk_id",
                                              "wall_time_seconds", "original_token_count"})
                or type(response.get("exit_code")) is not int or response["exit_code"] != 0
                or not isinstance(response.get("output"), str)):
            raise KnowledgeError("incomplete or unknown Codex CLI return", code="page_incomplete")
        return str(response["output"])
    if (not isinstance(response, dict) or response.get("interrupted") is not False
            or not isinstance(response.get("stdout"), str)
            or not isinstance(response.get("stderr"), str)
            or any(response.get(k) for k in (
                "backgroundTaskId", "backgroundedByUser", "timedOutAfterMs", "isImage",
                "rawOutputPath", "persistedOutputPath", "persistedOutputSize",
            ))):
        raise KnowledgeError("incomplete native CLI return", code="page_incomplete")
    return str(response["stdout"])


def make_manifest(projection: dict[str, Any], entry: dict[str, Any],
                  delivery_id: str) -> dict[str, Any]:
    text = canonical_json({**projection, "supply_status": "prepared", "entry": entry,
                           "delivery_id": delivery_id})
    chunks = []
    while text:
        low, high = 1, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if len(json.dumps(text[:middle], ensure_ascii=False).encode()) <= 20 * 1024:
                low = middle
            else:
                high = middle - 1
        chunks.append(text[:low])
        text = text[low:]
    manifest = {
        "schema_version": SCHEMA, "entry_id": entry["entry_id"],
        "session_id": entry["session_id"], "change_id": entry["change_id"],
        "authority_digest": projection["authority_digest"], "delivery_id": delivery_id,
        "context_digest": sha256("".join(chunks).encode("utf-8")).hexdigest(),
        "chunks": chunks,
    }
    manifest["manifest_id"] = digest_record(manifest)
    return manifest


def read_manifest(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    selected = load_json_record(context_path(root, entry["entry_id"], "current.json"))
    return _manifest_at(root, entry, selected["manifest_id"])


def _manifest_at(root: Path, entry: dict[str, Any], mid: str) -> dict[str, Any]:
    if not isinstance(mid, str) or not re.fullmatch(r"[0-9a-f]{64}", mid):
        raise KnowledgeError("invalid manifest identity")
    manifest = load_json_record(context_path(root, entry["entry_id"], mid + ".json"))
    if (manifest.get("entry_id") != entry["entry_id"]
            or manifest.get("session_id") != entry["session_id"]
            or manifest.get("change_id") != entry["change_id"]
            or manifest.get("schema_version") != SCHEMA
            or digest_record({k: v for k, v in manifest.items() if k != "manifest_id"}) != mid):
        raise KnowledgeError("manifest integrity mismatch", code="context_unavailable")
    text = "".join(manifest["chunks"])
    content = json.loads(text, object_pairs_hook=_unique_object)
    if (sha256(text.encode("utf-8")).hexdigest() != manifest["context_digest"]
            or content["entry"] != entry or content["delivery_id"] != manifest["delivery_id"]
            or digest_record({k: content[k] for k in _AUTHORITY_FIELDS
                              if k != "authorization_lineage" or k in content})
            != manifest["authority_digest"]):
        raise KnowledgeError("manifest content does not match authority",
                             code="context_unavailable")
    return manifest


def _project_statements(root: Path, change: str,
                        ledger: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Recover retained self-reports without granting knowledge/approval authority."""
    entry_ids = set()
    for delivery_id, delivery in ledger["deliveries"].items():
        match = re.fullmatch(r"context-([A-Za-z0-9_-]{1,128})-[0-9a-f]{64}", delivery_id)
        if delivery["change_id"] == change and match:
            entry_ids.add(match[1])
    declarations, problems = [], []
    # ponytail: scan this Change's retained entry declarations; index only if measured costly.
    for entry_id in sorted(entry_ids):
        try:
            directory = context_path(root, entry_id, "statements")
            if not directory.exists():
                continue
            entry = load_json_record(context_path(root, entry_id, "entry.json"))
            if (entry.get("entry_id") != entry_id or entry.get("change_id") != change
                    or entry.get("root") != root.resolve().as_posix()):
                raise KnowledgeError("historical entry identity mismatch")
            for path in sorted(directory.glob("*.json")):
                statement = load_json_record(context_path(root, entry_id, "statements", path.name))
                manifest = _manifest_at(root, entry, statement["manifest_id"])
                if (statement.get("schema_version") != "entry-statement/v1"
                        or statement.get("entry_id") != entry_id
                        or digest_record(statement) != path.stem
                        or manifest["delivery_id"] not in ledger["deliveries"]):
                    raise KnowledgeError("historical statement integrity mismatch")
                declarations.append({
                    "statement_id": path.stem, "change_id": change,
                    "source_entry_id": entry_id, "source_session_id": entry["session_id"],
                    "manifest_id": statement["manifest_id"], "declaration": statement,
                    "category": "executor-self-report", "authority_effect": "unchanged",
                    "status": "unresolved" if statement["decision"] == "challenge" else "declared",
                    "recognized_disposition": None, "current_epoch_observation": False,
                    "resolution_scope": "no linked recognized conclusion in this carrier",
                    "locator": path.relative_to(root).as_posix(),
                })
        except (ValueError, KeyError, TypeError, OSError) as exc:
            problems.append(f"entry declaration unavailable: {entry_id}: {exc}")
    return declarations, problems


def page_data(manifest: dict[str, Any], page: int) -> dict[str, Any]:
    if not 1 <= page <= len(manifest["chunks"]):
        raise KnowledgeError("invalid context page")
    content = manifest["chunks"][page - 1]
    data = {k: manifest[k] for k in (
        "schema_version", "entry_id", "session_id", "change_id", "authority_digest",
        "delivery_id", "context_digest", "manifest_id",
    )} | {"page": page, "total_pages": len(manifest["chunks"]), "content": content,
         "content_digest": sha256(content.encode("utf-8")).hexdigest(),
         "utf8_bytes": len(content.encode("utf-8")),
         "token_estimate": (len(content.encode("utf-8")) + 2) // 3,
         "token_estimate_method": "UTF8 bytes / 3 heuristic; not measured tokens",
         "next_page": page + 1 if page < len(manifest["chunks"]) else None}
    entry = json.loads("".join(manifest["chunks"]))["entry"]
    if entry.get("harness") == "codex":
        data["next_command"] = entry_command(entry, page + 1) if data["next_page"] else None
    return data


def validate_return(root: Path, entry: dict[str, Any], manifest: dict[str, Any],
                    payload: dict[str, Any]) -> int:
    """Validate an actual native CLI tool-return callback, never a claimed hash."""
    if (not isinstance(payload.get("tool_input"), dict)
            or payload.get("hook_event_name") != "PostToolUse" or payload.get("tool_name") != "Bash"
            or payload.get("session_id") != entry["session_id"] or payload.get("agent_id")
            or not callback_matches_workspace(root, payload.get("cwd"))
            or not isinstance(payload.get("tool_use_id"), str) or not payload["tool_use_id"]):
        raise KnowledgeError("tool return identity mismatch", code="page_incomplete")
    if entry.get("harness") == "codex":
        codex_root_turn(root, entry["entry_id"], payload, current=False)
    stdout = returned_stdout(entry, payload)
    envelope = json.loads(stdout, object_pairs_hook=_unique_object)
    if (not isinstance(envelope, dict)
            or set(envelope) != {"command", "version", "status", "exit_code", "data", "errors"}
            or envelope["command"] != "change context" or envelope["exit_code"] != 0
            or envelope["status"] not in {"pass", "warning"} or envelope["errors"] != []):
        raise KnowledgeError("not a successful context retrieval", code="page_incomplete")
    data = envelope["data"]
    if not isinstance(data, dict):
        raise KnowledgeError("invalid context return data", code="page_incomplete")
    page = data.get("page")
    if type(page) is not int:
        raise KnowledgeError("invalid context page", code="page_incomplete")
    commands = {entry_command(entry, page)}
    if entry.get("harness") == "codex" and page == 1:
        commands.add(entry_command(entry, bind=True))
    if (data != page_data(manifest, page)
            or payload.get("tool_input", {}).get("command") not in commands
            or len(stdout.encode("utf-8")) > PAGE_BYTES):
        raise KnowledgeError("returned page differs from supplied content", code="page_incomplete")
    return page


def observed_pages(root: Path, entry: dict[str, Any],
                   manifest: dict[str, Any]) -> list[dict[str, Any]]:
    directory = context_path(root, entry["entry_id"], "receipts", manifest["manifest_id"])
    receipts = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        receipt = load_json_record(context_path(
            root, entry["entry_id"], "receipts", manifest["manifest_id"], path.name,
        ))
        validate_return(root, entry, manifest, receipt)
        receipts.append(receipt)
    return receipts


def entry_readiness(root: Path, change: str, session: str,
                    action_path: str | list[str] | None = None) -> dict[str, Any]:
    """Current supply, this epoch's complete returns and local dependencies separately."""
    reasons = []
    current: dict[str, Any] | None = None
    command = "Run the bound SessionStart hook and retrieve its context pages."
    try:
        entry = session_entry(root, session)
        command = entry_command(entry)
        if entry["change_id"] != change:
            raise KnowledgeError("session is bound to another Change", code="entry_unbound")
        current = project_context(root, change)
        manifest = read_manifest(root, entry)
        if manifest["authority_digest"] != current["authority_digest"]:
            raise KnowledgeError("current authority requires context refresh", code="context_stale")
        receipts = observed_pages(root, entry, manifest)
        pages = {validate_return(root, entry, manifest, receipt) for receipt in receipts}
        missing = sorted(set(range(1, len(manifest["chunks"]) + 1)) - pages)
        if missing:
            reasons.append(f"context pages not observed: {missing}")
            command = entry_command(entry, missing[0])
        ledger, _ = load_ledger(root / ".harness/events.jsonl", load_policy(root))
        policy = load_policy(root)
        if not policy or "keepsail-cli-observer" not in policy["observation_issuers"]:
            reasons.append("CLI observer is not recognized")
        delivery = ledger["deliveries"].get(manifest["delivery_id"])
        knowledge = current["knowledge"]
        if (delivery is None or delivery["basis_digest"] != knowledge["basis_digest"]
                or delivery["constraints"] != knowledge["constraints"]):
            reasons.append("current constraints require an exact retained delivery")
        for version in knowledge["constraints"] or []:
            if not any(o.get("delivery_id") == manifest["delivery_id"]
                       and o.get("version_digest") == version["version_digest"]
                       and o.get("entry_id") == entry["entry_id"]
                       and o.get("session_id") == session for o in ledger["observations"]):
                reasons.append(f"current entry acquisition missing: {version['knowledge_id']}")
        paths = (action_path if isinstance(action_path, list)
                 else [action_path] if action_path else [])
        if paths:
            action_knowledge = report(root, change, extra_paths=paths)
            if action_knowledge["constraints"] != knowledge["constraints"] or any(
                reason.startswith("unknown applicability:")
                and reason not in (knowledge["blocking_reasons"] or [])
                for reason in action_knowledge["blocking_reasons"]
            ):
                reasons.append("action reveals additional constraints; record within-approval "
                               "coverage, then refresh context")
                command = (f"keepsail implementation record {change} --assessment <path>; "
                           "then " + entry_command(entry))
        reasons.extend(current["problems"])
        check(root, change, paths=paths or None)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        reasons.append(str(exc))
    return {"ready": not reasons, "blocking_reasons": reasons, "next_command": command,
            "current_state": current["identity"]["current_state"] if current else None,
            "approval_id": (current.get("authorization") or {}).get("approval_id")
            if current else None}


def context_gate_inputs(root: Path, change: str, session: str,
                        action_path: str | list[str] | None
                        ) -> tuple[ChangeState | None, EntryReadiness]:
    """The same current-state/readiness seam for the selected hook and gate CLI."""
    try:
        validate_slug(change)
        state = derive_state(root / ".harness/events.jsonl").get(change)
        value = entry_readiness(root, change, session, action_path)
        reasons = list(value["blocking_reasons"])
        if not action_path:
            reasons.append("selected edit path unavailable")
        if state is None or value["current_state"] != state.current_state or (
            value["approval_id"] != (state.effective_approval or {}).get("approval_id")
        ):
            reasons.append("selected lifecycle or approval snapshot unavailable/stale")
        return state, EntryReadiness(tuple(reasons), value["next_command"])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return None, EntryReadiness((str(exc),),
                                    "Set KEEPSAIL_CHANGE_ID and start the task session.")


def codex_patch_paths(root: Path, patch: Any) -> list[str]:
    """Extract every file/move path from the selected native patch grammar."""
    if not isinstance(patch, str):
        raise KnowledgeError("patch text unavailable")
    lines = patch.splitlines()
    if len(lines) < 3 or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise KnowledgeError("patch boundaries unavailable")
    paths, i = [], 1

    def add(raw: str) -> None:
        if not raw or raw.strip() != raw or "\x00" in raw:
            raise KnowledgeError("invalid patch path")
        path = canonical_relpath(root, raw)
        if path in {None, "."}:
            raise KnowledgeError("patch path outside workspace or unresolved")
        if path not in paths:
            paths.append(path)

    while i < len(lines) - 1:
        header = re.fullmatch(r"\*\*\* (Add|Update|Delete) File: (.+)", lines[i])
        if not header:
            raise KnowledgeError("unrecognized patch file header")
        mode = header[1]
        add(header[2])
        i += 1
        if mode == "Update" and lines[i].startswith("*** Move to: "):
            add(lines[i][13:])
            i += 1
        body = []
        while i < len(lines) - 1 and not re.match(r"\*\*\* (Add|Update|Delete) File: ", lines[i]):
            body.append(lines[i])
            i += 1
        if mode == "Delete" and body:
            raise KnowledgeError("delete patch has unexpected body")
        if mode == "Add" and any(not line.startswith("+") for line in body):
            raise KnowledgeError("add patch body unavailable")
        if mode == "Update" and (not body or any(
            not (line.startswith(("@@", " ", "+", "-")) or line == "*** End of File")
            for line in body
        )):
            raise KnowledgeError("update patch body unavailable")
    if not paths:
        raise KnowledgeError("patch paths unavailable")
    return paths


def _approval_lineage(root: Path, change: str, approval: dict[str, Any] | None
                      ) -> list[dict[str, Any]]:
    prior_id = (approval or {}).get("subject", {}).get("prior_approval")
    if not prior_id:
        return []
    approvals = {}
    for line in effective_event_lines((root / ".harness/events.jsonl").read_text(
        encoding="utf-8",
    ).splitlines()):
        try:
            event = parse_event_line(line)
        except EventSchemaError:
            continue  # Match the reducer's legacy tolerance; never infer approval from a skip.
        if event.change_id == change and event.type == "plan_approved":
            value = event.payload.get("approval")
            if isinstance(value, dict):
                checked = validate_approval(value, change_id=change)
                approvals[checked["approval_id"]] = checked
    result, seen = [], {(approval or {}).get("approval_id")}
    while prior_id:
        if prior_id in seen or prior_id not in approvals:
            raise KnowledgeError("referenced prior approval missing or cyclic")
        seen.add(prior_id)
        prior = approvals[prior_id]
        result.append(prior)
        prior_id = prior["subject"].get("prior_approval")
    return result


def project_context(root: Path, change: str) -> dict[str, Any]:
    """Read current authority and historical grounds, without creating supply."""
    validate_slug(change)
    root = root.resolve()
    state = derive_state(root / ".harness/events.jsonl").get(change)
    if state is None:
        raise KnowledgeError("unknown Change", code="entry_unbound")
    knowledge = report(root, change)
    policy = load_policy(root)
    ledger, _ = load_ledger(root / ".harness/events.jsonl", policy)
    approval = validate_approval(state.effective_approval, change_id=change) if (
        state.effective_approval is not None
    ) else None
    decisions, errors = load_decisions(root)
    problems = [f"decision unavailable: {e}" for e in errors]
    declarations, declaration_errors = _project_statements(root, change, ledger)
    problems.extend(declaration_errors)
    conventions = []
    for decision in sorted(decisions, key=lambda d: d.id):
        if decision.status != "ratified":
            continue
        if compute_body_hash(decision.body) != decision.ratified_text_hash:
            problems.append(f"ratified decision text drift: {decision.id}")
        conventions.append({
            "id": decision.id, "version": decision.ratified_text_hash,
            "body": decision.body, "ratified_by": decision.ratified_by,
            "ratified_at": decision.ratified_at,
            "source": decision.path.relative_to(root).as_posix() if decision.path else None,
            "source_digest": sha256(decision.path.read_bytes()).hexdigest()
            if decision.path else None,
        })
    identity = {
        "root": root.as_posix(), "change_id": change,
        "current_state": state.current_state,
        "product_id": knowledge.get("product_id"),
        "repository_id": knowledge.get("repository_id"),
        "head": resolve_commit(root), "trusted_base": resolve_contract_base(root),
    }
    current = {key: knowledge.get(key) for key in (
        "coverage", "basis_digest", "context", "constraints", "evaluated",
        "recognition_evidence", "impacts", "challenges", "blocking_reasons", "limits",
    )}
    authority = {
        "identity": identity, "authorization": approval,
        "authorization_lineage": _approval_lineage(root, change, approval),
        "policy_digest": policy["policy_digest"] if policy else None,
        "pending_revision": state.pending_revision,
        "conventions": conventions, "knowledge": current, "problems": problems,
    }
    # Observation/delivery appends are intentionally excluded from this fingerprint.
    authority_digest = digest_record(authority)
    history: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
    for delivery_id, delivery in ledger["deliveries"].items():
        if delivery["change_id"] != change:
            continue
        context = delivery["context"]
        for version in delivery["constraints"]:
            key = (version["version_digest"], context.get("approval_id"),
                   context.get("plan_subject_id"))
            if key not in history:
                history[key] = {
                    "version": version, "approval_id": key[1], "plan_subject_id": key[2],
                    "first_delivery_id": delivery_id, "delivery_count": 0,
                }
            history[key]["latest_delivery_id"] = delivery_id
            history[key]["delivery_count"] += 1
    return {
        "schema_version": SCHEMA, **authority, "authority_digest": authority_digest,
        "recovery": {"supplied": list(history.values()),
                     "unresolved_declarations": [d["statement_id"] for d in declarations
                                                 if d["status"] == "unresolved"],
                     "detail": "knowledge show retains every exact historical delivery/context"},
        "trace": {
            "project_statements": declarations,
            "statements": knowledge.get("statements", [])[-10:],
            "statement_count": len(knowledge.get("statements", [])),
            "acquisition_coverage": knowledge.get("acquisition_coverage", [])[-10:],
            "observation_ids": [o.get("tool_use_id", o.get("delivery_id"))
                                for o in knowledge.get("observations", [])[-10:]],
            "observation_count": len(knowledge.get("observations", [])),
            "detail": "knowledge show retains native knowledge trace; project declarations "
                      "retain original entry/manifest locators and do not grant authority",
            "missing": knowledge.get("missing_observations", []),
        },
        "supply_status": "not_supplied", "acquisition_status": "not_observed",
    }
