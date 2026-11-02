"""Versioned, derived knowledge exports. Original native events remain untouched.

The v2 reader replays ordered operations, resolving deliveries from retained
versions/conclusions. Git baselines supply history; this is not a second ledger
or an authority source. Only the native observer can create acquisitions.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

from keepsail.core.approval import canonical_json, digest_record
from keepsail.core.events import parse_event_line
from keepsail.core.knowledge import (
    EVENT_TYPES,
    _empty,
    _need,
    _replay_operation,
    _unique_pairs,
    _view,
)

SCHEMA = "knowledge-checkpoint/v2"
FACT = "retained-knowledge-operation/v2"
ACQUISITION = "retained-acquisition/v2"
SOURCE = "retained-evidence-source/v1"
BRIDGE = "legacy-bootstrap-operation/v1"
HOST_LOCATORS = frozenset({"thread_id", "session_id", "root_turn_id", "tool_use_id",
                           "question_call_id"})
BaselineResult = tuple[list[dict[str, Any]], list[dict[str, str]]]


def _alias(kind: str, value: Any) -> Any:
    return kind + ":" + sha256(str(value).encode()).hexdigest() if value is not None else None


def retained_source(original: Any) -> Any:
    """Retain a conclusion's content without publishing its host locator bytes.

    Only explicit root-level source metadata is projected. The native evidence
    stays untouched; this envelope identifies the derived bytes and original
    source digest, rather than claiming to reproduce the original JSON.
    """
    if not isinstance(original, dict):
        return original
    if original.get("schema_version") == SOURCE:
        _need(set(original) == {"schema_version", "representation", "source_digest",
                                "content", "host_locators"}
              and original.get("representation") == "derived-not-original-source-json"
              and isinstance(original.get("content"), dict)
              and isinstance(original.get("host_locators"), dict)
              and set(original["host_locators"]).issubset(HOST_LOCATORS)
              and bool(original["host_locators"])
              and not HOST_LOCATORS.intersection(original["content"]),
              "invalid retained evidence source")
        for digest in [original.get("source_digest"), *original["host_locators"].values()]:
            _need(isinstance(digest, str) and len(digest) == 64
                  and all(c in "0123456789abcdef" for c in digest),
                  "invalid retained source digest or logical locator")
        return deepcopy(original)
    locators = {k: digest_record(v) for k, v in original.items() if k in HOST_LOCATORS}
    if not locators:
        return deepcopy(original)
    return {"schema_version": SOURCE, "representation": "derived-not-original-source-json",
            "source_digest": digest_record(original),
            "content": {k: deepcopy(v) for k, v in original.items() if k not in HOST_LOCATORS},
            "host_locators": locators}


def host_locators(events: list[dict[str, Any]]) -> dict[str, str]:
    """Identify actual host values from owned metadata, never from body heuristics."""
    result = {}
    for event in events:
        request = event.get("payload", {}).get("request", {})
        source = request.get("evidence", {}).get("original_evidence", {})
        record = request.get("record", {})
        for metadata in (source, record, *record.get("pages", [])):
            if isinstance(metadata, dict):
                for key in HOST_LOCATORS.intersection(metadata):
                    value = metadata[key]
                    if isinstance(value, str) and value:
                        result[value] = "host-locator:" + digest_record(value)
    return result


def compact_facts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Interpret each operation with its own prefix, never with future metadata."""
    locators: dict[str, str] = {}
    result = []
    for raw in events:
        locators.update(host_locators([raw]))
        result.append(compact_fact(raw, locators=locators))
    return result


