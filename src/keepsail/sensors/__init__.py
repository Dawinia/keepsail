"""Sensor base architecture for keepsail.

Per sensor-gate-architecture §2.1: Sensors observe lifecycle events / activities and
emit new events. A Sensor subclass declares which events / activities trigger it and
implements an idempotent `check()` that returns a SensorResult.

Public surface:
- Sensor (ABC) — subclass to write a new sensor
- SensorResult — what check() returns (status / summary / details / emit_events / suggested_action)
- Activity / ActivityType — non-event trigger payload
  (commit, push, file_change, cli_done, cli_verify)
- WorkspaceContext — read-only workspace snapshot passed to Sensor.check()
- Determinism / SensorStatus — Literal aliases used in Sensor / SensorResult

See sensor-gate-architecture spec §2.1 for the full contract.

API stability: **experimental** (v0.1). The Sensor interface may change in v0.2
without backwards compatibility. Pin to v0.1 if depending on this API.
Plugin sensors (loaded via `.harness/sensors.yaml` path+class entries) execute
arbitrary code in the daemon process; sandboxing is deferred to v0.2 (spec §3.6 #6).
"""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from keepsail.core.events import Event
from keepsail.core.workspace import WorkspaceContext

__all__ = [
    "Activity",
    "ActivityType",
    "Determinism",
    "Sensor",
    "SensorResult",
    "SensorStatus",
    "WorkspaceContext",
]

ActivityType = Literal["commit", "push", "file_change", "cli_done", "cli_verify"]
Determinism = Literal["computational", "inferential"]
SensorStatus = Literal["pass", "fail", "warning", "informational"]


@dataclass(frozen=True)
class Activity:
    """Non-event trigger (git hook, file watcher, CLI invocation) passed to sensors.

    See sensor-gate-architecture spec §2.1.
    """

    type: ActivityType
    change_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SensorResult:
    """Outcome of a single `Sensor.check()` call. Immutable.

    See sensor-gate-architecture spec §2.1.
    """

    status: SensorStatus
    summary: str
    details: dict[str, Any] | None = None
    emit_events: list[Event] = field(default_factory=list)
    suggested_action: str | None = None


class Sensor(ABC):
    """Observer that runs on lifecycle events or activities and may emit new events.

    See sensor-gate-architecture spec §2.1 for the full contract.
    Subclasses must define `name` (non-empty) and `version` (not the default "0.0.0").
    """

    name: ClassVar[str] = ""
    version: ClassVar[str] = "0.0.0"
    triggers_on_events: ClassVar[tuple[str, ...]] = ()
    triggers_on_activities: ClassVar[tuple[ActivityType, ...]] = ()
    determinism: ClassVar[Determinism] = "computational"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if inspect.isabstract(cls):
            return
        if not cls.name:
            raise TypeError(
                f"{cls.__name__} must define a non-empty `name` class attribute"
            )
        if not cls.version or cls.version == "0.0.0":
            raise TypeError(
                f"{cls.__name__} must define `version` (not the default '0.0.0')"
            )

    @abstractmethod
    def check(self, trigger: Event | Activity, context: WorkspaceContext) -> SensorResult: ...

    def reviewer_strategy(self) -> Literal["subagent", "human", "hybrid"] | None:
        return None


# --------------------------------------------------------------------------- #
# Built-in sensor registration
# --------------------------------------------------------------------------- #
#
# Registered at the BOTTOM of this module (after the base-class defs) to avoid
# the import cycle: `verification_runner` and `registry` both
# `from keepsail.sensors import ...`, so the names above must already be
# bound before we import them. Importing `keepsail.sensors` (which any
# `from keepsail.sensors.registry import ...` does first) thus self-
# registers every built-in sensor. `verification-runner` is the first builtin.
from keepsail.sensors.registry import register_builtin  # noqa: E402
from keepsail.sensors.verification_runner import VerificationRunner  # noqa: E402

register_builtin("verification-runner", VerificationRunner)

from keepsail.sensors.pr_decorator import PRDecorator  # noqa: E402

register_builtin("PR-decorator", PRDecorator)
