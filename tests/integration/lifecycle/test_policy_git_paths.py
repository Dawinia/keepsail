"""Git filenames must not be silently changed by the new policy path contract."""

import subprocess

from keepsail.core.approval import git_change_manifest, make_code_subject
from keepsail.core.git_diff import parse_name_status_z, require_literal_git_diff


def test_git_names_with_brackets_keep_their_exact_blob_identity(tmp_path):
    def git(*args, data=None):
        return subprocess.check_output(["git", *args], cwd=tmp_path, input=data).strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "fixture")
    blob = git("hash-object", "-w", "--stdin", data=b"exact content\n").decode()
    empty = git("mktree", "-z", data=b"").decode()
    tree = git("mktree", "-z", data=f"100644 blob {blob}\tnotes[1].md\0".encode()).decode()
    base = git("commit-tree", empty, data=b"base\n").decode()
    head = git("commit-tree", tree, "-p", base, data=b"head\n").decode()
    require_literal_git_diff(tmp_path, base=base, head=head)
    manifest = git_change_manifest(tmp_path, base=base, head=head)
    assert manifest[0]["path"] == "notes[1].md"
    assert manifest[0]["new"]["blob"] == blob


def test_backslash_git_object_has_exact_identity_without_rewriting_legacy_manifest(tmp_path):
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
    # Historical code subjects retain their established interpretation, while
    # new subjects preserve the exact Git filename and blob identity.
    legacy = git_change_manifest(tmp_path, base=base, head=head)
    assert legacy[0]["path"] == "secure/name.txt"
    assert legacy[0]["new"]["blob"] is None
    exact = git_change_manifest(tmp_path, base=base, head=head, literal_paths=True)
    assert exact[0]["path"] == "secure\\name.txt"
    assert exact[0]["new"]["blob"] == blob
    subject = make_code_subject(tmp_path, change_id="delivery", approval_id="approval:test",
                                base=base, head=head, knowledge_basis=None)
    assert subject["path_representation"] == "git-literal/v1"
    assert subject["manifest"] == exact