def compact_fact(raw: dict[str, Any], *, locators: dict[str, str] | None = None) -> dict[str, Any]:
    """Convert a validated native operation, never label the new bytes original."""
    event = parse_event_line(canonical_json(raw))
    _need(event.type in EVENT_TYPES, "unsupported retained operation")
    identity = raw.get("framework_state") or {}
    bridged = isinstance(identity, dict) and identity.get("schema_version") == BRIDGE
    payload = deepcopy(event.payload)
    result = payload.pop("result")
    request = payload["request"]
    request.pop("expected_revision", None)
    if isinstance(request.get("evidence"), dict):
        evidence = request["evidence"]
        evidence["original_evidence"] = retained_source(evidence["original_evidence"])
    record = request.get("record", {})
    if record.get("kind") in {"statement", "challenge"} and isinstance(record.get("reason"), str):
        original_reason = reason = record["reason"]
        for value, reference in (locators or {}).items():
            reason = re.sub(r"(?<![\w-])" + re.escape(value) + r"(?![\w-])", reference, reason)
        if reason != original_reason:
            record["reason"] = reason
            record["reason_projection"] = {"schema_version": "retained-statement-reason/v1",
                                            "source_digest": digest_record(original_reason)}
    if not bridged and record.get("kind") in {
        "acquisition", "context-acquisition", "statement", "emitted",
    }:
        for field in ("session_id", "root_turn_id", "tool_use_id"):
            if field in record:
                record[field] = _alias(field, record[field])
        for page in record.get("pages", []):
            for field in ("root_turn_id", "tool_use_id"):
                if field in page:
                    page[field] = _alias(field, page[field])
    if record.get("kind") == "acquisition" and record.get("schema_version") is None:
        # v1's accepted fact is retained, with its original trust ceiling. It is
        # neither a replay of the callback nor a newly observed v2 acquisition.
        receipt = record.pop("original_receipt")
        record["schema_version"] = ACQUISITION
        record["source_receipt_digest"] = digest_record(receipt)
        record["source_event_digest"] = digest_record(raw)
        record["limits"] = ["accepted-v1-fact", "original-return-bytes-not-published",
                            "not-understanding-or-compliance"]
    delivery = request.get("delivery")
    if delivery is not None:
        # A delivery result repeats the exact recognition conclusions. Its
        # digest describes the same explicit derived source representation as
        # the replayed delivery, while source_event_digest still binds raw input.
        for evidence in result.get("recognition_evidence", {}).values():
            evidence["original_evidence"] = retained_source(evidence["original_evidence"])
        delivery["constraints"] = [v["version_digest"] for v in delivery["constraints"]]
        delivery["recognition_evidence"] = {
            version: evidence["evidence_id"]
            for version, evidence in delivery["recognition_evidence"].items()
        }
    source_id, source_digest = event.event_id, digest_record(raw)
    if bridged:
        _need(set(identity) == {"schema_version", "representation", "source_event_id",
                                "source_event_digest"}
              and identity["representation"] == "derived-not-original-event-bytes",
              "invalid legacy bridge source")
        source_id, source_digest = identity["source_event_id"], identity["source_event_digest"]
        _need(isinstance(source_id, str) and bool(source_id)
              and isinstance(source_digest, str) and len(source_digest) == 64
              and all(c in "0123456789abcdef" for c in source_digest),
              "invalid legacy bridge identity")
    fact = {
        "schema_version": FACT, "source_event_id": source_id,
        "source_event_digest": source_digest, "event_type": event.type,
        "change_id": event.change_id, "payload": payload,
        "result_digest": digest_record(result),
    }
    if bridged:
        _need(event.event_id == "derived-" + digest_record([event.change_id, fact]),
              "legacy bridge event does not bind its derived content")
    return fact


