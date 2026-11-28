"""Isolated Git repositories for recognition-policy lifecycle tests (no signing).

Shared by the policy transition, adoption and migration tests.  Everything is
real Git and the real CLI in-process; only the verifier "installed from the
base" is built into its own virtual environment.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import venv
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from click.testing import CliRunner, Result

from keepsail.cli import main
from keepsail.core.approval import digest_record, recognition_policy_digest
from keepsail.core.paths import events_path
from keepsail.core.reducer import derive_state
from keepsail.engineering.gitignore_injector import _CANONICAL_PATHS
from keepsail.engineering.verification_config import (
    parse_verification_config,
    required_check_contract,
)

SOURCE = Path(__file__).resolve().parents[3]
OLD_PROCESS = {"id": "old-review", "version": "v1", "issuer": "old-reviewer"}
OWNER_PROCESS = {"id": "owner-plan-review", "version": "owner-plan-review/v1", "issuer": "owner"}
VERIFICATION = {"layers": {"baseline": {"enabled": False},
                           "framework_adapter": {"enabled": False},
                           "user_checks": {"enabled": True}},
                "checks": [{"id": "fixture", "command": [sys.executable, "-c", "print('ok')"]}]}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def checks_digest(verification: dict[str, Any]) -> str:
    return required_check_contract(parse_verification_config(
        yaml.safe_dump(verification), strict=True))["digest"]


def v1_policy(process: dict[str, str] = OLD_PROCESS, *, enabled: bool = True) -> dict[str, Any]:
    raw: dict[str, Any] = {"version": "review-recognition/v1", "enabled": enabled, "process": {
        "id": process["id"], "version": process["version"], "kinds": ["plan", "code"],
        "issuers": [process["issuer"]], "evidence_forms": ["json"]}}
    if enabled:
        raw["process"]["policy_digest"] = recognition_policy_digest(raw)
    return raw


def v2_policy(*, plan: dict[str, str] = OWNER_PROCESS, code: dict[str, str] | None = None,
              code_review: str = "off", scope: list[str] | None = None,
              verification: dict[str, Any] = VERIFICATION,
              builtin: str = "keepsail-baseline/v2") -> dict[str, Any]:
    def process(item: dict[str, str]) -> dict[str, Any]:
        return {"id": item["id"], "version": item["version"], "issuers": [item["issuer"]],
                "evidence_forms": ["json"], "requirements": {}}

    processes = {"plan": process(plan)}
    if code_review != "off" or code is not None:
        processes["code"] = process(code or plan)
    review: dict[str, Any] = {"mode": code_review}
    if code_review == "scope":
        review["scope"] = scope or ["src"]
    raw: dict[str, Any] = {"version": "review-recognition/v2", "enabled": True,
                           "processes_by_kind": processes, "code_review": review,
                           "required_checks_digest": checks_digest(verification),
                           "builtin_checks_version": builtin}
    raw["policy_digest"] = digest_record(raw)
    return raw


def policy_digest(raw: dict[str, Any]) -> str:
    if raw["version"] == "review-recognition/v1":
        return str(raw["process"]["policy_digest"])
    return str(raw["policy_digest"])


class PolicyRepo:
    """A committed trusted base on ``main`` and a ``candidate`` working branch."""

    def __init__(self, root: Path, policy: dict[str, Any] | None, *,
                 verification: dict[str, Any] = VERIFICATION, copy_source: bool = False,
                 extra: dict[str, str] | None = None) -> None:
        self.root = root
        self.harness = root / ".harness"
        self.harness.mkdir(parents=True)
        if copy_source:
            shutil.copytree(SOURCE / "src/keepsail", root / "src/keepsail",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for filename in ("pyproject.toml", "README.md"):
                shutil.copy2(SOURCE / filename, root / filename)
        if policy is not None:
            self.write_policy(policy)
        self.write_verification(verification)
        (root / "plan.md").write_text("# Deliver the approved change\n", encoding="utf-8")
        (root / ".gitignore").write_text("\n".join(_CANONICAL_PATHS) + "\n", encoding="utf-8")
        for name, text in (extra or {}).items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text, encoding="utf-8")
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "fixture@example.invalid")
        git(root, "config", "user.name", "fixture")
        git(root, "config", "core.autocrlf", "false")
        self.base = self.commit("trusted base")
        git(root, "switch", "-qc", "candidate")
        self.runner = CliRunner()

    # -- files and Git -----------------------------------------------------
    def write_policy(self, raw: dict[str, Any] | None) -> None:
        path = self.harness / "review-recognition.yaml"
        if raw is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    def write_verification(self, verification: dict[str, Any]) -> None:
        (self.harness / "verification.yaml").write_text(yaml.safe_dump(verification),
                                                        encoding="utf-8")

    def commit(self, message: str) -> str:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--allow-empty", "-m", message)
        return git(self.root, "rev-parse", "HEAD")

    def advance_main(self, commit: str) -> None:
        git(self.root, "update-ref", "refs/heads/main", commit)

    # -- CLI and lifecycle ---------------------------------------------------
    def cli(self, *args: str, data: Any = None) -> Result:
        text = json.dumps(data) if isinstance(data, (dict, list)) else data
        return self.runner.invoke(main, ["--workspace", str(self.root), *args], input=text)

    def ok(self, *args: str, data: Any = None) -> Result:
        result = self.cli(*args, data=data)
        assert result.exit_code == 0, (args, result.output)
        return result

    def state(self, change: str) -> Any:
        return derive_state(events_path(self.root))[change]

    def evidence(self, change: str, kind: str, subject_id: str, process: dict[str, str],
                 policy: dict[str, Any], *, evidence_id: str | None = None,
                 decision: str = "approve", supersedes: str | None = None) -> dict[str, Any]:
        item = {"version": "review-evidence/v1",
                "evidence_id": evidence_id or f"{kind}-{change}-{process['id']}",
                "kind": kind, "subject_id": subject_id, "decision": decision,
                "process": {"id": process["id"], "version": process["version"]},
                "issuer": process["issuer"], "form": "json",
                "original_evidence": {"decision": decision},
                "provenance": {"policy_digest": policy_digest(policy)}}
        if supersedes is not None:
            item["supersedes"] = supersedes
        return item

    def plan(self, change: str, *, risk_boundary: str | None = None,
             scope: str = "[plan.md]") -> str:
        if change not in derive_state(events_path(self.root)):
            self.ok("change", "start", change, "--framework", "plain")
        args = ["plan", "ready", change, "--plan", "plan.md", "--scope", scope,
                "--commitment", "goal=Deliver the approved change"]
        if risk_boundary is not None:
            args += ["--commitment", f"RISK-BOUNDARY={risk_boundary}"]
        self.ok(*args)
        return str(self.state(change).pending_revision["subject"]["subject_id"])

    def revise(self, change: str, *, risk_boundary: str | None = None) -> str:
        """Submit a plan revision in place (the state does not rewind)."""
        args = ["plan", "redeclare", change, "--reason", "revise the plan", "--plan", "plan.md",
                "--commitment", "goal=Deliver the approved change"]
        if risk_boundary is not None:
            args += ["--commitment", f"RISK-BOUNDARY={risk_boundary}"]
        self.ok(*args)
        return str(self.state(change).pending_revision["subject"]["subject_id"])

    def approve(self, change: str, process: dict[str, str], policy: dict[str, Any], *,
                risk_boundary: str | None = None, start: bool = True) -> str:
        subject = self.plan(change, risk_boundary=risk_boundary)
        self.ok("review", "import", change, "--evidence", "-",
                data=self.evidence(change, "plan", subject, process, policy))
        if start:
            self.ok("implementation", "start", change)
        return subject

    def record(self, change: str, references: list[str]) -> None:
        self.ok("implementation", "record", change, "--assessment", "-", data={
            "affected_commitments": ["goal"], "conclusion": "within_approval",
            "reasons": ["Implement the approved change."], "references": references})

    def code_review(self, change: str, process: dict[str, str], policy: dict[str, Any]) -> None:
        subject = self.state(change).current_code_subject["subject_id"]
        self.ok("review", "import", change, "--evidence", "-",
                data=self.evidence(change, "code", subject, process, policy))

    def attest(self, change: str) -> dict[str, Any]:
        from keepsail.core.attestation_v3 import parse_v3_line

        self.ok("attest", "write", change)
        path = self.harness / f"attestations/v3/{change}.jsonl"
        record = parse_v3_line(path.read_bytes())
        git(self.root, "add", path.relative_to(self.root).as_posix())
        git(self.root, "commit", "-qm", f"retain {change} evidence")
        return record

    def verify(self, base: str, head: str = "HEAD") -> Result:
        return self.cli("--json", "attest", "verify", "--base", base, "--head", head)


def verify_with_installed_base(root: Path, base: str, head: str, *, label: str,
                               source_ref: str | None = None) -> subprocess.CompletedProcess[str]:
    """Build and install the verifier from the exact base, then block Python networking.

    ``source_ref`` builds a different commit of *this* repository instead (the
    migration test pins the previous release this way).
    """
    area = root.parent / f"{root.name}-{label}"
    checkout = area / "trusted"
    wheels = area / "wheels"
    environment = area / "venv"
    area.mkdir()
    git(root, "clone", "-q", "--shared", "--no-checkout", "-c", "core.autocrlf=false",
        str(root), str(checkout))
    git(checkout, "checkout", "-q", "--detach", base)
    build_from = checkout
    if source_ref is not None:
        build_from = area / "source"
        git(SOURCE, "worktree", "add", "-q", "--detach", str(build_from), source_ref)
    wheels.mkdir()
    env_python = install_wheel(build_from, wheels, environment)
    if source_ref is not None:
        git(SOURCE, "worktree", "remove", "--force", str(build_from))
    probe = subprocess.check_output(
        [str(env_python), "-I", "-c",
         "import hashlib,pathlib,keepsail.cli.attest as m; "
         "p=pathlib.Path(m.__file__).resolve(); print(p); "
         "print(hashlib.sha256(p.read_bytes()).hexdigest())"], text=True,
    ).splitlines()
    assert "site-packages" in probe[0]
    if source_ref is None:
        committed = subprocess.check_output(
            ["git", "show", f"{base}:src/keepsail/cli/attest.py"], cwd=root)
        assert probe[1] == sha256(committed).hexdigest()
    entries = subprocess.check_output(
        ["git", "ls-tree", "-rz", head, "--", ".harness/attestations"], cwd=checkout)
    for entry in filter(None, entries.split(b"\0")):
        header, raw_path = entry.split(b"\t", 1)
        mode, kind, oid = header.split()
        relative = Path(raw_path.decode("utf-8"))
        assert mode in {b"100644", b"100755"} and kind == b"blob"
        assert relative.parts[:2] == (".harness", "attestations")
        assert relative.suffix == ".jsonl" and ".." not in relative.parts
        destination = checkout / relative
        assert destination.resolve().is_relative_to(checkout.resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(subprocess.check_output(["git", "cat-file", "blob", oid.decode()],
                                                        cwd=checkout))
    program = (
        "import socket\n"
        "def blocked(*a, **k): raise RuntimeError('network disabled for verifier')\n"
        "socket.create_connection=blocked\n"
        "socket.socket.connect=blocked\n"
        "socket.socket.connect_ex=blocked\n"
        "socket.getaddrinfo=blocked\n"
        "from keepsail.cli import main\n"
        "main()\n"
    )
    help_text = subprocess.check_output(
        [str(env_python), "-I", "-c", "from keepsail.cli import main; main()", "attest", "verify",
         "--help"], cwd=checkout, text=True,
    )
    args = [str(env_python), "-I", "-c", program, "--workspace", str(checkout), "--json",
            "attest", "verify", "--base", base, "--head", head]
    if "--repository-id" in help_text:
        # Existing workflows pass host identity; the new verifier reports it as given.
        args.extend(["--repository-id", "owner/project", "--target-ref", "refs/heads/main"])
    if os.environ.get("KEEPSAIL_TEST_NETWORK_NAMESPACE") == "1":
        assert sys.platform.startswith("linux"), "network namespace acceptance requires Linux"
        program = (
            "import errno, socket\n"
            "try: socket.create_connection(('192.0.2.1', 9), timeout=2)\n"
            "except OSError as exc:\n"
            "    if exc.errno != errno.ENETUNREACH: raise\n"
            "else: raise AssertionError('network namespace is not isolated')\n"
        ) + program
        args[3] = program
        args = ["sudo", "unshare", "--net", f"--setgid={os.getgid()}",
                f"--setuid={os.getuid()}", "--", *args]
    return subprocess.run(
        args, cwd=checkout, capture_output=True, text=True,
        env={**os.environ, "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0"},
        timeout=300,
    )


def install_wheel(source: Path, wheels: Path, environment: Path) -> Path:
    uv_name = "uv.exe" if os.name == "nt" else "uv"
    adjacent_uv = Path(sys.executable).parent / uv_name
    uv = str(adjacent_uv) if adjacent_uv.is_file() else shutil.which("uv")
    env_python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if uv:
        subprocess.run([uv, "build", "--wheel", "--out-dir", str(wheels), str(source)],
                       check=True, capture_output=True)
        subprocess.run([uv, "venv", "--python", sys.executable, str(environment)],
                       check=True, capture_output=True)
        wheel = next(wheels.glob("keepsail-*.whl"))
        subprocess.run([uv, "pip", "install", "--python", str(env_python), str(wheel)],
                       check=True, capture_output=True)
    else:
        subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir",
                        str(wheels), str(source)], check=True, capture_output=True)
        venv.EnvBuilder(with_pip=True).create(environment)
        wheel = next(wheels.glob("keepsail-*.whl"))
        subprocess.run([str(env_python), "-m", "pip", "install", str(wheel)],
                       check=True, capture_output=True)
    return env_python


def edited(raw: dict[str, Any], **changes: Any) -> dict[str, Any]:
    value = deepcopy(raw)
    value.update(changes)
    if value["version"] == "review-recognition/v2":
        value["policy_digest"] = digest_record({k: v for k, v in value.items()
                                                if k != "policy_digest"})
    return value
