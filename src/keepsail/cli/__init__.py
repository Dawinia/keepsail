"""keepsail CLI root group.

Defines the top-level `keepsail` Click group and its lazy command registry.
Per `cli-command-surface` §2.1 global conventions (`--workspace`, `--json`,
`--quiet`, `--verbose` flags).
"""

from __future__ import annotations

import click

from keepsail.cli.group_options import (
    GroupAwareCommand,
    GroupAwareGroup,
)
from keepsail.cli.lazy_group import CommandSpec, LazyGroup
from keepsail.version import __version__

COMMAND_SPECS = {
    "knowledge": CommandSpec(
        "keepsail.cli.knowledge:knowledge_group",
        "Deliver explicit constraints and retain versions and impact evidence.",
    ),
    "adapter": CommandSpec(
        "keepsail.cli.adapter:adapter_group",
        "Install / uninstall / list keepsail integrations for frameworks + agents.",
    ),
    "attest": CommandSpec(
        "keepsail.cli.attest:attest_group",
        "Lifecycle attestation: snapshot evidence + verify it covers a diff.",
    ),
    "change": CommandSpec(
        "keepsail.cli.change:change_group",
        "Declare / abandon / list lifecycle changes.",
    ),
    "decision": CommandSpec(
        "keepsail.cli.decision:decision_group",
        "Author, ratify, and check decision records.",
    ),
    "doc": CommandSpec(
        "keepsail.cli.doc:doc_group",
        "Check that derivable docs match their generators.",
    ),
    "done": CommandSpec(
        "keepsail.cli.done:done_cmd",
        "Verify a change and emit implementation_complete on a pass.",
    ),
    "event": CommandSpec(
        "keepsail.cli.event:event_group",
        "Inspect the event stream.",
    ),
    "gate": CommandSpec(
        "keepsail.cli.gate:gate_group",
        "Inspect the gate registry.",
    ),
    "implementation": CommandSpec(
        "keepsail.cli.implementation:implementation_group",
        "Implementation-phase lifecycle verbs.",
    ),
    "init": CommandSpec(
        "keepsail.cli.init:init_cmd",
        "Initialize a project for keepsail.",
    ),
    "observe": CommandSpec(
        "keepsail.cli.observe:observe_group",
        "Operate the optional framework-observer host (start / stop / status).",
    ),
    "on-merge": CommandSpec(
        "keepsail.cli.on_merge:on_merge_cli",
        "Emit a ``merged`` event (transitions the change to ARCHIVED).",
    ),
    "plan": CommandSpec(
        "keepsail.cli.plan:plan_group",
        "Plan-phase lifecycle verbs (plain-mode manual emit).",
    ),
    "pr": CommandSpec(
        "keepsail.cli.pr:pr_group",
        "PR-side helpers (validate PR metadata + lifecycle).",
    ),
    "report": CommandSpec(
        "keepsail.cli.report:report_cmd",
        "Show what the harness measurably did for you over a repo/time-window.",
    ),
    "review": CommandSpec(
        "keepsail.cli.review:review_group",
        "Import externally produced, user-recognized review evidence.",
    ),
    "sensor": CommandSpec(
        "keepsail.cli.sensor:sensor_group",
        "Inspect the sensor registry.",
    ),
    "state": CommandSpec(
        "keepsail.cli.state:state_group",
        "Inspect / rebuild the derived state.yaml.",
    ),
    "status": CommandSpec(
        "keepsail.cli.status:status_cmd",
        "Show current state for one change, all changes, or the most recently active change.",
    ),
    "sync": CommandSpec(
        "keepsail.cli.sync:sync_cmd",
        "Re-render the managed keepsail artifacts without re-running init.",
    ),
    "verification": CommandSpec(
        "keepsail.cli.verification:verification_group",
        "Register / manage verification checks in `.harness/verification.yaml`.",
    ),
    "verify": CommandSpec(
        "keepsail.cli.verify:verify_cmd",
        "Run verification checks for a change and report the verdict.",
    ),
}


@click.group(
    cls=LazyGroup,
    command_specs=COMMAND_SPECS,
    help="Keepsail — product-work control layer across agent harnesses.",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(__version__, "--version", "-V", package_name="keepsail")
@click.option(
    "--workspace",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Project root (defaults to walk-up from cwd).",
)
@click.option("--json", "json_output", is_flag=True, help="Machine-parseable JSON output.")
@click.option("--quiet", "-q", is_flag=True)
@click.option("--verbose", "-v", count=True)
@click.pass_context
def main(
    ctx: click.Context,
    workspace: str | None,
    json_output: bool,
    quiet: bool,
    verbose: int,
) -> None:
    """Root command group for keepsail."""
    # Naming convention for ctx.obj keys:
    #   - Keys use the SHORT CLI flag name (e.g. "json", "quiet", "workspace"), NOT the
    #     Python param name (`json_output` was renamed only to avoid shadowing stdlib `json`).
    #   - Subcommands must read `ctx.obj["json"]`, `ctx.obj["quiet"]`, etc. — never
    #     `ctx.obj["json_output"]`. The Python param `json_output` is private to this function.
    #   - If you add a new global flag in the future, store it under its CLI name in ctx.obj.
    ctx.ensure_object(dict)
    ctx.obj["workspace"] = workspace
    ctx.obj["json"] = json_output
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose


# Re-export names used by other modules / tests.
__all__ = [
    "CommandSpec",
    "GroupAwareCommand",
    "GroupAwareGroup",
    "LazyGroup",
    "main",
]
