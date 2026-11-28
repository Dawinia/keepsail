"""Record the owner's acceptance of a risk-boundary change; adopt a first policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from keepsail.cli.errors import format_error
from keepsail.cli.output import json_envelope
from keepsail.cli.policy_choice import (
    adoption_options,
    choice_from_params,
    confirm_required_checks,
)
from keepsail.core.approval import ApprovalError
from keepsail.core.clock import utc_now_iso
from keepsail.core.emit_validation import EmitPreconditionError
from keepsail.core.events import Actor, Event
from keepsail.core.identity import resolve_identity
from keepsail.core.paths import HarnessNotInitialized, events_path, find_harness_root
from keepsail.core.post_emit import refresh_state_after_emit
from keepsail.core.reducer import derive_state
from keepsail.core.review_verdict import read_change_events
from keepsail.core.risk_boundary import ACCEPTANCE_EVENT, POLICY_PATH, VERIFICATION_PATH
from keepsail.core.scope_match import GitScopeError, working_tree_dirty
from keepsail.core.ulid import new_event_id
from keepsail.core.writer import EventWriter
from keepsail.exit_codes import EXIT_NO_CONFIG, EXIT_OK, EXIT_VALIDATION


@click.group("policy")
def policy_group() -> None:
    """Adopt a first policy, or record the owner's acceptance of a policy change."""


def _describe(differences: list[dict[str, Any]], labels: list[str]) -> list[str]:
    lines = [f"  - {label}" for label in labels]
    for row in differences:
        if row["direction"] == "added":
            detail = f"added {json.dumps(row['after'], ensure_ascii=False)}"
        elif row["direction"] == "removed":
            detail = f"removed (was {json.dumps(row['before'], ensure_ascii=False)})"
        else:
            detail = (f"{json.dumps(row['before'], ensure_ascii=False)} -> "
                      f"{json.dumps(row['after'], ensure_ascii=False)}")
        lines.append(f"    {row['object']}{row['path']}: {detail}")
    return lines


@policy_group.command("accept")
@click.argument("change")
@click.pass_context
def accept_policy_change(ctx: click.Context, change: str) -> None:
    """Record the owner's acceptance of CHANGE's committed policy/check change.

    The candidate is the committed HEAD (the workspace is not read).  Every
    obligation change is printed before the event is recorded.  The record is
    owner-visible evidence in the ledger, attestation and PR, not a signature.
    """
    from keepsail.core.policy_acceptance import expected_acceptance

    command = "policy accept"
    try:
        root = find_harness_root(Path(ctx.obj.get("workspace") or "."))
        if working_tree_dirty(root, [POLICY_PATH, VERIFICATION_PATH]):
            raise ApprovalError("the recognition policy or verification.yaml has uncommitted "
                                "changes; commit them first (policy accept reads HEAD)")
        state = derive_state(events_path(root)).get(change)
        boundary, payload = expected_acceptance(root, state)
        prior = [event for event in read_change_events(events_path(root), change)
                 if event.type == ACCEPTANCE_EVENT]
        idempotent = bool(prior) and prior[-1].payload == payload
        if not ctx.obj.get("json") and not ctx.obj.get("quiet"):
            click.echo(f"keepsail: risk-boundary change in {change} "
                       f"(policy {boundary.base.digest} -> "
                       f"{boundary.target.digest or boundary.target.state}):")
            for line in _describe(boundary.differences, boundary.labels):
                click.echo(line)
        event_id = prior[-1].event_id if idempotent else new_event_id()
        if not idempotent:
            assert state is not None
            event = Event(event_id=event_id, type=ACCEPTANCE_EVENT, change_id=change,
                          timestamp=utc_now_iso(),
                          actor=Actor(type="human", identifier=resolve_identity(root, None)),
                          framework=state.framework, payload=payload)
            EventWriter(events_path(root)).emit(event)
            refresh_state_after_emit(root)
    except HarnessNotInitialized as exc:
        click.echo(format_error(subcommand=command, message=exc.message, hint=exc.hint), err=True)
        sys.exit(EXIT_NO_CONFIG)
    except (ApprovalError, EmitPreconditionError, GitScopeError, OSError, ValueError) as exc:
        click.echo(format_error(subcommand=command, message=str(exc)), err=True)
        sys.exit(EXIT_VALIDATION)
    data = {"change": change, "event_id": event_id, "idempotent": idempotent,
            "acceptance": payload, "labels": boundary.labels,
            "identity_assurance": "recorded-local-identity"}
    if ctx.obj.get("json"):
        click.echo(json_envelope(command=command, status="pass", exit_code=EXIT_OK, data=data))
    elif not ctx.obj.get("quiet"):
        click.echo(f"keepsail: {'already recorded' if idempotent else 'recorded'} the owner's "
                   f"acceptance for {change} ({event_id})")


@policy_group.command("enable")
@adoption_options
@click.pass_context
def enable_policy_cmd(ctx: click.Context, /, **params: Any) -> None:
    """Adopt: write the first enabled recognition policy (owner's initial setup).

    Runs only while the trusted base has no enabled policy.  It appends no
    event and changes no Change; commit the result as the adoption commit.
    """
    import os

    from keepsail.cli.init_plan import InteractionMode
    from keepsail.cli.init_ui import detect_runtime_terminal_capabilities
    from keepsail.core.policy_adoption import enable_policy

    command = "policy enable"
    interactive = (not ctx.obj.get("json") and detect_runtime_terminal_capabilities(
        sys.stdin, sys.stdout, os.environ).mode is not InteractionMode.NON_INTERACTIVE)
    try:
        root = find_harness_root(Path(ctx.obj.get("workspace") or "."))
        choice = choice_from_params(params, interactive=interactive)
        if not ctx.obj.get("json") and not ctx.obj.get("quiet"):
            confirm_required_checks(root, interactive=interactive)
        policy = enable_policy(root, choice)
    except HarnessNotInitialized as exc:
        click.echo(format_error(subcommand=command, message=exc.message, hint=exc.hint), err=True)
        sys.exit(EXIT_NO_CONFIG)
    except (ApprovalError, OSError, ValueError) as exc:
        click.echo(format_error(subcommand=command, message=str(exc)), err=True)
        sys.exit(EXIT_VALIDATION)
    if ctx.obj.get("json"):
        click.echo(json_envelope(command=command, status="pass", exit_code=EXIT_OK,
                                 data={"policy": policy, "path": POLICY_PATH}))
    elif not ctx.obj.get("quiet"):
        click.echo(f"keepsail: wrote the enabled policy to {POLICY_PATH} "
                   f"({policy['policy_digest']}); commit it to the target branch as the "
                   "adoption commit, then enable branch protection and CI")
