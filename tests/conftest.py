# tests-as-package layout: tests/__init__.py + tests/unit/__init__.py make
# pytest collection rootdir-stable AND allow `from tests.unit.fixtures import X`
# in later phases (e.g., shared verification-runner fixtures). Keep this if
# you add `tests/utils.py`; remove `__init__.py` files if you prefer
# rootdir-only collection.

from copy import deepcopy
from shutil import copytree

import pytest


@pytest.fixture(scope="session")
def _approved_context_template(tmp_path_factory):
    """Bootstrap once through native public operations; never share mutable test state."""
    from tests.unit.core import test_knowledge as fixtures

    policy = fixtures.policy()
    policy["observation_issuers"].append("keepsail-cli-observer")
    policy["policy_digest"] = fixtures.policy_digest(policy)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(fixtures, "policy", lambda: policy)
        return fixtures.Workspace(tmp_path_factory.mktemp("approved-context-template"))


@pytest.fixture
def context_workspace(tmp_path, _approved_context_template, monkeypatch):
    import yaml

    from tests.unit.core import test_knowledge as fixtures

    copytree(_approved_context_template.root, tmp_path, dirs_exist_ok=True)
    workspace = deepcopy(_approved_context_template)
    workspace.root = tmp_path
    policy = yaml.safe_load((tmp_path / ".harness/knowledge-recognition.yaml").read_text())
    monkeypatch.setattr(fixtures, "policy", lambda: deepcopy(policy))
    return workspace
