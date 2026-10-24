"""Execute the workflow's actual evidence projection against real Git objects."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.unit.core.test_knowledge import git


def projection_program() -> str:
    workflow = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / ".github/workflows/merge-gate.yml").read_text()
    )
    step = next(
        s
        for s in workflow["jobs"]["attest-verify"]["steps"]
        if s.get("name") == "Prepare trusted BASE workspace with exact target evidence"
    )
    return step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


@pytest.mark.parametrize("case", ["valid", "missing-object", "symlink", "wrong-base"])
def test_workflow_projects_only_regular_target_evidence(tmp_path, case):
    source = tmp_path / "source"
    source.mkdir()
    (source / ".harness").mkdir()
    (source / "source.py").write_text("trusted source\n")
    git(source, "init", "-q", "-b", "main")
    git(source, "config", "user.email", "fixture@example.invalid")
    git(source, "config", "user.name", "Projection fixture")
    git(source, "add", ".")
    git(source, "commit", "-qm", "trusted base")
    base = git(source, "rev-parse", "HEAD")
    attest = source / ".harness/attestations/probe.jsonl"
    attest.parent.mkdir(parents=True)
    original = b'{"fixture":"exact original bytes"}\n'
    attest.write_bytes(original)
    (source / "source.py").write_text("candidate source must not be projected\n")
    (source / ".harness/knowledge-recognition.yaml").write_text("candidate policy\n")
    git(source, "add", ".")
    if case == "symlink":
        blob = (
            subprocess.check_output(
                ["git", "hash-object", "-w", "--stdin"], cwd=source, input=b"../../source.py"
            )
            .decode()
            .strip()
        )
        git(
            source,
            "update-index",
            "--cacheinfo",
            f"120000,{blob},.harness/attestations/probe.jsonl",
        )
    git(source, "commit", "-qm", "target evidence and candidate")
    head = git(source, "rev-parse", "HEAD")
    trusted = source / ".harness-trusted-base"
    subprocess.run(["git", "clone", "-q", "--shared", str(source), str(trusted)], check=True)
    git(trusted, "checkout", "-q", "--detach", base)
    result = subprocess.run(
        [sys.executable, "-c", projection_program()],
        capture_output=True,
        env={
            **os.environ,
            "GITHUB_WORKSPACE": str(source),
            "BASE_SHA": head if case == "wrong-base" else base,
            "HEAD_SHA": "0" * 40 if case == "missing-object" else head,
        },
    )
    assert (result.returncode == 0) == (case == "valid"), result.stderr
    assert (trusted / "source.py").read_text() == "trusted source\n"
    assert not (trusted / ".harness/knowledge-recognition.yaml").exists()
    assert git(trusted, "rev-parse", "HEAD") == base
    target = trusted / ".harness/attestations/probe.jsonl"
    if case == "valid":
        assert target.read_bytes() == original
    else:
        assert not target.exists()
