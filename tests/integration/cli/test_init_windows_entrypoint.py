"""Installed-entrypoint contracts for the portable ``init`` command path.

These tests deliberately enter through the root lazy Click group or the generated
console script.  They do not import ``keepsail.cli.init`` directly: native
Windows reachability depends on selecting ``init`` before any POSIX-only lifecycle
module is imported.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from keepsail.cli.init_models import discover_reviewer_models

_AGENTS_BEGIN = b"<!-- keepsail section begin "
_AGENTS_END = b"<!-- keepsail section end -->"
_GITIGNORE_BEGIN = b"# >>> keepsail gitignore (do not edit between markers)"
_GITIGNORE_END = b"# <<< keepsail gitignore"


def _console_script() -> str:
    entrypoint = shutil.which("keepsail")
    assert entrypoint is not None, "the keepsail console script must be installed"
    return entrypoint


def _run_init(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _console_script(),
            "--workspace",
            str(workspace),
            "init",
            "--no-agent",
            *args,
        ],
        input="",
        text=True,
        capture_output=True,
        check=False,
    )


def test_root_lazy_init_rejects_posix_and_unrelated_eager_imports(tmp_path: Path) -> None:
    workspace = tmp_path / "fresh process workspace"
    workspace.mkdir()
    probe = textwrap.dedent(
        """
        import importlib.abc
        import pathlib
        import subprocess
        import sys

        workspace = pathlib.Path(sys.argv[1])
        # prompt_toolkit imports asyncio, which imports the host subprocess module.
        # Preload that platform infrastructure before the package import boundary:
        # POSIX subprocess itself imports fcntl, while Windows subprocess does not.
        # Removing fcntl now lets the finder reject any later package/lifecycle
        # attempt without turning a host-stdlib difference into a false failure.
        del subprocess
        sys.modules.pop("fcntl", None)
        forbidden = {
            "fcntl",
            "keepsail.core.writer",
            "keepsail.core.post_emit",
            "keepsail.daemon.server",
            "keepsail.daemon.supervisor",
            "keepsail.cli.adapter",
            "keepsail.cli.attest",
            "keepsail.cli.change",
            "keepsail.cli.decision",
            "keepsail.cli.doc",
            "keepsail.cli.done",
            "keepsail.cli.event",
            "keepsail.cli.gate",
            "keepsail.cli.implementation",
            "keepsail.cli.observe",
            "keepsail.cli.on_merge",
            "keepsail.cli.plan",
            "keepsail.cli.pr",
            "keepsail.cli.report",
            "keepsail.cli.review",
            "keepsail.cli.sensor",
            "keepsail.cli.state",
            "keepsail.cli.status",
            "keepsail.cli.sync",
            "keepsail.cli.verify",
            "keepsail.cli.verification",
        }

        class RejectForbiddenImports(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                del path, target
                if fullname in forbidden:
                    raise AssertionError(f"forbidden eager import: {fullname}")
                return None

        sys.meta_path.insert(0, RejectForbiddenImports())

        from click.testing import CliRunner
        from keepsail.cli import main

        result = CliRunner().invoke(
            main,
            ["--workspace", str(workspace), "init", "--no-agent"],
        )
        if result.exit_code != 0:
            raise AssertionError(result.output) from result.exception
        if "keepsail.cli.init" not in sys.modules:
            raise AssertionError("the real lazy init command was not resolved")
        loaded = sorted(forbidden.intersection(sys.modules))
        if loaded:
            raise AssertionError(f"forbidden modules loaded: {loaded}")
        if not (workspace / ".harness").is_dir():
            raise AssertionError("init did not create .harness")
        """
    )

    result = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(workspace)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_non_tty_console_init_accepts_workspace_path_with_spaces(tmp_path: Path) -> None:
    workspace = tmp_path / "keepsail init smoke"
    workspace.mkdir()

    result = _run_init(workspace)

    assert result.returncode == 0, result.stderr or result.stdout
    assert (workspace / ".harness").is_dir()


def test_reviewer_model_discovery_accepts_windows_style_home_with_spaces(
    tmp_path: Path,
) -> None:
    home = tmp_path / "C:" / "Users" / "Test User"
    config = home / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('model = "gpt-5.2-codex"\n', encoding="utf-8")

    discovery = discover_reviewer_models(
        home=home,
        persisted_models={},
        sources={"codex"},
    )

    assert [candidate.model for candidate in discovery.candidates["codex"]] == ["gpt-5.2-codex"]


def test_init_preserves_crlf_user_content_around_managed_markers(tmp_path: Path) -> None:
    workspace = tmp_path / "crlf workspace"
    workspace.mkdir()
    agents_user = b"# Team agents\r\n\r\nKeep this guidance.\r\n"
    gitignore_user = b"# Team ignores\r\n*.local\r\n"
    agents_path = workspace / "AGENTS.md"
    gitignore_path = workspace / ".gitignore"
    agents_path.write_bytes(agents_user)
    gitignore_path.write_bytes(gitignore_user)

    result = _run_init(workspace)

    assert result.returncode == 0, result.stderr or result.stdout
    agents = agents_path.read_bytes()
    gitignore = gitignore_path.read_bytes()
    assert agents.startswith(agents_user)
    assert (
        gitignore.decode("utf-8")
        .replace("\r\n", "\n")
        .startswith(gitignore_user.decode("utf-8").replace("\r\n", "\n"))
    )
    assert agents.count(_AGENTS_BEGIN) == 1
    assert agents.count(_AGENTS_END) == 1
    assert gitignore.count(_GITIGNORE_BEGIN) == 1
    assert gitignore.count(_GITIGNORE_END) == 1
    # AGENTS.md adopts its existing uniform style. For .gitignore, assert the user
    # lines and ordering above; do not invent a package-wide newline-normalization
    # guarantee for a separate injector.
    assert b"\n" not in agents.replace(b"\r\n", b"")


@pytest.mark.skipif(sys.platform != "win32", reason="requires the Windows console launcher")
def test_windows_uses_the_installed_console_launcher(tmp_path: Path) -> None:
    entrypoint = Path(_console_script())
    assert entrypoint.suffix.lower() == ".exe"

    workspace = tmp_path / "native Windows launcher"
    workspace.mkdir()
    result = _run_init(workspace)

    assert result.returncode == 0, result.stderr or result.stdout
    assert (workspace / ".harness").is_dir()


def test_ci_wheel_import_does_not_resolve_from_checkout_src() -> None:
    if os.environ.get("KEEPSAIL_EXPECT_INSTALLED_WHEEL") != "1":
        return

    import keepsail

    package_path = Path(keepsail.__file__).resolve()
    checkout_src = Path(os.environ["GITHUB_WORKSPACE"]).resolve() / "src"
    assert not package_path.is_relative_to(checkout_src)
    assert "site-packages" in {part.lower() for part in package_path.parts}
