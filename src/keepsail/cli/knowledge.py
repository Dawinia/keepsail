"""CLI delivery surface for explicitly applicable, versioned knowledge."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from keepsail.cli.errors import format_error
from keepsail.cli.output import json_envelope
from keepsail.core.approval import ApprovalError
from keepsail.core.clock import utc_now_iso
from keepsail.core.emit_validation import EmitPreconditionError
from keepsail.core.events import Actor, Event
from keepsail.core.knowledge import (
    PROTOCOL,
    KnowledgeError,
    check,
    load_ledger,
    load_policy,
    prepare,
    read_record,
    report,
)
from keepsail.core.paths import HarnessNotInitialized, events_path, find_harness_root
from keepsail.core.post_emit import refresh_state_after_emit
from keepsail.core.ulid import new_event_id
from keepsail.core.writer import EventWriter


@click.group("knowledge")
def knowledge_group() -> None:
    """Deliver explicit constraints and retain knowledge versions and impact evidence."""


def _output(
    ctx: click.Context, command: str, data: dict[str, Any], *, error: Exception | None = None
) -> None:
    code = getattr(error, "exit_code", 2) if error else 0
    warning = bool(data.get("blocking_reasons"))
    if ctx.obj.get("json"):
        click.echo(
            json_envelope(
                command=command,
                status="fail" if error else "warning" if warning else "pass",
                exit_code=code,
                data=data,
                errors=[
                    {"code": getattr(error, "code", "knowledge_invalid"), "message": str(error)}
                ]
                if error
                else [],
            )
        )
    elif error:
        click.echo(
            format_error(
                subcommand=command,
                message=str(error),
                hint="Inspect `knowledge show` and the retained evidence.",
            ),
            err=True,
        )
    else:
        # JSON inside a human context dump is intentional: it retains exact text
        # and missing observations without a second lossy rendering vocabulary.
        import json

        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    if error:
        sys.exit(code)


def _root(ctx: click.Context) -> Path:
    return find_harness_root(Path(ctx.obj.get("workspace") or "."))


def _run(ctx: click.Context, command: str, action: Any) -> None:
    try:
        data = action(_root(ctx))
    except HarnessNotInitialized as exc:
        _output(ctx, command, {}, error=KnowledgeError(str(exc), exit_code=3))
        return
    except KnowledgeError as exc:
        _output(ctx, command, exc.data, error=exc)
        return
    except (ApprovalError, EmitPreconditionError, ValueError, TypeError, KeyError) as exc:
        _output(ctx, command, {}, error=exc)
        return
    except OSError as exc:
        _output(ctx, command, {}, error=KnowledgeError(str(exc), exit_code=1))
        return
    _output(ctx, command, data)


def _submit(root: Path, event_type: str, request: dict[str, Any]) -> dict[str, Any]:
    payload, replay = prepare(root, event_type, request)
    if not replay:
        event = Event(
            event_id=new_event_id(),
            type=event_type,
            change_id=request["change_id"],
            timestamp=utc_now_iso(),
            actor=Actor(type="agent", identifier="knowledge-cli"),
            framework="plain",
            payload=payload,
        )
        try:
            EventWriter(events_path(root)).emit(event)
        except EmitPreconditionError as exc:
            # The writer rechecks under the lock. Classify a concurrent CAS loss
            # without treating its validation failure as successful delivery.
            _, revision = load_ledger(events_path(root), load_policy(root))
            if revision != request["expected_revision"]:
                raise KnowledgeError(
                    "knowledge revision conflict", code="knowledge_conflict", exit_code=5
                ) from exc
            raise
        refresh_state_after_emit(root)
    return {
        **payload["result"],
        "idempotent_replay": replay,
        "revision": load_ledger(events_path(root), load_policy(root))[1],
    }


@knowledge_group.command("propose")
@click.option("--record", required=True, help="Workspace JSON knowledge operation.")
@click.pass_context
def propose(ctx: click.Context, record: str) -> None:
    """Retain an immutable candidate; this does not grant authority."""
    _run(
        ctx,
        "knowledge propose",
        lambda root: _submit(root, "knowledge_proposed", read_record(root, record)),
    )


@knowledge_group.command("import")
@click.option(
    "--evidence", required=True, help="Workspace JSON operation with original conclusion."
)
@click.pass_context
def import_evidence(ctx: click.Context, evidence: str) -> None:
    """Import an exact recognition, applicability or impact conclusion."""
    _run(
        ctx,
        "knowledge import",
        lambda root: _submit(root, "knowledge_imported", read_record(root, evidence)),
    )


@knowledge_group.command("record")
@click.option("--record", required=True, help="Workspace JSON observation or agent statement.")
@click.pass_context
def record_evidence(ctx: click.Context, record: str) -> None:
    """Record acquisition, statement, challenge or execution, preserving its category."""
    _run(
        ctx,
        "knowledge record",
        lambda root: _submit(root, "knowledge_recorded", read_record(root, record)),
    )


@knowledge_group.command("deliver")
@click.argument("change")
@click.option("--operation-id", required=True)
@click.option("--expected-revision", required=True)
@click.pass_context
def deliver(ctx: click.Context, change: str, operation_id: str, expected_revision: str) -> None:
    """Persist the exact finite constraint set before writing it to stdout."""

    def action(root: Path) -> dict[str, Any]:
        policy = load_policy(root)
        ledger, _ = load_ledger(events_path(root), policy)
        prior = ledger["operations"].get(operation_id)
        if prior:
            request = prior["request"]
            if (
                request["change_id"] != change
                or request["expected_revision"] != expected_revision
                or "delivery" not in request
            ):
                raise KnowledgeError("operation ID reused for a different delivery", exit_code=5)
        else:
            view = report(root, change)
            if view["coverage"] == "not_recorded":
                raise KnowledgeError("no owner-activated knowledge policy", exit_code=3)
            request = {
                "schema_version": PROTOCOL,
                "operation_id": operation_id,
                "expected_revision": expected_revision,
                "change_id": change,
                "delivery": {
                    k: view[k]
                    for k in (
                        "change_id",
                        "constraints",
                        "basis_digest",
                        "evaluated",
                        "context",
                        "recognition_evidence",
                    )
                },
            }
        result = _submit(root, "knowledge_delivered", request)
        current = report(root, change)
        result["stale"] = (
            result["basis_digest"] != current["basis_digest"]
            or result["constraints"] != current["constraints"]
        )
        result["missing_observations"] = ["recipient-acquisition", "understanding", "compliance"]
        result["limits"] = ["explicit-rules-only", "single-repository"]
        return result

    _run(ctx, "knowledge deliver", action)


@knowledge_group.command("show")
@click.argument("identifier", required=False)
@click.option("--version", "version_digest", default=None)
@click.pass_context
def show(ctx: click.Context, identifier: str | None, version_digest: str | None) -> None:
    """Read current and historical knowledge, original evidence and operation revision."""

    def action(root: Path) -> dict[str, Any]:
        policy = load_policy(root)
        ledger, revision = load_ledger(events_path(root), policy)
        versions = [
            v
            for d, v in ledger["versions"].items()
            if (identifier is None or v["knowledge_id"] == identifier)
            and (version_digest is None or d == version_digest)
        ]
        if (identifier or version_digest) and not versions:
            raise KnowledgeError("unknown knowledge identity or version")
        return {
            "coverage": "explicit-rules-only" if policy else "not_recorded",
            "revision": revision,
            "versions": [dict(v, state=ledger["states"][v["version_digest"]]) for v in versions],
            "evidence": list(ledger["evidence"].values()),
            "deliveries": ledger["deliveries"],
            "executions": ledger["executions"],
        }

    _run(ctx, "knowledge show", action)


@knowledge_group.command("check")
@click.argument("change")
@click.option(
    "--paths", multiple=True, help="Declared independent action paths (segment prefixes)."
)
@click.pass_context
def check_command(ctx: click.Context, change: str, paths: tuple[str, ...]) -> None:
    """Check unresolved obligations; this never grants execution permission."""
    _run(ctx, "knowledge check", lambda root: check(root, change, paths=list(paths) or None))
