"""Import a signed authorization without granting or activating a policy."""

from __future__ import annotations

import base64
import binascii
import json
import sys
from hashlib import sha256
from pathlib import Path

import click

from keepsail.cli.errors import format_error
from keepsail.cli.output import json_envelope
from keepsail.core.approval import (
    ApprovalError,
    digest_record,
    load_json_input,
    resolve_contract_base,
)
from keepsail.core.clock import utc_now_iso
from keepsail.core.emit_validation import EmitPreconditionError
from keepsail.core.events import Actor, Event
from keepsail.core.identity import resolve_identity
from keepsail.core.paths import HarnessNotInitialized, events_path, find_harness_root
from keepsail.core.policy_authority import parse_unique_yaml, validate_authorization_import
from keepsail.core.post_emit import refresh_state_after_emit
from keepsail.core.reducer import derive_state
from keepsail.core.review_verdict import read_change_events
from keepsail.core.scope_match import GitScopeError
from keepsail.core.ulid import new_event_id
from keepsail.core.writer import EventWriter
from keepsail.exit_codes import EXIT_NO_CONFIG, EXIT_OK, EXIT_VALIDATION


@click.group("policy")
def policy_group() -> None:
    """Inspect and import policy transition evidence."""


@policy_group.group("initial")
def initial_group() -> None:
    """Prepare, but never activate, an owner-established first policy."""


@initial_group.command("prepare")
@click.option("--repository-id", required=True, help="Owner-confirmed repository identity.")
@click.option("--target-ref", required=True, help="Owner-confirmed full target branch ref.")
@click.option("--public-key", required=True, help="Base64-encoded raw Ed25519 public key.")
@click.option("--enable-recovery", is_flag=True, help="Include recovery in the proposed purposes.")
@click.pass_context
def prepare_initial(ctx: click.Context, repository_id: str, target_ref: str, public_key: str,
                    enable_recovery: bool) -> None:
    """Print a light-policy proposal and trust configuration; activate nothing."""
    from keepsail.core.delivery_policy import parse_delivery_policy
    from keepsail.core.policy_authority import parse_authority
    from keepsail.core.verification_config import parse_verification_config, required_check_contract

    command = "policy initial prepare"
    try:
        root = find_harness_root(Path(ctx.obj.get("workspace") or "."))
        key = base64.b64decode(public_key, validate=True)
        purposes = ["policy-transition", "plan-decision"]
        if enable_recovery:
            purposes.append("policy-recovery")
        authority = {"version": "policy-authority/v1", "repository_id": repository_id,
                     "target_ref": target_ref, "enabled": True, "keys": [{
                         "key_id": sha256(key).hexdigest(), "algorithm": "ed25519",
                         "public_key": public_key, "purposes": purposes,
                     }]}
        parse_authority(authority)
        config = parse_verification_config(
            (root / ".harness/verification.yaml").read_text(encoding="utf-8"), strict=True
        )
        policy = {"version": "review-recognition/v2", "enabled": True,
                  "processes_by_kind": {"plan": {"id": "maintainer-plan-review",
                      "version": "maintainer-plan-review/v1", "issuers": ["maintainer"],
                      "evidence_forms": ["signed-plan-decision"], "requirements": {}}},
                  "code_review": {"mode": "off"},
                  "required_checks_digest": required_check_contract(config)["digest"],
                  "builtin_checks_version": "keepsail-baseline/v2",
                  "activation": {"kind": "initial"}}
        policy["policy_digest"] = digest_record(policy)
        parse_delivery_policy(policy)
    except HarnessNotInitialized as exc:
        click.echo(format_error(subcommand=command, message=exc.message, hint=exc.hint), err=True)
        sys.exit(EXIT_NO_CONFIG)
    except (ApprovalError, OSError, ValueError, binascii.Error) as exc:
        click.echo(format_error(subcommand=command, message=str(exc)), err=True)
        sys.exit(EXIT_VALIDATION)
    data = {"policy": policy, "authority": authority, "authority_effect": "unchanged"}
    if ctx.obj.get("json"):
        click.echo(json_envelope(command=command, status="pass", exit_code=EXIT_OK, data=data))
    else:
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))


@initial_group.command("confirmation")
@click.option("--initial-commit", required=True,
              help="Full commit ID of the proposed first policy.")
