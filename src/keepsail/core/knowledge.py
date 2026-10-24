"""Explicit, versioned product constraints. The event log is the only authority.

This module deliberately does not retrieve semantic context or execute reviewers.
Its public seam is report/prepare/validate_event; callers share the same predicates.
"""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from keepsail.core.approval import (
    ApprovalError,
    canonical_json,
    digest_record,
    load_json_record,
    resolve_contract_base,
)
from keepsail.core.events import KNOWLEDGE_EVENT_TYPES, Event, parse_event_line
from keepsail.core.scope_match import GitScopeError, covered_by_scope, file_text_at_commit

PROTOCOL = "knowledge-operation/v1"
POLICY_PATH = ".harness/knowledge-recognition.yaml"
EVENT_TYPES = KNOWLEDGE_EVENT_TYPES
PREREQUISITES = frozenset(
    {
        "plan_ready",
        "implementation_started",
        "implementation_complete",
        "code_review_passed",
        "merged",
    }
)


class KnowledgeError(ApprovalError):
    """Invalid knowledge evidence or an unmet obligation."""

    def __init__(self, message: str, *, code: str = "knowledge_invalid", exit_code: int = 2):
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.data: dict[str, Any] = {}


def _need(condition: object, message: str) -> None:
    if not condition:
        raise KnowledgeError(message)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(v) for v in value)


def _path(value: str) -> str:
    p = PurePosixPath(value)
    _need(
        value
        and "\\" not in value
        and not p.is_absolute()
        and ".." not in p.parts
        and ":" not in value
        and not any(c in value for c in "*?[]")
        and str(p) not in {".", ""},
        "paths must be relative segment prefixes, not globs",
    )
    return str(p).rstrip("/")


def read_record(root: Path, raw: str) -> dict[str, Any]:
    """Only explicitly supplied files inside this workspace may be retained."""
    path = (root / raw).resolve()
    _need(path.is_relative_to(root.resolve()), "record path escapes workspace")
    record = load_json_record(path)
    # Preserve byte evidence separately from canonical subject identity.
    record["_input_digest"] = sha256(path.read_bytes()).hexdigest()
    return record


def policy_digest(policy: dict[str, Any]) -> str:
    return digest_record({k: v for k, v in policy.items() if k != "policy_digest"})


def validate_policy(raw: object) -> dict[str, Any]:
    _need(isinstance(raw, dict), "knowledge policy must be a mapping")
    assert isinstance(raw, dict)
    _need(
        set(raw)
        <= {
            "version",
            "enabled",
            "product_id",
            "repository_id",
            "minimum_reader",
            "owner_activation",
            "human_issuers",
            "observation_issuers",
            "processes",
            "policy_digest",
        },
        "unsupported knowledge policy requirement",
    )
    _need(
        raw.get("version") == "knowledge-recognition/v1" and raw.get("enabled") is True,
        "knowledge policy must explicitly enable protocol v1",
    )
    for key in ("product_id", "repository_id"):
        _need(_text(raw.get(key)), f"knowledge policy needs {key}")
    _need(raw.get("minimum_reader") == PROTOCOL, "unsupported minimum knowledge reader")
    owner = raw.get("owner_activation")
    _need(
        isinstance(owner, dict)
        and owner.get("decision") == "activate"
        and all(_text(owner.get(k)) for k in ("id", "source", "by")),
        "knowledge activation requires retained owner authorization",
    )
    _need(_strings(raw.get("human_issuers")), "knowledge policy needs human issuers")
    processes = raw.get("processes")
    _need(isinstance(processes, list) and processes, "knowledge policy needs recognized processes")
    assert isinstance(processes, list)
    for process in processes:
        _need(
            isinstance(process, dict)
            and all(_text(process.get(k)) for k in ("id", "version"))
            and _strings(process.get("issuers"))
            and _strings(process.get("kinds")),
            "invalid recognized knowledge process",
        )
        _need(
            set(process["kinds"]) <= {"recognition", "applicability", "disposition"},
            "unsupported knowledge process kind",
        )
    _need(raw.get("policy_digest") == policy_digest(raw), "knowledge policy digest mismatch")
    return dict(raw)


@lru_cache(maxsize=128)
def _policy_at_commit(root: Path, commit: str) -> dict[str, Any] | None:
    """Only immutable Git objects are cached; mutable policy files are always reread."""
    from keepsail.core.scope_match import tracked_files_at_commit

    if POLICY_PATH not in tracked_files_at_commit(root, commit):
        return None
    return _configured_policy(yaml.safe_load(file_text_at_commit(root, commit, POLICY_PATH)))


def _configured_policy(raw: object) -> dict[str, Any]:
    try:
        return validate_policy(raw)
    except KnowledgeError as exc:
        raise KnowledgeError(str(exc), code="knowledge_config_invalid", exit_code=3) from exc