def _replay_fact(ledger: dict[str, Any], fact: dict[str, Any], policy: dict[str, Any]) -> None:
    _need(set(fact) == {"schema_version", "source_event_id", "source_event_digest", "event_type",
                        "change_id", "payload", "result_digest"}
          and fact["schema_version"] == FACT, "unsupported retained fact format")
    _need(isinstance(fact["source_event_id"], str) and fact["source_event_id"],
          "retained fact lacks source identity")
    for field in ("source_event_digest", "result_digest"):
        _need(isinstance(fact[field], str) and len(fact[field]) == 64
              and all(c in "0123456789abcdef" for c in fact[field]), "invalid fact digest")
    payload = deepcopy(fact["payload"])
    _need(payload.get("policy_digest") == policy["policy_digest"], "retained fact policy mismatch")
    request = payload["request"]
    _need(request.get("change_id") == fact["change_id"]
          and "expected_revision" not in request, "invalid derived request binding")
    # The pure operation validator requires a revision field. This explicit
    # derived marker never goes to the native CAS writer or claims a log prefix.
    request["expected_revision"] = "derived:" + digest_record(fact)
    if isinstance(request.get("evidence"), dict):
        evidence = request["evidence"]
        evidence["original_evidence"] = retained_source(evidence["original_evidence"])
    delivery = request.get("delivery")
    if delivery is not None:
        delivery["constraints"] = [ledger["versions"][v] for v in delivery["constraints"]]
        delivery["recognition_evidence"] = {
            version: ledger["evidence"][eid]
            for version, eid in delivery["recognition_evidence"].items()
        }
    record = request.get("record", {})
    if record.get("schema_version") == ACQUISITION:
        retained_type = fact["event_type"]
        if retained_type == "knowledge_operation_v2":
            _need(payload.get("minimum_reader") == "knowledge-trigger/v2"
                  and payload.get("operation_type") == "knowledge_recorded"
                  and payload.get("trigger_contexts") == {}
                  and payload.get("trigger_snapshots") == [],
                  "retained acquisition cannot change trigger semantics")
            retained_type = payload["operation_type"]
        _need(retained_type == "knowledge_recorded" and record.get("kind") == "acquisition",
              "retained acquisition on wrong operation")
        _need(record.get("producer") in policy["observation_issuers"],
              "retained acquisition has unrecognized producer")
        supplied = ledger["deliveries"].get(record.get("delivery_id"), {})
        version = ledger["versions"].get(record.get("version_digest"), {})
        _need(supplied.get("change_id") == fact["change_id"] and version
              and version in supplied.get("constraints", [])
              and record.get("returned_content_digest") == sha256(
                  version["body"].encode()).hexdigest()
              and record.get("source_event_digest") == fact["source_event_digest"]
              and isinstance(record.get("source_receipt_digest"), str)
              and len(record["source_receipt_digest"]) == 64
              and record.get("limits") == ["accepted-v1-fact",
                                           "original-return-bytes-not-published",
                                           "not-understanding-or-compliance"]
              and "original_receipt" not in record,
              "retained acquisition relationship mismatch")
        op = request["operation_id"]
        _need(op not in ledger["operations"], "duplicate retained operation")
        result = {"record_id": op, "kind": "acquisition", "recorded": True}
        ledger["observations"].append({**record, "change_id": fact["change_id"]})
        ledger["operations"][op] = {"request": request, "result": result}
    else:
        result = _replay_operation(ledger, fact["event_type"], payload, policy)
    _need(digest_record(result) == fact["result_digest"], "retained operation result mismatch")


def replay_facts(facts: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    ledger = _empty()
    seen = set()
    for fact in facts:
        _need(fact["source_event_id"] not in seen, "duplicate retained source event")
        seen.add(fact["source_event_id"])
        _replay_fact(ledger, fact, policy)
    return ledger


def _git(root: Path, *args: str) -> str:
    # A missing local object must fail, including in a partial clone. Disallow
    # every fetch transport rather than relying on the user's remote settings.
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "GIT_ALLOW_PROTOCOL": "", "GIT_NO_LAZY_FETCH": "1",
             "GIT_TERMINAL_PROMPT": "0"},
    )
    _need(result.returncode == 0, "local Git checkpoint object unavailable")
    return result.stdout