@click.option("--repository-id", required=True)
@click.option("--target-ref", required=True)
@click.option("--evidence", required=True, type=click.Path(exists=True, dir_okay=False,
                                                         allow_dash=True))
@click.pass_context
def initial_confirmation(ctx: click.Context, initial_commit: str, repository_id: str,
                         target_ref: str, evidence: str) -> None:
    """Print a record retaining the supplied original owner confirmation."""
    from keepsail.core.initial_policy import prepare_initial_confirmation

    command = "policy initial confirmation"
    try:
        root = find_harness_root(Path(ctx.obj.get("workspace") or "."))
        record = prepare_initial_confirmation(
            root, initial_commit=initial_commit, repository_id=repository_id,
            target_ref=target_ref, owner_confirmation=load_json_input(evidence),
        )
    except HarnessNotInitialized as exc:
        click.echo(format_error(subcommand=command, message=exc.message, hint=exc.hint), err=True)
        sys.exit(EXIT_NO_CONFIG)
    except (ApprovalError, GitScopeError, OSError, ValueError) as exc:
        click.echo(format_error(subcommand=command, message=str(exc)), err=True)
        sys.exit(EXIT_VALIDATION)
    if ctx.obj.get("json"):
        click.echo(json_envelope(command=command, status="pass", exit_code=EXIT_OK,
                                 data={"confirmation": record, "authority_effect": "unchanged",
                                       "assurance": "retained-owner-claim"}))
    else:
        click.echo(json.dumps(record, ensure_ascii=False, indent=2))


@policy_group.group("authorization")
def authorization_group() -> None:
    """Work with signed policy transition authorizations."""


@authorization_group.command("import")
@click.argument("change")
@click.option("--evidence", required=True, type=click.Path(exists=True, dir_okay=False,
                                                         allow_dash=True))
@click.option("--repository-id", required=True, help="Explicit local repository identity.")
@click.option("--target-ref", required=True, help="Explicit full target branch ref.")
@click.option("--target-authority", type=click.Path(exists=True, dir_okay=False),
              help="Proposed YAML authority for a key rotation.")
@click.pass_context
def import_authorization(ctx: click.Context, change: str, evidence: str, repository_id: str,
                         target_ref: str, target_authority: str | None) -> None:
    """Retain an exact signed authorization; it does not approve or activate a plan."""
    command = "policy authorization import"
    try:
        root = find_harness_root(Path(ctx.obj.get("workspace") or "."))
        record = load_json_input(evidence)
        proposed = (parse_unique_yaml(Path(target_authority).read_text(encoding="utf-8"))
                    if target_authority else None)
        base = resolve_contract_base(root)
        payload = {"authorization": record, "authorization_digest": digest_record(record),
                   "trusted_base": base, "repository_id": repository_id,
                   "target_ref": target_ref, "target_authority": proposed}
        current = derive_state(events_path(root)).get(change)
        validate_authorization_import(root, current, change, payload)
        prior = [event.payload for event in read_change_events(events_path(root), change)
                 if event.type == "policy_authorization_imported"]
        idempotent = payload in prior
        if not idempotent:
            assert current is not None
            event = Event(event_id=new_event_id(), type="policy_authorization_imported",
                          change_id=change, timestamp=utc_now_iso(),
                          actor=Actor(type="agent", identifier=resolve_identity(root, None)),
                          framework=current.framework, payload=payload)
            EventWriter(events_path(root)).emit(event)
            refresh_state_after_emit(root)
    except HarnessNotInitialized as exc:
        click.echo(format_error(subcommand=command, message=exc.message, hint=exc.hint), err=True)
        sys.exit(EXIT_NO_CONFIG)
    except (ApprovalError, EmitPreconditionError, GitScopeError, OSError, ValueError) as exc:
        click.echo(format_error(subcommand=command, message=str(exc)), err=True)
        sys.exit(EXIT_VALIDATION)
    data = {"change": change, "authorization_digest": payload["authorization_digest"],
            "trusted_base": base, "repository_id": repository_id, "target_ref": target_ref,
            "identity_assurance": "local-explicit", "idempotent": idempotent,
            "authority_effect": "unchanged"}
    if ctx.obj.get("json"):
        click.echo(json_envelope(command=command, status="pass", exit_code=EXIT_OK, data=data))
    elif not ctx.obj.get("quiet"):
        click.echo(f"retained policy authorization for {change}; authority unchanged")
