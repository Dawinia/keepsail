"""Read-only per-occurrence legacy-name inventory (tracked files, including hidden)."""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

PATTERN = re.compile(
    r"super[-_ ]harness|superharness|(?<![A-Za-z0-9_])sh(?![A-Za-z0-9_])", re.IGNORECASE
)
REPORT = "docs/keepsail-name-audit.md"


def category(path: str, line: str, token: str) -> str:
    if (path.startswith(("docs/plans/", "docs/decisions/", ".harness/attestations/"))
            or path == "docs/product-foundations.md" or "/.harness/" in path):
        return "historical"
    if path == "LICENSE":
        return "copyright-attribution"
    if path == ".harness/review-recognition.yaml":
        return "recognized-policy-digest-preserved"
    if path == ".gitignore":
        return "stable-managed-identity-and-explanation"
    if path == "scripts/audit_brand_names.py":
        return "inventory-scanner-pattern"
    if token.lower() == "sh":
        return "system-shell"
    if token.lower() == "super_harness":
        return "import-or-environment-compatibility"
    if "github.com/Dawinia/super-harness" in line:
        return "existing-repository-link"
    if path.startswith("tests/"):
        return "legacy-compatibility-test"
    if path in {"README.md", "README.zh-CN.md", "docs/keepsail-migration.md", REPORT}:
        return "migration-explanation"
    if ("<!--" in line or "super-harness version" in line
            or "super-harness.yml" in line or "super-harness-backup" in line
            or "super-harness.lock" in line or "super-harness gitignore" in line):
        return "stable-protocol-or-managed-identity"
    if path == "pyproject.toml" or 'cli="$verifier/super-harness"' in line:
        return "legacy-console-or-trusted-base"
    return "UNCLASSIFIED"


def scan(root: Path) -> list[dict[str, object]]:
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    rows: list[dict[str, object]] = []
    for path in paths:
        if not path or path == REPORT:
            continue  # The derived report is excluded to avoid recursive counts.
        text = (root / path).read_text(encoding="utf-8")
        counts: Counter[str] = Counter()
        findings = []
        for number, line in enumerate(text.splitlines(), 1):
            for match in PATTERN.finditer(line):
                kind = category(path, line, match.group())
                counts[kind] += 1
                findings.append({"line": number, "token": match.group(), "category": kind})
        if findings or PATTERN.search(path):
            rows.append({"path": path, "counts": dict(sorted(counts.items())),
                         "occurrences": findings})
    return rows


if __name__ == "__main__":
    result = scan(Path(__file__).resolve().parents[1])
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(int(any("UNCLASSIFIED" in row["counts"] for row in result)))
