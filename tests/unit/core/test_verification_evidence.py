from copy import deepcopy

import pytest

from keepsail.core.approval import ApprovalError
from keepsail.core.baseline_contract import builtin_check_contract
from keepsail.core.verification_evidence import verify_check_evidence
from keepsail.engineering.verification_config import (
    parse_verification_config,
    required_check_contract,
)
from keepsail.sensors.verification_runner import CheckResult, CheckTask, check_evidence


def fixture():
    cfg = parse_verification_config("""
checks:
  - id: shared
    command: [python, -m, pytest]
adapter_provided:
  - id: shared
    command: [adapter, check]
    provided_by: framework
""", strict=True)
    tasks = [CheckTask("lifecycle-ordering", True, lambda: None, source="baseline"),
             CheckTask("shared", True, lambda: None, source="adapter:framework"),
             CheckTask("shared", True, lambda: None, source="user")]
    results = [CheckResult(task.id, "pass", 0, 1, True, "fixture", None) for task in tasks]
    checks = check_evidence(cfg, tasks, results, builtin_version="keepsail-baseline/v1",
                            trusted_base="a" * 40)
    verification = {"subject_id": "code:one", "outcome": "passed", "snapshot_unchanged": True,
                    "check_evidence": checks}
    return cfg, verification


def test_builtin_contract_versions_have_frozen_golden_digests():
    assert builtin_check_contract("keepsail-baseline/v1")["digest"] == (
        "1ddaacd7fa9767c94accceabd71efc7363447721f90e3d35e22200b86e022d7a"
    )
    assert builtin_check_contract("keepsail-baseline/v2")["digest"] == (
        "9d9d5b0fa54cf652f874480833245bf6161c86d96d40de2e5f5dac21aa661eb2"
    )


def test_results_bind_subject_source_id_and_inherited_definition():
    cfg, verification = fixture()
    summary = verify_check_evidence(verification, subject_id="code:one",
                                    required_contract=required_check_contract(cfg),
                                    builtin_version="keepsail-baseline/v1", trusted_base="a" * 40)
    assert summary == {"required_project_checks": 2, "required_total_checks": 3}


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(subject_id="code:other"),
    lambda v: v["check_evidence"]["results"].pop(),
    lambda v: v["check_evidence"]["results"][1].update(status="skipped"),
    lambda v: v["check_evidence"]["results"][1].update(exit_code=1),
    lambda v: v["check_evidence"]["results"][1].update(must_pass=False),
    lambda v: v["check_evidence"]["results"][1].update(definition_digest="f" * 64),
    lambda v: v["check_evidence"]["results"][1].update(source="user"),
    lambda v: v["check_evidence"].update(builtin_checks_version="keepsail-baseline/v2"),
    lambda v: v["check_evidence"].update(trusted_base="b" * 40),
])
def test_missing_failed_changed_or_misbound_results_are_rejected(mutation):
    cfg, verification = fixture()
    changed = deepcopy(verification)
    mutation(changed)
    with pytest.raises(ApprovalError):
        verify_check_evidence(changed, subject_id="code:one",
                              required_contract=required_check_contract(cfg),
                              builtin_version="keepsail-baseline/v1", trusted_base="a" * 40)


def test_empty_project_checks_are_reported_separately():
    cfg = parse_verification_config("checks: []\nadapter_provided: []\n", strict=True)
    task = CheckTask("lifecycle-ordering", True, lambda: None, source="baseline")
    result = CheckResult(task.id, "pass", 0, 1, True, "fixture", None)
    verification = {"subject_id": "code:one", "outcome": "passed", "snapshot_unchanged": True,
                    "check_evidence": check_evidence(cfg, [task], [result],
                                                     builtin_version="keepsail-baseline/v1",
                                                     trusted_base="a" * 40)}
    summary = verify_check_evidence(verification, subject_id="code:one",
                                    required_contract=required_check_contract(cfg),
                                    builtin_version="keepsail-baseline/v1", trusted_base="a" * 40)
    assert summary == {"required_project_checks": 0, "required_total_checks": 1}
