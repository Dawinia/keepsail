# tests-as-package layout: tests/__init__.py + tests/unit/__init__.py make
# pytest collection rootdir-stable AND allow `from tests.unit.fixtures import X`
# in later phases (e.g., shared verification-runner fixtures). Keep this if
# you add `tests/utils.py`; remove `__init__.py` files if you prefer
# rootdir-only collection.

from copy import deepcopy
from shutil import copytree

import pytest


@pytest.fixture(scope="session")
def _knowledge_template(tmp_path_factory):
    from tests.unit.core.test_knowledge import Workspace

    return Workspace(tmp_path_factory.mktemp("knowledge-template"))


@pytest.fixture
def knowledge_workspace(tmp_path, _knowledge_template):
    copytree(_knowledge_template.root, tmp_path, dirs_exist_ok=True)
    workspace = deepcopy(_knowledge_template)
    workspace.root = tmp_path
    return workspace


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


@pytest.fixture(autouse=True)
def _claude_code_cli_at_minimum(monkeypatch):
    """Report the minimum Claude Code CLI to in-process installs.

    The Claude Code adapter refuses to write exec-form hooks unless the `claude`
    CLI is at least the supported minimum. Most tests are not about that preflight
    (and CI has no `claude`), so this single seam -- resolution plus version run --
    answers with the minimum. Preflight tests replace it again with their own fake.
    """
    from keepsail.adapters.agent import claude_code

    minimum = ".".join(str(part) for part in claude_code.MINIMUM_CLAUDE_CODE_VERSION)
    monkeypatch.setattr(claude_code, "probe_claude_code_version", lambda *_args: minimum)


@pytest.fixture
def posix_hook_target(monkeypatch):
    """Plan agent hooks for a POSIX host, whatever OS runs the test.

    For tests that use POSIX-style fake executable paths; the Windows transport and
    `.exe` rules are covered by tests that set the target explicitly.
    """
    from keepsail.adapters.agent.claude_code import ClaudeCodeAdapter
    from keepsail.adapters.agent.codex import CodexAdapter

    monkeypatch.setattr(ClaudeCodeAdapter, "target_os", "posix")
    monkeypatch.setattr(CodexAdapter, "target_os", "posix")


def hook_argv(handler):
    """A handler's argument vector joined by spaces, for exec and string forms."""
    return " ".join([handler["command"], *handler.get("args", [])])


def fake_claude_cli_env(directory, version="2.1.332"):
    """Environment whose PATH starts with a fake `claude` printing ``version``.

    For tests that run the installed `keepsail` binary in a subprocess, where the
    in-process preflight seam does not apply: the real preflight resolves and runs
    this fake instead of a Claude Code install that CI does not have.
    """
    import os
    import stat
    from pathlib import Path

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        (directory / "claude.cmd").write_text(f"@echo {version} (Claude Code)\r\n")
    else:
        script = directory / "claude"
        script.write_text(f"#!/bin/sh\necho '{version} (Claude Code)'\n")
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {**os.environ, "PATH": str(directory) + os.pathsep + os.environ.get("PATH", "")}