def _checkpoints(text: str) -> list[dict[str, Any]]:
    result = []
    for line in text.splitlines():
        if not line.strip():
            continue
        raw = json.loads(line, object_pairs_hook=_unique_pairs)
        if raw.get("schema_version") == "attestation/v2":
            from keepsail.core.attestation_format import expand_attestation
            expand_attestation(raw)
            result.append(raw["knowledge_checkpoint"])
        elif raw.get("type") == "knowledge_checkpointed":
            result.append(raw["payload"])
    return result


def baseline(root: Path, commit: str, policy: dict[str, Any], *,
             stack: frozenset[str] = frozenset(),
             _memo: dict[str, BaselineResult] | None = None,
             ) -> BaselineResult:
    _need(commit not in stack, "cyclic checkpoint baseline")
    # Only this closure traversal shares validated immutable commits. A later
    # action must read its own Git inputs; the active stack still detects cycles.
    memo = {} if _memo is None else _memo
    if commit in memo:
        return memo[commit]
    resolved = _git(root, "rev-parse", "--verify", commit + "^{commit}").strip()
    _need(resolved == commit, "checkpoint baseline requires a full immutable commit")
    paths = _git(root, "ls-tree", "-rz", "--name-only", commit).split("\0")
    facts: list[dict[str, Any]] = []
    indexed: dict[str, dict[str, Any]] = {}
    refs = []
    for path in sorted(p for p in paths if p.startswith(".harness/attestations/")
                       and p.endswith(".jsonl")):
        for payload in _checkpoints(_git(root, "show", f"{commit}:{path}")):
            available = resolve_facts(root, payload, policy, stack=stack | {commit}, _memo=memo)
            refs.append({"path": path, "digest": payload["digest"]})
            for fact in available:
                identifier = fact["source_event_id"]
                if identifier in indexed:
                    _need(indexed[identifier] == fact, "conflicting historical knowledge fact")
                else:
                    facts.append(fact)
                    indexed[identifier] = fact
    # Reject a mutually inconsistent union, even when each checkpoint is valid.
    replay_facts(facts, policy)
    memo[commit] = facts, refs
    return memo[commit]


def resolve_facts(root: Path, payload: dict[str, Any], policy: dict[str, Any], *,
                  stack: frozenset[str] = frozenset(),
                  _memo: dict[str, BaselineResult] | None = None) -> list[dict[str, Any]]:
    _need(payload.get("digest") == digest_record({k: v for k, v in payload.items()
                                                 if k != "digest"}),
          "knowledge checkpoint digest mismatch")
    if payload.get("schema_version") == "knowledge-checkpoint/v1":
        _need(payload.get("policy") == policy, "historical checkpoint policy mismatch")
        ledger = _empty()
        for raw in payload["events"]:
            event = parse_event_line(canonical_json(raw))
            _need(event.type in EVENT_TYPES and event.payload.get("policy_digest")
                  == policy["policy_digest"], "invalid historical knowledge event")
            result = _replay_operation(ledger, event.type, event.payload, policy)
            _need(result == event.payload.get("result"), "historical knowledge result mismatch")
        facts = compact_facts(payload["events"])
        replay_facts(facts, policy)
        return facts
    _need(set(payload) == {"schema_version", "representation", "policy_digest", "baseline",
                           "delta", "contexts", "expected_view_digest", "digest"}
          and payload.get("schema_version") == SCHEMA
          and payload.get("representation") == "derived-not-original-event-bytes"
          and payload.get("policy_digest") == policy["policy_digest"],
          "unsupported knowledge checkpoint representation")
    binding = payload["baseline"]
    _need(set(binding) == {"commit", "checkpoints"}, "invalid checkpoint baseline binding")
    facts, refs = baseline(root, binding["commit"], policy, stack=stack, _memo=_memo)
    _need(refs == binding["checkpoints"], "checkpoint baseline closure mismatch")
    _need(isinstance(payload["delta"], list), "checkpoint delta must be a list")
    _need(isinstance(payload["contexts"], dict), "checkpoint contexts must be an object")
    combined = facts + decode_delta(payload["delta"], payload["contexts"])
    replay_facts(combined, policy)
    return combined


