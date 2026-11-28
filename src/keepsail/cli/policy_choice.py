"""Adoption choices shared by `init` and `policy enable` (no event-writer imports)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click


def adoption_options(function: Any) -> Any:
    """Shared adoption choices for `init` and `policy enable`."""
    options = [
        click.option("--recognize", type=click.Choice(["owner", "external"]),
                     help="Whose review conclusions count: the owner (default) or an "
                          "external process."),
        click.option("--process-id", help="External review process id."),
        click.option("--process-version", help="External review process version."),
        click.option("--issuer", help="External review process issuer."),
        click.option("--code-review", "code_review", type=click.Choice(["off", "full", "scope"]),
                     help="Which deliveries need code review."),
        click.option("--code-review-scope", "code_review_scope", multiple=True,
                     help="Literal repository path needing code review (with --code-review "
                          "scope); repeatable."),
    ]
    for option in reversed(options):
        function = option(function)
    return function


def adoption_requested(params: dict[str, Any]) -> bool:
    return any(params.get(key) for key in ("recognize", "process_id", "process_version",
                                           "issuer", "code_review", "code_review_scope"))


def choice_from_params(params: dict[str, Any], *, interactive: bool) -> Any:
    from keepsail.core.approval import ApprovalError
    from keepsail.core.policy_adoption import PolicyChoice

    recognizer = params.get("recognize")
    code_review = params.get("code_review")
    process_id = params.get("process_id")
    process_version = params.get("process_version")
    issuer = params.get("issuer")
    scope = tuple(params.get("code_review_scope") or ())
    if interactive and not adoption_requested(params):
        click.echo("Whose review conclusions count for plan approval (and code review)?")
        recognizer = click.prompt("  owner = you, imported with `review import`; external = "
                                  "another process", type=click.Choice(["owner", "external"]),
                                  default="owner")
        if recognizer == "external":
            process_id = click.prompt("  process id")
            process_version = click.prompt("  process version")
            issuer = click.prompt("  issuer")
        code_review = click.prompt("Which deliveries need code review?",
                                   type=click.Choice(["off", "full", "scope"]), default="off")
        if code_review == "scope":
            raw = click.prompt("  paths needing code review (comma-separated)")
            scope = tuple(item.strip() for item in raw.split(",") if item.strip())
    if code_review is None:
        raise ApprovalError("choose which deliveries need code review with --code-review "
                            "off|full|scope")
    return PolicyChoice(recognizer=recognizer or "owner", process_id=process_id,
                        process_version=process_version, issuer=issuer,
                        code_review=code_review, scope=scope)


def confirm_required_checks(root: Path, *, interactive: bool) -> None:
    from keepsail.core.approval import ApprovalError
    from keepsail.core.policy_adoption import required_check_summary

    summary = required_check_summary(
        (root / ".harness/verification.yaml").read_text(encoding="utf-8"))
    click.echo("Required checks from .harness/verification.yaml:")
    for line in summary or ["(none)"]:
        click.echo(f"  - {line}")
    if interactive and not click.confirm("Use these required checks?", default=True):
        raise ApprovalError("edit .harness/verification.yaml, then run `keepsail policy enable`")
