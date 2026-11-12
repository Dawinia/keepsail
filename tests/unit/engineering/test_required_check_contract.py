import pytest

from keepsail.core.approval import ApprovalError
from keepsail.engineering.verification_config import (
    VerificationConfigError,
    parse_verification_config,
    required_check_contract,
)

CONFIG = """
layers:
  baseline: {enabled: true}
  framework_adapter: {enabled: true}
  user_checks: {enabled: true}
defaults:
  timeout_seconds: 60
  workdir: app
  env: {CI: '1', SHARED: default}
checks:
  - id: tests
    command: [python, -m, pytest, '${CHANGE_ID}']
    env: {SHARED: override}
  - id: optional
    command: [python, --version]
    must_pass: false
adapter_provided:
  - id: verify
    command: [tool, check]
    provided_by: framework-a
"""


def contract(text=CONFIG):
    return required_check_contract(parse_verification_config(text, strict=True))


def test_contract_normalizes_inherited_settings_sources_and_mandatory_checks():
    result = contract()
    assert [(item["source"], item["id"]) for item in result["checks"]] == [
        ("adapter:framework-a", "verify"), ("user", "tests"),
    ]
    check = result["checks"][1]
    assert check["env"] == {"CI": "1", "SHARED": "override"}
    assert check["timeout_seconds"] == 60
    assert check["workdir"] == "app"
    assert check["command"] == ["python", "-m", "pytest", "${CHANGE_ID}"]
    assert check["must_pass"] is True


@pytest.mark.parametrize("old,new", [
    ("timeout_seconds: 60", "timeout_seconds: 61"),
    ("workdir: app", "workdir: other"),
    ("CI: '1'", "CI: '2'"),
    ("provided_by: framework-a", "provided_by: framework-b"),
    ("-m, pytest", "-m, unittest"),
    ("user_checks: {enabled: true}", "user_checks: {enabled: false}"),
    ("id: tests", "id: renamed"),
])
def test_material_obligation_changes_change_digest(old, new):
    assert contract()["digest"] != contract(CONFIG.replace(old, new))["digest"]


def test_optional_check_changes_do_not_change_mandatory_digest():
    changed = CONFIG.replace("python, --version", "python, -V")
    assert contract()["digest"] == contract(changed)["digest"]


def test_strict_config_rejects_duplicate_keys_and_unidentified_required_adapters():
    with pytest.raises(ApprovalError, match="duplicate"):
        contract(CONFIG + "checks: []\n")
    with pytest.raises(VerificationConfigError, match="source identity"):
        contract(CONFIG.replace("    provided_by: framework-a\n", ""))