def view_digest(view: dict[str, Any]) -> str:
    normative = deepcopy({k: view[k] for k in ("basis_digest", "constraints", "impacts")})
    for impact in normative["impacts"]:
        evidence = impact.get("disposition")
        if isinstance(evidence, dict):
            evidence["original_evidence"] = retained_source(evidence["original_evidence"])
    return digest_record(normative)


def _fact_contexts(fact: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    """Only the owned context fields, never arbitrary input/evidence JSON."""
    payload = fact["payload"]
    result = [(payload, "approval_context")] if "approval_context" in payload else []
    delivery = payload["request"].get("delivery")
    if delivery is not None:
        result.append((delivery, "context"))
    contexts = payload.get("trigger_contexts", {})
    result.extend((contexts, key) for key in contexts)
    result.extend((snapshot, "context") for snapshot in payload.get("trigger_snapshots", []))
    return result


def encode_delta(facts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    encoded = deepcopy(facts)
    contexts = {}
    for fact in encoded:
        for container, key in _fact_contexts(fact):
            value = container[key]
            digest = digest_record(value)
            contexts[digest] = value
            container[key] = {"$knowledge_context": digest}
    return encoded, contexts


def decode_delta(facts: list[dict[str, Any]], contexts: dict[str, Any]) -> list[dict[str, Any]]:
    decoded = deepcopy(facts)
    used = set()
    for fact in decoded:
        for container, key in _fact_contexts(fact):
            ref = container[key]
            _need(isinstance(ref, dict) and set(ref) == {"$knowledge_context"},
                  "delivery context requires a versioned local reference")
            digest = ref["$knowledge_context"]
            value = contexts.get(digest)
            _need(value is not None and digest_record(value) == digest,
                  "missing or changed retained context")
            used.add(digest)
            container[key] = value
    _need(used == set(contexts), "unreferenced retained context")
    return decoded


def make_checkpoint(root: Path, change: str, inputs: Any, base: str) -> dict[str, Any]:
    from keepsail.core.knowledge import report

    policy = inputs.policy
    _need(policy is not None, "no activated knowledge policy")
    previous, refs = baseline(root, base, policy)
    indexed = {f["source_event_id"]: f for f in previous}
    current = compact_facts(inputs.ledger["events"])
    current_by_id = {f["source_event_id"]: f for f in current}
    _need(all(current_by_id.get(identifier) == fact for identifier, fact in indexed.items()),
          "live knowledge omits or changes trusted baseline facts")
    delta = [fact for fact in current if fact["source_event_id"] not in indexed]
    replayed = replay_facts(previous + delta, policy)
    state = inputs.states[change]
    from keepsail.core.knowledge import _context
    expected = report(root, change, inputs=inputs)
    verified = (state.current_code_subject or {}).get("subject_id") if (
        state.current_state == "READY_TO_MERGE"
        and (state.current_verification or {}).get("outcome") == "passed"
    ) else None
    rebuilt = _view(replayed, policy, change, _context(state), verified)
    _need(view_digest(rebuilt) == view_digest(expected),
          "derived knowledge changed normative facts")
    encoded, contexts = encode_delta(delta)
    record = {
        "schema_version": SCHEMA, "representation": "derived-not-original-event-bytes",
        "policy_digest": policy["policy_digest"],
        "baseline": {"commit": base, "checkpoints": refs}, "delta": encoded,
        "contexts": contexts,
        "expected_view_digest": view_digest(expected),
    }
    return {**record, "digest": digest_record(record)}


def legacy_bootstrap_checkpoint(root: Path, change: str, inputs: Any, base: str) -> dict[str, Any]:
    """One reader-first release; preserve trusted v1 bytes and derive new v1-readable facts.

    This cannot represent a task's context-acquisition acceptance. It is limited
    to an exact empty finite set without impacts or target observations; other
    tasks' acquisition telemetry stays native and is delivered by their own v2
    export. Normative operations and all trusted original facts remain intact.
    """
    from keepsail.core.knowledge import _context, report

    policy = inputs.policy
    _need(policy is not None, "bootstrap requires the existing trusted knowledge policy")
    expected = report(root, change, inputs=inputs)
    _need(not expected["constraints"] and not expected["impacts"],
          "legacy bootstrap requires an exact empty finite set without impacts")
    ledger = inputs.ledger
    _need(not any(o.get("change_id") == change for o in ledger["observations"])
          and not any(o.get("change_id") == change
                      for o in ledger["context_observations"].values()),
          "legacy bootstrap cannot represent target acquisition observations")
    trusted: dict[str, dict[str, Any]] = {}
    paths = _git(root, "ls-tree", "-rz", "--name-only", base).split("\0")
    for path in sorted(p for p in paths if p.startswith(".harness/attestations/")
                       and p.endswith(".jsonl")):
        for payload in _checkpoints(_git(root, "show", f"{base}:{path}")):
            _need(payload.get("schema_version") == "knowledge-checkpoint/v1",
                  "legacy bootstrap requires a pre-v2 trusted base")
            resolve_facts(root, payload, policy)  # Validate original operations before reuse.
            for raw in payload["events"]:
                old = trusted.setdefault(raw["event_id"], raw)
                _need(old == raw, "conflicting trusted bootstrap history")
    replayed, events, seen, locators = _empty(), [], set(), {}
    for raw in ledger["events"]:
        locators.update(host_locators([raw]))
        if raw["event_id"] in trusted:
            _need(trusted[raw["event_id"]] == raw, "native bootstrap changed trusted history")
            event = deepcopy(raw)
            seen.add(raw["event_id"])
            result = _replay_operation(replayed, raw["type"], event["payload"], policy)
            _need(result == event["payload"]["result"], "trusted bootstrap result mismatch")
        else:
            record = raw["payload"]["request"].get("record", {})
            if record.get("kind") in {"acquisition", "context-acquisition"}:
                continue  # Explicitly outside this bootstrap's empty acquisition scope.
            fact = compact_fact(raw, locators=locators)
            payload = deepcopy(fact["payload"])
            payload["request"]["expected_revision"] = raw["payload"]["request"]["expected_revision"]
            delivery = payload["request"].get("delivery")
            if delivery is not None:
                delivery["constraints"] = [replayed["versions"][v]
                                           for v in delivery["constraints"]]
                delivery["recognition_evidence"] = {
                    v: replayed["evidence"][eid]
                    for v, eid in delivery["recognition_evidence"].items()}
            payload["result"] = _replay_operation(replayed, raw["type"], payload, policy)
            identifier = "derived-" + digest_record([raw["change_id"], fact])
            event = {**deepcopy(raw), "event_id": identifier,
                     "payload": payload, "framework_state": {
                         "schema_version": BRIDGE,
                         "representation": "derived-not-original-event-bytes",
                         "source_event_id": fact["source_event_id"],
                         "source_event_digest": fact["source_event_digest"]}}
        events.append(event)
    _need(seen == set(trusted), "native bootstrap omits trusted knowledge history")
    state = inputs.states[change]
    verified = (state.current_code_subject or {}).get("subject_id") if (
        state.current_state == "READY_TO_MERGE"
        and (state.current_verification or {}).get("outcome") == "passed") else None
    view = _view(replayed, policy, change, _context(state), verified)
    _need(view_digest(view) == view_digest(expected), "bootstrap changed normative knowledge")
    record = {"schema_version": "knowledge-checkpoint/v1",
              "representation": "legacy-bootstrap-derived-not-original-event-bytes",
              "policy": policy, "events": events, "view": view,
              "source_revision": inputs.revision}
    return {**record, "digest": digest_record(record)}
