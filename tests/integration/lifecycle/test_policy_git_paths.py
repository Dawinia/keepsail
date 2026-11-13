"""Git filenames must not be silently changed by the new policy path contract."""

import subprocess

import pytest

from keepsail.core.approval import git_change_manifest
from keepsail.core.git_diff import parse_name_status_z, require_literal_git_diff


def test_backslash_git_object_is_rejected_without_rewriting_legacy_manifest(tmp_path):
    def git(*args, data=None):
        return subprocess.check_output(["git", *args], cwd=tmp_path, input=data).strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "fixture")
    blob = git("hash-object", "-w", "--stdin", data=b"exact content\n").decode()
    empty = git("mktree", "-z", data=b"").decode()
    tree = git("mktree", "-z", data=f"100644 blob {blob}\tsecure\\name.txt\0".encode()).decode()
    base = git("commit-tree", empty, data=b"base\n").decode()
    head = git("commit-tree", tree, "-p", base, data=b"head\n").decode()
    raw = subprocess.check_output(
        ["git", "diff", "--name-status", "-z", base, head], cwd=tmp_path
    ).decode()
    assert parse_name_status_z(raw)[0].paths == ("secure\\name.txt",)
    # Historical code subjects retain their established interpretation. New
    # deliveries reject the ambiguous representation before it grants authority.
    legacy = git_change_manifest(tmp_path, base=base, head=head)
    assert legacy[0]["path"] == "secure/name.txt"
    assert legacy[0]["new"]["blob"] is None
    with pytest.raises(ValueError, match="unsupported literal Git path"):
        require_literal_git_diff(tmp_path, base=base, head=head)