def policy_configuration(
    root: Path, *, ref: str | None = None, candidate_ref: str | None = None
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Resolve effective authority separately from a validated delivery candidate.

    Explicit Git inputs never read the mutable worktree. A first candidate may
    be delivered normally, but only the trusted base can enable the protocol.
    """
    try:
        from keepsail.core.scope_match import resolve_commit

        current = None
        if candidate_ref is not None:
            current = _policy_at_commit(root.resolve(), resolve_commit(root, candidate_ref))
        elif ref is None:
            try:
                text = (root / POLICY_PATH).read_text(encoding="utf-8")
            except FileNotFoundError:
                pass
            else:
                current = _configured_policy(yaml.safe_load(text))
        if (ref is None and candidate_ref is None and current is None
                and not any((p / ".git").exists() for p in (root, *root.parents))):
            return None, None
        base = resolve_commit(root, ref) if ref else resolve_contract_base(root)
        trusted = _policy_at_commit(root.resolve(), base)
        if trusted is None:
            return None, deepcopy(current)
        if ref is None or candidate_ref is not None:
            if current is None:
                raise KnowledgeError("activated knowledge policy is missing", exit_code=3)
            _need(current == trusted, "candidate cannot replace the trusted knowledge policy")
        return deepcopy(trusted), None
    except KnowledgeError:
        raise
    except (GitScopeError, ApprovalError) as exc:
        raise KnowledgeError(str(exc), exit_code=4) from exc
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise KnowledgeError(f"knowledge configuration unreadable: {exc}", exit_code=3) from exc


def load_policy(root: Path, *, ref: str | None = None) -> dict[str, Any] | None:
    """Load trusted authority; a validated first candidate has none."""
    return policy_configuration(root, ref=ref)[0]


def version_record(raw: object, policy: dict[str, Any]) -> dict[str, Any]:
    _need(isinstance(raw, dict), "knowledge version must be an object")
    assert isinstance(raw, dict)
    required = {
        "product_id",
        "knowledge_id",
        "body",
        "rationale",
        "sources",
        "selector",
        "authority",
        "previous_version",
        "schema_version",
    }
    _need(set(raw) == required, "knowledge version has missing or unknown fields")
    _need(raw["schema_version"] == "knowledge-version/v1", "unsupported knowledge version")
    _need(raw["product_id"] == policy["product_id"], "knowledge belongs to another product")
    for key in ("knowledge_id", "body", "rationale"):
        _need(_text(raw[key]), f"knowledge version needs {key}")
    _need(
        isinstance(raw["authority"], str) and raw["authority"] in {"guidance", "constraint"},
        "invalid knowledge authority",
    )
    _need(raw["previous_version"] is None or _text(raw["previous_version"]), "invalid predecessor")
    sources = raw["sources"]
    _need(isinstance(sources, list) and sources, "knowledge needs retained sources")
    for source in sources:
        _need(
            isinstance(source, dict)
            and _text(source.get("origin"))
            and _text(source.get("content")),
            "sources need origin and retained content",
        )
    selector = raw["selector"]
    _need(isinstance(selector, dict) and selector, "knowledge needs an explicit selector")
    if "global" in selector:
        _need(selector == {"global": True}, "global must be true and exclusive")
    else:
        _need(set(selector) <= {"repository_ids", "change_ids", "paths"}, "unknown selector")
        for key, values in selector.items():
            _need(_strings(values), f"selector {key} needs nonempty strings")
            if key == "paths":
                for value in values:
                    _path(value)
    result = deepcopy(raw)
    result["version_digest"] = digest_record(raw)
    return result


def _evidence(raw: object, policy: dict[str, Any]) -> dict[str, Any]:
    _need(isinstance(raw, dict), "knowledge conclusion must be an object")
    assert isinstance(raw, dict)
    for key in ("evidence_id", "kind", "subject_id", "decision", "issuer"):
        _need(_text(raw.get(key)), f"conclusion needs {key}")
    _need(raw.get("schema_version") == "knowledge-evidence/v1", "unsupported knowledge evidence")
    _need(
        raw.get("original_evidence") and isinstance(raw.get("provenance"), dict),
        "conclusion needs original evidence and provenance",
    )
    _need(
        raw["provenance"].get("policy_digest") == policy["policy_digest"],
        "conclusion names another recognition policy",
    )
    _need(
        raw.get("authorization_effect") in {"unchanged", "requires-human-authorization"},
        "conclusion must explicitly classify its authorization effect",
    )
    recognized = any(
        raw.get("process") == {"id": p["id"], "version": p["version"]}
        and raw["kind"] in p["kinds"]
        and raw["issuer"] in p["issuers"]
        for p in policy["processes"]
    )
    _need(recognized, "conclusion is not from a recognized process")
    if raw["authorization_effect"] == "requires-human-authorization":
        _need(
            raw["issuer"] in policy["human_issuers"] and raw.get("human_authorization"),
            "authority/risk changes require owner evidence",
        )
    return deepcopy(raw)


def _empty() -> dict[str, Any]:
    return {
        "versions": {},
        "current": {},
        "states": {},
        "recognitions": {},
        "evidence": {},
        "deliveries": {},
        "statements": [],
        "observations": [],
        "challenges": {},
        "dispositions": {},
        "executions": {},
        "applicability": {},
        "impact_approvals": {},
        "operations": {},
        "events": [],
    }


def load_ledger(path: Path, policy: dict[str, Any] | None) -> tuple[dict[str, Any], str]:
    """Strict new-protocol replay; unrelated historic unknown types remain visible elsewhere."""
    ledger = _empty()
    if policy and not path.exists():
        raise KnowledgeError(
            "knowledge_corrupt: activated event ledger is missing", code="knowledge_corrupt"
        )
    content = path.read_bytes() if path.exists() else b""
    if policy and content and not content.endswith(b"\n"):
        raise KnowledgeError("knowledge_corrupt: unterminated event log", code="knowledge_corrupt")
    prefix = sha256()
    for number, raw_line in enumerate(content.splitlines(keepends=True), 1):
        prior_revision = prefix.hexdigest()
        prefix.update(raw_line)
        line = raw_line.decode("utf-8")
        if not line.strip():
            continue
        try:
            raw = json.loads(line, object_pairs_hook=_unique_pairs)
            event = parse_event_line(line)
        except (ValueError, TypeError, KeyError) as exc:
            if policy or "knowledge_" in line:
                raise KnowledgeError(
                    f"knowledge_corrupt: event {number}: {exc}", code="knowledge_corrupt"
                ) from exc
            continue
        if event.type.startswith("knowledge_") and event.type not in EVENT_TYPES:
            _need(event.type == "knowledge_checkpointed", "unsupported knowledge event protocol")
        if event.type not in EVENT_TYPES:
            continue
        _need(policy is not None, "knowledge events exist but activation policy is missing")
        assert policy is not None
        _need(
            event.payload.get("policy_digest") == policy["policy_digest"],
            "knowledge event policy mismatch",
        )
        request = event.payload.get("request")
        _need(isinstance(request, dict), "knowledge event lacks its original request")
        assert isinstance(request, dict)
        _need(
            request.get("expected_revision") == prior_revision,
            "knowledge_corrupt: operation was not bound to its log prefix",
        )
        result = _apply(
            ledger, event.type, request, policy, event.payload.get("approval_context", {})
        )
        _need(result == event.payload.get("result"), "knowledge event result was corrupted")
        ledger["events"].append(raw)
    return ledger, sha256(content).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _need(key not in result, f"duplicate key: {key}")
        result[key] = value
    return result


def _operation(request: dict[str, Any]) -> str:
    _need(request.get("schema_version") == PROTOCOL, "unsupported knowledge operation")
    for key in ("operation_id", "expected_revision", "change_id"):
        _need(_text(request.get(key)), f"operation needs {key}")
    return str(request["operation_id"])


def _apply(
    ledger: dict[str, Any],
    event_type: str,
    request: dict[str, Any],
    policy: dict[str, Any],
    approval_context: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    approval_context = approval_context or {}
    _need(
        isinstance(approval_context, dict)
        and all(
            isinstance(k, str) and (v is None or isinstance(v, str))
            for k, v in approval_context.items()
        ),
        "invalid trigger approval context",
    )

    def capture_impact_approval(kid: str, target: str | None = None) -> None:
        linked = {
            d["change_id"]
            for d in ledger["deliveries"].values()
            if any(v["knowledge_id"] == kid for v in d["constraints"])
        }
        if target is not None:
            linked = {target}
        for change_id in linked:
            _need(change_id in approval_context, "trigger omits linked Change approval context")
            ledger["impact_approvals"][(change_id, kid)] = approval_context[change_id]

    op = _operation(request)
    _need(op not in ledger["operations"], "duplicate operation event")
    if event_type == "knowledge_proposed":
        version = version_record(request.get("version"), policy)
        digest, kid = version["version_digest"], version["knowledge_id"]
        _need(digest not in ledger["versions"], "version already proposed")
        _need(version["previous_version"] == ledger["current"].get(kid), "stale predecessor")
        ledger["versions"][digest] = version
        ledger["states"][digest] = "candidate"
        result = {"version_digest": digest, "state": "candidate", "effective": False}
    elif event_type == "knowledge_imported":
        evidence = _evidence(request.get("evidence"), policy)
        eid = evidence["evidence_id"]
        _need(eid not in ledger["evidence"], "evidence ID already imported")
        kind, decision, subject = evidence["kind"], evidence["decision"], evidence["subject_id"]
        if kind == "recognition":
            _need(decision in {"recognize", "reject", "retire"}, "no knowledge conclusion")
            _need(subject in ledger["versions"], "recognition names an unknown version")
            version = ledger["versions"][subject]
            kid = version["knowledge_id"]
            if decision == "recognize":
                _need(ledger["states"][subject] == "candidate", "version is not a candidate")
                previous = ledger["current"].get(kid)
                _need(version["previous_version"] == previous, "recognition has stale predecessor")
                if previous:
                    old = ledger["versions"][previous]
                    if old["authority"] == "constraint" and (
                        version["authority"] != "constraint"
                        or old["selector"] != version["selector"]
                    ):
                        _need(
                            evidence["authorization_effect"] == "requires-human-authorization",
                            "constraint authority/selector changes require owner authorization",
                        )
                    ledger["states"][previous] = "superseded"
                ledger["current"][kid] = subject
                ledger["states"][subject] = "effective"
                ledger["recognitions"][subject] = eid
                capture_impact_approval(kid)
            elif decision == "retire":
                _need(ledger["current"].get(kid) == subject, "cannot retire a noncurrent version")
                if version["authority"] == "constraint":
                    _need(
                        evidence["authorization_effect"] == "requires-human-authorization",
                        "retiring an effective constraint requires owner authorization",
                    )
                del ledger["current"][kid]
                ledger["states"][subject] = "retired"
                capture_impact_approval(kid)
        elif kind == "applicability":
            _need(decision in {"apply", "not_applicable"}, "no applicability conclusion")
            _need(subject in ledger["versions"], "applicability names unknown version")
            _need(_text(evidence.get("target_change_id")), "applicability needs target Change")
            if decision == "not_applicable":
                _need(
                    evidence["authorization_effect"] == "requires-human-authorization",
                    "constraint exclusion requires explicit owner authorization",
                )
            ledger["applicability"][(evidence["target_change_id"], subject)] = eid
            capture_impact_approval(
                ledger["versions"][subject]["knowledge_id"], evidence["target_change_id"]
            )
        elif kind == "disposition":
            _need(
                decision in {"continue", "adjust", "reapprove", "not_applicable"},
                "no impact disposition",
            )
            _need(isinstance(evidence.get("impact"), dict), "disposition needs exact impact")
            impact = evidence["impact"]
            _need(subject == digest_record(impact), "disposition impact digest mismatch")
            _need(
                _text(impact.get("change_id")) and _text(impact.get("basis_digest")),
                "impact needs Change and basis",
            )
            _need(
                evidence.get("use_version") in ledger["versions"] or decision == "not_applicable",
                "disposition must select an exact version",
            )
            if decision != "not_applicable":
                selected = evidence["use_version"]
                _need(
                    selected in ledger["recognitions"]
                    and ledger["versions"][selected]["authority"] == "constraint",
                    "disposition cannot grant candidate or guidance constraint authority",
                )
            if decision in {"adjust", "reapprove"}:
                _need(
                    _strings(evidence.get("obligations")), "adjustment needs explicit obligations"
                )
            if decision == "not_applicable":
                _need(
                    evidence["authorization_effect"] == "requires-human-authorization",
                    "exclusion requires owner authorization",
                )
            _need(subject not in ledger["dispositions"], "impact already has a disposition")
            ledger["dispositions"][subject] = eid
        else:
            raise KnowledgeError("unsupported conclusion kind")
        ledger["evidence"][eid] = evidence
        result = {"evidence_id": eid, "decision": decision, "effective": decision not in {"reject"}}
    elif event_type == "knowledge_delivered":
        delivery = request.get("delivery")
        _need(
            isinstance(delivery, dict) and _text(delivery.get("basis_digest")),
            "delivery needs exact basis",
        )
        assert isinstance(delivery, dict)
        for item in delivery.get("constraints", []):
            _need(
                item == ledger["versions"].get(item.get("version_digest")),
                "delivery version does not match retained content",
            )
            eid = ledger["recognitions"].get(item["version_digest"])
            _need(
                delivery.get("recognition_evidence", {}).get(item["version_digest"])
                == ledger["evidence"].get(eid)
                and eid is not None,
                "delivery must retain exact recognition evidence",
            )
        ledger["deliveries"][op] = deepcopy(delivery)
        result = {"delivery_id": op, "supply_status": "prepared", **deepcopy(delivery)}
    else:
        record = request.get("record")
        _need(isinstance(record, dict), "knowledge record must be an object")
        assert isinstance(record, dict)
        kind = record.get("kind")
        _need(isinstance(kind, str), "knowledge record kind must be a string")
        if kind in {"statement", "challenge", "acquisition", "emitted"}:
            delivery = ledger["deliveries"].get(record.get("delivery_id"))
            _need(
                delivery is not None and delivery["change_id"] == request["change_id"],
                "record needs a delivery for this Change",
            )
            if kind in {"statement", "challenge", "acquisition"}:
                _need(
                    record.get("version_digest")
                    in {v["version_digest"] for v in delivery["constraints"]},
                    "record names a version not supplied in that delivery",
                )
            if kind in {"statement", "challenge"}:
                _need(
                    record.get("decision") in {"adopt", "reject", "challenge"}
                    and _text(record.get("reason")),
                    "statement needs decision and reason",
                )
                ledger["statements"].append({**record, "change_id": request["change_id"]})
                if kind == "challenge" or record["decision"] == "challenge":
                    _need(
                        _strings(record.get("dependent_paths"))
                        or record.get("dependency") == "global",
                        "challenge needs dependencies",
                    )
                    for path in record.get("dependent_paths", []):
                        _path(path)
                    ledger["challenges"][op] = {**record, "change_id": request["change_id"]}
                    capture_impact_approval(
                        ledger["versions"][record["version_digest"]]["knowledge_id"],
                        request["change_id"],
                    )
            elif kind == "acquisition":
                _need(
                    record.get("producer") in policy.get("observation_issuers", [])
                    and record.get("original_receipt")
                    and _text(record.get("returned_content_digest")),
                    "acquisition needs a recognized observer and original receipt",
                )
                body = ledger["versions"][record["version_digest"]]["body"]
                _need(
                    record["returned_content_digest"] == sha256(body.encode("utf-8")).hexdigest(),
                    "acquisition content digest does not match supplied text",
                )
                ledger["observations"].append({**record, "change_id": request["change_id"]})
            else:
                ledger["statements"].append(
                    {
                        **record,
                        "change_id": request["change_id"],
                        "category": "self-reported-output",
                    }
                )
        elif kind == "execution":
            eid = record.get("disposition_id")
            _need(
                eid in ledger["evidence"] and ledger["evidence"][eid]["kind"] == "disposition",
                "execution needs a recognized disposition",
            )
            _need(
                ledger["evidence"][eid]["impact"]["change_id"] == request["change_id"],
                "execution belongs to another Change",
            )
            _need(
                record.get("outcome") in {"reported", "failed", "no-conclusion", "verified"},
                "execution needs explicit outcome",
            )
            _need(record.get("evidence"), "execution needs retained action evidence")
            ledger["executions"][eid] = deepcopy(record)
        else:
            raise KnowledgeError("unsupported knowledge record kind")
        result = {"record_id": op, "kind": kind, "recorded": True}
    ledger["operations"][op] = {"request": deepcopy(request), "result": deepcopy(result)}
    return result


def _matches(version: dict[str, Any], policy: dict[str, Any], change: str, paths: list[str]) -> str:
    selector = version["selector"]
    if selector.get("global"):
        return "matched"
    for key, value in (("repository_ids", policy["repository_id"]), ("change_ids", change)):
        if key in selector and value not in selector[key]:
            return "non_matching"
    if "paths" in selector:
        if not paths:
            return "unknown"
        if not any(covered_by_scope(_path(p), selector["paths"]) for p in paths):
            return "non_matching"
    return "matched"


def _view(
    ledger: dict[str, Any],
    policy: dict[str, Any],
    change: str,
    context: dict[str, Any],
    verified_subject: str | None = None,
) -> dict[str, Any]:
    evaluated, constraints, blockers = [], [], []
    for digest in sorted(ledger["current"].values()):
        version = ledger["versions"][digest]
        match = _matches(version, policy, change, context["paths"])
        relation = "global" if version["selector"].get("global") else "explicit-rule"
        eid = ledger["applicability"].get((change, digest))
        if eid:
            match = "matched" if ledger["evidence"][eid]["decision"] == "apply" else "non_matching"
            relation = "recognized-judgment"
        evaluated.append({"version_digest": digest, "match": match, "relation_source": relation})
        if version["authority"] == "constraint":
            if match == "matched":
                constraints.append(deepcopy(version))
            elif match == "unknown":
                blockers.append(f"unknown applicability: {digest}")
    supplied = [
        dict(v, delivery_id=did)
        for did, d in ledger["deliveries"].items()
        if d["change_id"] == change
        for v in d["constraints"]
    ]
    challenges = {cid: c for cid, c in ledger["challenges"].items() if c["change_id"] == change}
    # A basis excludes observation and disposition telemetry. A disposition cannot
    # invalidate itself, but knowledge, applicability, approval or coverage can.
    basis = digest_record(
        {
            "policy": policy["policy_digest"],
            "context": context,
            "evaluated": evaluated,
            "challenges": challenges,
        }
    )

    def impact_basis(kid: str) -> str:
        versions = {
            d: ledger["states"][d]
            for d, v in ledger["versions"].items()
            if v["knowledge_id"] == kid and ledger["states"][d] != "candidate"
        }
        return digest_record(
            {
                "policy": policy["policy_digest"],
                "paths": context["paths"],
                "current": ledger["current"].get(kid),
                "versions": versions,
                "applicability": sorted(
                    (str(k), v)
                    for k, v in ledger["applicability"].items()
                    if k[0] == change and k[1] in versions
                ),
            }
        )

    impacts: dict[str, dict[str, Any]] = {}
    current_set = {v["version_digest"] for v in constraints}
    for old in supplied:
        old_digest = old["version_digest"]
        if old_digest not in current_set:
            impact = {
                "change_id": change,
                "knowledge_id": old["knowledge_id"],
                "old_version": old_digest,
                "new_version": ledger["current"].get(old["knowledge_id"]),
                "basis_digest": impact_basis(old["knowledge_id"]),
                "approval_id": ledger["impact_approvals"].get(
                    (change, old["knowledge_id"]), context["approval_id"]
                ),
                "trigger": "version-or-applicability-changed",
            }
            impacts[digest_record(impact)] = impact
    for cid, challenge in challenges.items():
        impact = {
            "change_id": change,
            "knowledge_id": ledger["versions"][challenge["version_digest"]]["knowledge_id"],
            "old_version": challenge["version_digest"],
            "new_version": ledger["current"].get(
                ledger["versions"][challenge["version_digest"]]["knowledge_id"]
            ),
            "basis_digest": impact_basis(
                ledger["versions"][challenge["version_digest"]]["knowledge_id"]
            ),
            "approval_id": ledger["impact_approvals"].get(
                (change, ledger["versions"][challenge["version_digest"]]["knowledge_id"]),
                context["approval_id"],
            ),
            "trigger": "challenge",
            "challenge_id": cid,
        }
        impacts[digest_record(impact)] = impact
    outcomes = []
    for iid, impact in sorted(impacts.items()):
        eid = ledger["dispositions"].get(iid)
        evidence = ledger["evidence"].get(eid) if eid else None
        status = "pending"
        if evidence:
            decision = evidence["decision"]
            if decision in {"continue", "not_applicable"}:
                status = "resolved"
            else:
                execution = ledger["executions"].get(eid)
                if (
                    execution
                    and execution.get("outcome") == "verified"
                    and verified_subject
                    and execution.get("subject_id") == verified_subject
                ):
                    status = "resolved"
                else:
                    status = "executing"
            if evidence:
                constraints = [
                    v for v in constraints if v["knowledge_id"] != impact["knowledge_id"]
                ]
                if decision != "not_applicable":
                    constraints.append(deepcopy(ledger["versions"][evidence["use_version"]]))
        if status != "resolved":
            blockers.append(f"unresolved impact: {iid}")
        outcomes.append(
            {
                "impact_id": iid,
                **impact,
                "status": status,
                "disposition_id": eid,
                "disposition": evidence,
            }
        )
    basis = digest_record(
        {
            "selection_basis": basis,
            "constraints": sorted(v["version_digest"] for v in constraints),
            "dispositions": {
                i["impact_id"]: i["disposition_id"] for i in outcomes if i["disposition_id"]
            },
        }
    )
    acquisitions = [
        {
            "delivery_id": v["delivery_id"],
            "version_digest": v["version_digest"],
            "status": "observed"
            if any(
                o.get("kind") == "acquisition"
                and o["change_id"] == change
                and o.get("delivery_id") == v["delivery_id"]
                and o.get("version_digest") == v["version_digest"]
                for o in ledger["observations"]
            )
            else "not_observed",
        }
        for v in supplied
    ]
    return {
        "schema_version": "knowledge-context/v1",
        "coverage": "explicit-rules-only",
        "product_id": policy["product_id"],
        "repository_id": policy["repository_id"],
        "change_id": change,
        "basis_digest": basis,
        "context": context,
        "constraints": sorted(constraints, key=lambda v: v["version_digest"]),
        "recognition_evidence": {
            v["version_digest"]: ledger["evidence"][ledger["recognitions"][v["version_digest"]]]
            for v in constraints
        },
        "evaluated": evaluated,
        "supply_history": supplied,
        "impacts": outcomes,
        "challenges": challenges,
        "acquisition_coverage": acquisitions,
        "blocking_reasons": blockers,
        "statements": [s for s in ledger["statements"] if s["change_id"] == change],
        "observations": [s for s in ledger["observations"] if s["change_id"] == change],
        "missing_observations": ["understanding", "compliance"]
        + (
            []
            if acquisitions and all(a["status"] == "observed" for a in acquisitions)
            else ["recipient-acquisition"]
        ),
        "limits": ["single-repository", "unidentified-semantic-relations-not-evaluated"],
    }


def _context(state: Any, extra_paths: list[str] | None = None) -> dict[str, Any]:
    scope = state.scope.get("files", [])
    paths = set(scope if isinstance(scope, list) else [])
    for row in state.coverage_manifest:
        paths.add(row["path"])
    if state.current_code_subject:
        for row in state.current_code_subject.get("manifest", []):
            paths.add(row["path"])
            if row.get("old_path"):
                paths.add(row["old_path"])
    paths.update(extra_paths or [])
    return {
        "paths": sorted(_path(p) for p in paths),
        "approval_id": (state.effective_approval or {}).get("approval_id"),
        "plan_subject_id": (state.effective_approval or {}).get("subject_id"),
    }


def report(
    root: Path,
    change: str,
    *,
    events_file: Path | None = None,
    extra_paths: list[str] | None = None,
) -> dict[str, Any]:
    from keepsail.core.reducer import derive_state

    path = events_file or root / ".harness/events.jsonl"
    policy, candidate = policy_configuration(root)
    ledger, revision = load_ledger(path, policy)
    if policy is None:
        view: dict[str, Any] = {"coverage": "not_recorded", "revision": revision}
        if candidate is not None:
            view["policy_candidate"] = {
                "status": "candidate", "policy_digest": candidate["policy_digest"]
            }
        return view
    state = derive_state(path).get(change)
    _need(state is not None, "unknown Change")
    assert state is not None
    verified = (
        (state.current_code_subject or {}).get("subject_id")
        if (
            state.current_state == "READY_TO_MERGE"
            and (state.current_verification or {}).get("outcome") == "passed"
        )
        else None
    )
    view = _view(ledger, policy, change, _context(state, extra_paths), verified)
    view["revision"] = revision
    view["effective_approval"] = state.effective_approval
    return view


def prepare(
    root: Path, event_type: str, request: dict[str, Any], *, events_file: Path | None = None
) -> tuple[dict[str, Any], bool]:
    path = events_file or root / ".harness/events.jsonl"
    policy = load_policy(root)
    _need(policy is not None, "no owner-activated knowledge policy")
    assert policy is not None
    ledger, revision = load_ledger(path, policy)
    op = _operation(request)
    prior = ledger["operations"].get(op)
    if prior:
        original_request = {k: v for k, v in prior["request"].items() if k != "_input_digest"}
        normalized_request = {k: v for k, v in request.items() if k != "_input_digest"}
        if original_request != normalized_request:
            raise KnowledgeError("operation ID reused with different request", exit_code=5)
        return {
            "request": prior["request"],
            "result": prior["result"],
            "policy_digest": policy["policy_digest"],
        }, True
    if request["expected_revision"] != revision:
        raise KnowledgeError("knowledge revision conflict", code="knowledge_conflict", exit_code=5)
    if event_type == "knowledge_delivered":
        view = report(root, request["change_id"], events_file=path)
        expected = {
            k: view[k]
            for k in (
                "change_id",
                "constraints",
                "basis_digest",
                "evaluated",
                "context",
                "recognition_evidence",
            )
        }
        _need(request.get("delivery") == expected, "delivery does not cover the current finite set")
    if event_type == "knowledge_imported":
        ev = request.get("evidence", {})
        target = ev.get("impact", {}).get("change_id") if ev.get("kind") == "disposition" else None
        if target:
            view = report(root, target, events_file=path)
            _need(
                any(
                    i["impact_id"] == ev.get("subject_id")
                    and {
                        k: v
                        for k, v in i.items()
                        if k not in {"impact_id", "status", "disposition_id", "disposition"}
                    }
                    == ev["impact"]
                    for i in view["impacts"]
                ),
                "stale or unknown impact subject",
            )
            version = ledger["versions"].get(ev.get("use_version"))
            if version:
                _need(
                    version["knowledge_id"] == ev["impact"]["knowledge_id"],
                    "disposition selects another knowledge identity",
                )
    if (
        event_type == "knowledge_recorded"
        and request.get("record", {}).get("outcome") == "verified"
    ):
        _validate_execution(root, path, ledger, request)
    from keepsail.core.reducer import derive_state

    approval_context = {
        cid: (s.effective_approval or {}).get("approval_id")
        for cid, s in derive_state(path).items()
    }
    result = _apply(ledger, event_type, request, policy, approval_context)
    return {
        "request": request,
        "result": result,
        "policy_digest": policy["policy_digest"],
        "approval_context": approval_context,
    }, False


def _validate_execution(
    root: Path, path: Path, ledger: dict[str, Any], request: dict[str, Any]
) -> None:
    from keepsail.core.reducer import derive_state

    record = request["record"]
    disposition = ledger["evidence"].get(record.get("disposition_id"), {})
    state = derive_state(path).get(request["change_id"])
    _need(state is not None, "execution names unknown Change")
    view = report(root, request["change_id"], events_file=path)
    _need(
        any(i["disposition_id"] == record.get("disposition_id") for i in view["impacts"]),
        "execution disposition is stale",
    )
    assert state is not None
    verification = state.current_verification or {}
    code = state.current_code_subject or {}
    _need(
        verification.get("outcome") == "passed"
        and code.get("subject_id")
        and record.get("subject_id") == code["subject_id"]
        and verification.get("subject_id") == code["subject_id"],
        "verified execution requires the current passed verification/code subject",
    )
    _need(
        state.current_state == "READY_TO_MERGE" and state.implementation_assessments,
        "verified execution requires actual assessment and recognized code review",
    )
    _need(
        set(record.get("fulfilled_obligations", [])) == set(disposition.get("obligations", [])),
        "execution must account for every adjustment obligation",
    )
    if disposition.get("decision") == "reapprove":
        _need(
            (state.effective_approval or {}).get("approval_id")
            != disposition["impact"]["approval_id"],
            "execution needs a new plan approval",
        )


def validate_event(events_file: Path, event: Event) -> None:
    root = events_file.parent.parent
    if event.type == "knowledge_checkpointed":
        expected = checkpoint(root, event.change_id, events_file=events_file)
        _need(event.payload == expected, "knowledge checkpoint does not match the recorded facts")
        _need(not expected["view"]["blocking_reasons"], "unresolved knowledge obligations")
    elif event.type in EVENT_TYPES:
        from keepsail.core.reducer import derive_state

        state = derive_state(events_file).get(event.change_id)
        _need(state is not None, "unknown governing Change")
        if event.type in {"knowledge_proposed", "knowledge_imported"}:
            _need(
                state is not None
                and state.effective_approval is not None
                and state.current_state == "IMPLEMENTATION_IN_PROGRESS",
                "knowledge authoring requires an approved governing Change",
            )
        request = event.payload.get("request", {})
        _need(event.change_id == request.get("change_id"), "knowledge governing Change mismatch")
        payload, replay = prepare(root, event.type, request, events_file=events_file)
        _need(not replay and payload == event.payload, "duplicate or corrupted knowledge event")
    elif event.type in PREREQUISITES:
        view = report(root, event.change_id, events_file=events_file)
        if view["coverage"] == "not_recorded":
            return
        # Plan submission itself contributes its estimated scope.
        if event.type == "plan_ready":
            extra = event.payload.get("scope", {}).get("files", [])
            view = report(root, event.change_id, events_file=events_file, extra_paths=extra)
        if event.type not in {"plan_ready"}:
            blocking = list(view["blocking_reasons"])
            # Adjustment execution needs an exact verified code review before it
            # can resolve. Permit that review epoch, never final merge, while a
            # recognized adjustment is being executed. Pending judgments still wait.
            if event.type in {"implementation_complete", "code_review_passed"}:
                running = {
                    i["impact_id"]
                    for i in view["impacts"]
                    if i["status"] == "executing"
                    and (
                        i["disposition"]["decision"] != "reapprove"
                        or i["approval_id"] != view["context"]["approval_id"]
                    )
                }
                blocking = [
                    b for b in blocking if b.removeprefix("unresolved impact: ") not in running
                ]
            _need(not blocking, "; ".join(blocking))
            ledger, _ = load_ledger(events_file, load_policy(root))
            supplied = any(
                d["change_id"] == event.change_id
                and d["basis_digest"] == view["basis_digest"]
                and d["constraints"] == view["constraints"]
                for d in ledger["deliveries"].values()
            )
            _need(supplied, "current constraints require an exact retained delivery")


def checkpoint(root: Path, change: str, *, events_file: Path | None = None) -> dict[str, Any]:
    """Self-contained cross-governing-Change evidence, without recursive checkpoints."""
    path = events_file or root / ".harness/events.jsonl"
    policy = load_policy(root)
    _need(policy is not None, "no activated knowledge policy")
    ledger, revision = load_ledger(path, policy)
    view = report(root, change, events_file=path)
    record = {
        "schema_version": "knowledge-checkpoint/v1",
        "policy": policy,
        "events": ledger["events"],
        "view": view,
        "source_revision": revision,
    }
    return {**record, "digest": digest_record(record)}


def retain_checkpoint(events_file: Path, change: str) -> None:
    """Called by attestation export, through the normal strict writer."""
    root = events_file.parent.parent
    if load_policy(root) is None:
        return
    from keepsail.core.clock import utc_now_iso
    from keepsail.core.events import Actor
    from keepsail.core.ulid import new_event_id
    from keepsail.core.writer import EventWriter

    payload = checkpoint(root, change, events_file=events_file)
    EventWriter(events_file).emit(
        Event(
            event_id=new_event_id(),
            type="knowledge_checkpointed",
            change_id=change,
            timestamp=utc_now_iso(),
            actor=Actor(type="agent", identifier="attestation-export"),
            framework="plain",
            payload=payload,
        )
    )


def validate_checkpoint(
    payload: dict[str, Any],
    policy: dict[str, Any],
    state: Any,
    *,
    required_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Pure retained-evidence validation. No local events/state/policy are consulted.

    CAS prefix receipts are retained here; their byte-level validation belongs to
    the live ledger. This snapshot revalidates recognized subjects and conclusions.
    """
    _need(
        payload.get("schema_version") == "knowledge-checkpoint/v1", "missing knowledge checkpoint"
    )
    _need(
        payload.get("digest") == digest_record({k: v for k, v in payload.items() if k != "digest"}),
        "knowledge checkpoint digest mismatch",
    )
    _need(payload.get("policy") == policy, "checkpoint does not use the trusted knowledge policy")
    ledger = _empty()
    events = payload.get("events")
    _need(isinstance(events, list), "checkpoint needs retained knowledge events")
    assert isinstance(events, list)
    for raw in events:
        event = parse_event_line(canonical_json(raw))
        _need(
            event.type in EVENT_TYPES
            and event.payload.get("policy_digest") == policy["policy_digest"],
            "invalid retained knowledge event",
        )
        request = event.payload.get("request")
        _need(isinstance(request, dict), "missing retained request")
        assert isinstance(request, dict)
        result = _apply(
            ledger, event.type, request, policy, event.payload.get("approval_context", {})
        )
        _need(result == event.payload.get("result"), "retained result mismatch")
        ledger["events"].append(raw)
    indexed = {e["event_id"]: e for e in events}
    for required in required_events or []:
        _need(
            indexed.get(required["event_id"]) == required,
            "checkpoint omits or changes trusted historical knowledge",
        )
    verified = (
        (state.current_code_subject or {}).get("subject_id")
        if (
            state.current_state == "READY_TO_MERGE"
            and (state.current_verification or {}).get("outcome") == "passed"
        )
        else None
    )
    view = _view(ledger, policy, state.change_id, _context(state), verified)
    retained = payload.get("view", {})
    _need(
        view["basis_digest"] == retained.get("basis_digest")
        and view["constraints"] == retained.get("constraints")
        and view["impacts"] == retained.get("impacts"),
        "knowledge checkpoint basis changed",
    )
    _need(not view["blocking_reasons"], "unresolved retained knowledge obligations")
    _need(
        any(
            d["change_id"] == state.change_id
            and d["basis_digest"] == view["basis_digest"]
            and d["constraints"] == view["constraints"]
            for d in ledger["deliveries"].values()
        ),
        "checkpoint lacks exact constraint delivery",
    )
    code = state.current_code_subject or {}
    _need(
        code.get("knowledge_basis", {}).get("digest") == view["basis_digest"],
        "code subject uses another knowledge basis",
    )
    for outcome in view["impacts"]:
        disposition = outcome["disposition"]
        if disposition and disposition["decision"] in {"adjust", "reapprove"}:
            execution = ledger["executions"].get(outcome["disposition_id"], {})
            _need(
                execution.get("outcome") == "verified"
                and execution.get("subject_id") == code.get("subject_id")
                and (state.current_verification or {}).get("outcome") == "passed"
                and state.current_state == "READY_TO_MERGE",
                "unverified retained execution",
            )
            _need(
                set(execution.get("fulfilled_obligations", []))
                == set(disposition.get("obligations", [])),
                "unaccounted retained obligations",
            )
            if disposition["decision"] == "reapprove":
                _need(
                    (state.effective_approval or {}).get("approval_id")
                    != disposition["impact"]["approval_id"],
                    "missing replacement approval",
                )
    return view


def check(root: Path, change: str, *, paths: list[str] | None = None) -> dict[str, Any]:
    view = report(root, change)
    if view["coverage"] == "not_recorded":
        return view
    if paths:
        unknown_constraints = any(
            b.startswith("unknown applicability:") for b in view["blocking_reasons"]
        )
        paths = [_path(p) for p in paths]
        relevant = []
        for impact in view["impacts"]:
            if impact["status"] == "resolved":
                continue
            challenge = view["challenges"].get(impact.get("challenge_id"), {})
            old: dict[str, Any] = next(
                (v for v in view["supply_history"] if v["version_digest"] == impact["old_version"]),
                {},
            )
            selector = old.get("selector", {})
            deps = challenge.get("dependent_paths", selector.get("paths", []))
            if challenge.get("dependency") == "global" or selector.get("global") or not deps:
                relevant.append(impact["impact_id"])
            elif any(covered_by_scope(p, deps) for p in paths):
                relevant.append(impact["impact_id"])
        view["blocking_reasons"] = [f"unresolved dependent impact: {i}" for i in relevant]
        if unknown_constraints:
            view["blocking_reasons"].append("unknown applicability cannot establish independence")
    if not paths:
        ledger, _ = load_ledger(root / ".harness/events.jsonl", load_policy(root))
        if not any(
            d["change_id"] == change
            and d["basis_digest"] == view["basis_digest"]
            and d["constraints"] == view["constraints"]
            for d in ledger["deliveries"].values()
        ):
            view["blocking_reasons"].append(
                "current constraints require an exact retained delivery"
            )
    if view["blocking_reasons"]:
        error = KnowledgeError("; ".join(view["blocking_reasons"]))
        error.data = view
        raise error
    return view
