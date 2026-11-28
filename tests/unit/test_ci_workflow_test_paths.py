"""Every test path a CI workflow passes to pytest must exist in the repository.

Guards against deleting or renaming a test file and leaving a CI step that
silently runs nothing (or errors only on the hosted runner).
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
_PATH = re.compile(r"(?<![\w/.-])(tests/[\w./-]+)")


def _pytest_runs():
    for workflow in sorted((ROOT / ".github/workflows").glob("*.yml")):
        data = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        for job_name, job in (data.get("jobs") or {}).items():
            for step in job.get("steps") or []:
                run = step.get("run")
                if isinstance(run, str) and "pytest" in run:
                    yield workflow.name, job_name, run


def test_workflow_pytest_paths_exist():
    referenced = []
    missing = []
    for workflow, job, run in _pytest_runs():
        for token in _PATH.findall(run):
            path = token.split("::", 1)[0].rstrip(".")
            referenced.append(path)
            if not (ROOT / path).exists():
                missing.append(f"{workflow}:{job}: {path}")
    assert referenced, "expected at least one explicit test path in the workflows"
    assert not missing, "workflow pytest steps reference missing paths:\n" + "\n".join(missing)


def test_the_guard_sees_multiline_and_continued_commands():
    runs = [run for _, _, run in _pytest_runs()]
    paths = {path for run in runs for path in _PATH.findall(run)}
    assert "tests/unit/core/test_policy_acceptance.py" in paths
    assert "tests/integration/lifecycle/test_delivery_policy_transition.py" in paths
    assert "tests/unit/cli/test_init_executor.py" in paths
