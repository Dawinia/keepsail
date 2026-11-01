"""Contract tests for the new plan-authority/evidence predicates."""

import subprocess
from pathlib import Path

import pytest
import yaml

from keepsail.core.approval import (
    ApprovalError,
    approval_record,
    artifact_digest,
    digest_record,
    load_recognition,
    make_code_subject,
    make_plan_subject,
    recognition_contract_active,
    recognition_policy_digest,
    resolve_contract_base,
    validate_evidence,
    validate_evidence_reuse,
    validate_implementation_assessment,
    validate_plan_subject,
)


def test_plan_subject_rejects_duplicate_artifacts_and_tampered_digest(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("# plan\n", encoding="utf-8")
    subject = make_plan_subject(
        tmp_path,
        change_id="c",
        artifacts=[("plan.md", "plan")],
        commitments=[{"id": "goal", "text": "ship it"}],
    )
    assert validate_plan_subject(subject, change_id="c")["subject_id"] == subject["subject_id"]
    subject["artifacts"][0]["content"] = "changed\n"
    with pytest.raises(ApprovalError, match="digest"):
        validate_plan_subject(subject, change_id="c")


def test_plan_text_digest_normalizes_line_endings() -> None:
    assert artifact_digest("a\r\nb\r\n") == artifact_digest("a\nb\n")


def test_automatic_coverage_tracks_git_and_workspace_without_unrelated_untracked(tmp_path):
    from keepsail.core.approval import implementation_coverage, validate_generated_coverage

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    for name in ("old.py", "delete.py", "space file.py", "源 文件.py", "cancel.py"):
        (tmp_path / name).write_text("original\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "base")
    git("switch", "-qc", "candidate")
    git("mv", "old.py", "new.py")
    (tmp_path / "delete.py").unlink()
    (tmp_path / "源 文件.py").write_text("committed\n", encoding="utf-8")
    git("add", "-u")
    git("commit", "-qm", "committed rename, deletion and unicode change")
    (tmp_path / "space file.py").write_text("unstaged\n", encoding="utf-8")
    (tmp_path / "cancel.py").write_text("staged change\n", encoding="utf-8")
    git("add", "cancel.py")
    (tmp_path / "cancel.py").write_text("original\n", encoding="utf-8")
    assert "cancel.py" not in git("diff", "HEAD", "--name-only")
    assert "cancel.py" in git("diff", "--cached", "--name-only")
    assert "cancel.py" in git("diff", "--name-only")
    for name in ("staged.py", "include me.py", "other task.py"):
        (tmp_path / name).write_text("new\n", encoding="utf-8")
    attestations = tmp_path / ".harness/attestations"
    attestations.mkdir(parents=True)
    (attestations / "a.jsonl").write_text("{}\n")
    (attestations / "tool.py").write_text("pass\n")
    git("add", "staged.py", ".harness/attestations")
    coverage, basis = implementation_coverage(tmp_path, include_paths=["include me.py"])
    assert {row["path"] for row in coverage} == {
        "old.py", "new.py", "delete.py", "源 文件.py", "space file.py", "staged.py",
        "include me.py", ".harness/attestations/tool.py", "cancel.py",
    }
    validate_generated_coverage(tmp_path, {"coverage": coverage, "coverage_basis": basis})
    (tmp_path / "space file.py").write_text("concurrent change\n", encoding="utf-8")
    with pytest.raises(ApprovalError, match="inputs changed"):
        validate_generated_coverage(tmp_path, {"coverage": coverage, "coverage_basis": basis})
    with pytest.raises(ApprovalError, match="outside the workspace"):
        implementation_coverage(tmp_path, include_paths=["../outside.py"])


def test_automatic_coverage_does_not_turn_git_failure_into_empty_coverage(tmp_path, monkeypatch):
    import keepsail.core.approval as approval
    from keepsail.core.scope_match import GitScopeError

    for args in (("init", "-q", "-b", "main"), ("config", "user.email", "test@example.com"),
                 ("config", "user.name", "Test"), ("commit", "-qm", "base", "--allow-empty")):
        subprocess.run(["git", *args], cwd=tmp_path, check=True)

    def failed(*args):
        raise GitScopeError("test Git failure")

    monkeypatch.setattr(approval, "_git", failed)
    with pytest.raises((ApprovalError, GitScopeError)):
        approval.implementation_coverage(tmp_path)


def test_recognition_can_be_loaded_from_a_trusted_git_ref(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    harness = tmp_path / ".harness"
    harness.mkdir()
    policy = {
        "version": "review-recognition/v1",
        "enabled": True,
        "process": {
            "id": "owner-review",
            "version": "1",
            "kinds": ["plan", "code"],
            "issuers": ["owner"],
            "evidence_forms": ["json"],
        },
    }
    policy["process"]["policy_digest"] = recognition_policy_digest(policy)
    (harness / "review-recognition.yaml").write_text(
        yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "recognition"], cwd=tmp_path, check=True)
    ref = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()

    (harness / "review-recognition.yaml").write_text(
        policy["version"] + "\nenabled: false\n", encoding="utf-8"
    )

    assert load_recognition(tmp_path, ref=ref).process_id == "owner-review"
    with pytest.raises(ApprovalError, match="enabled"):
        load_recognition(tmp_path)


def test_evidence_rejects_empty_original_and_unknown_version() -> None:
    base = {
        "version": "review-evidence/v1",
        "evidence_id": "e1",
        "kind": "plan",
        "subject_id": "plan:x",
        "decision": "approve",
        "process": {"id": "p", "version": "1"},
        "issuer": "owner",
        "original_evidence": {"verdict": "approve"},
        "provenance": {"change_id": "c"},
    }
    assert validate_evidence(base, change_id="c")["evidence_id"] == "e1"
    empty = {**base, "original_evidence": {}}
    with pytest.raises(ApprovalError, match="original evidence"):
        validate_evidence(empty)
    unknown = {**base, "version": "review-evidence/v0"}
    with pytest.raises(ApprovalError, match="version"):
        validate_evidence(unknown)


def test_evidence_replacement_must_supersede_latest_subject_conclusion() -> None:
    base = {
        "version": "review-evidence/v1",
        "evidence_id": "e1",
        "kind": "plan",
        "subject_id": "plan:x",
        "decision": "approve",
        "process": {"id": "p", "version": "1"},
        "issuer": "owner",
        "original_evidence": {"verdict": "approve"},
        "provenance": {"change_id": "c"},
    }
    assert validate_evidence_reuse(base, [], subject_id="plan:x") == "new"
    with pytest.raises(ApprovalError, match="supersede"):
        validate_evidence_reuse(
            {**base, "evidence_id": "e2", "decision": "reject"},
            [base],
            subject_id="plan:x",
        )
    assert (
        validate_evidence_reuse(
            {**base, "evidence_id": "e2", "decision": "reject", "supersedes": "e1"},
            [base],
            subject_id="plan:x",
        )
        == "new"
    )
    with pytest.raises(ApprovalError, match="current conclusion"):
        validate_evidence_reuse(
            {**base, "evidence_id": "e3", "supersedes": "unrelated"},
            [base],
            subject_id="plan:x",
        )


def test_code_subject_contains_rename_mode_and_blob_identity(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    old = tmp_path / "old.py"
    old.write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "old.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    old.rename(tmp_path / "new.py")
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "rename"], cwd=tmp_path, check=True)
    subject = make_code_subject(
        tmp_path,
        change_id="c",
        approval_id="approval:e1",
        base=base,
    )
    assert subject["manifest"]
    assert subject["manifest"][0]["path"] == "new.py"
    assert subject["manifest"][0]["old_path"] == "old.py"
    assert subject["subject_id"].startswith("code:")
    unsigned = {key: value for key, value in subject.items() if key not in {"subject_id", "head"}}
    assert subject["subject_id"] == f"code:{digest_record(unsigned)}"


def test_code_subject_uses_merge_base_when_target_branch_advances(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    shared = tmp_path / "shared.py"
    shared.write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "shared.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-qb", "candidate"], cwd=tmp_path, check=True)
    shared.write_text("value = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "shared.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate change"], cwd=tmp_path, check=True)
    candidate_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    subprocess.run(["git", "checkout", "main", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "target-only.py").write_text("target = True\n", encoding="utf-8")
    subprocess.run(["git", "add", "target-only.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "target branch advanced"], cwd=tmp_path, check=True)
    advanced_base = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    subprocess.run(["git", "checkout", "candidate", "-q"], cwd=tmp_path, check=True)

    subject = make_code_subject(
        tmp_path,
        change_id="c",
        approval_id="approval:e1",
        base=advanced_base,
        head=candidate_head,
    )

    merge_base = subprocess.check_output(
        ["git", "merge-base", advanced_base, candidate_head], cwd=tmp_path, text=True
    ).strip()
    assert subject["base"] == merge_base
    assert [row["path"] for row in subject["manifest"]] == ["shared.py"]


def test_new_contract_base_ignores_legacy_review_governance(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "review-governance.yaml").write_text(
        "review:\n  base_branch: unrelated\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)

    assert len(resolve_contract_base(tmp_path)) == 40


def test_base_lookup_is_bounded_and_tracks_live_ref_priority(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("commit", "--allow-empty", "-qm", "first")
    first = git("rev-parse", "HEAD")
    git("commit", "--allow-empty", "-qm", "second")
    second = git("rev-parse", "HEAD")
    git("update-ref", "refs/heads/main", first)
    git("tag", "main", second)
    git("tag", "origin/main", second)
    git("update-ref", "--no-deref", "refs/remotes/origin/HEAD", second)
    original_run = subprocess.run

    def resolve(max_calls=1):
        calls = []

        def tracked(*args, **kwargs):
            calls.append(args[0])
            return original_run(*args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(subprocess, "run", tracked)
            value = resolve_contract_base(tmp_path)
        assert 1 <= len(calls) <= max_calls, calls
        return value

    assert resolve() == first
    git("update-ref", "refs/remotes/origin/main", second)
    assert resolve() == second
    git("update-ref", "refs/remotes/origin/trunk", first)
    git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    assert resolve() == first
    git("update-ref", "refs/remotes/origin/trunk", second)
    assert resolve() == second
    git("tag", "-a", "authority-base", "-m", "annotated", first)
    git("update-ref", "refs/remotes/origin/trunk", git("rev-parse", "refs/tags/authority-base"))
    assert resolve(max_calls=2) == first
    # A non-commit preferred ref must not become authority or hide the valid fallback.
    git("update-ref", "refs/remotes/origin/trunk", git("rev-parse", first + "^{tree}"))
    assert resolve() == second
    for ref in ("refs/remotes/origin/trunk", "refs/remotes/origin/main", "refs/heads/main"):
        git("update-ref", "-d", ref)
    with pytest.raises(ApprovalError, match="reachable trusted baseline"):
        resolve_contract_base(tmp_path)


def test_recognition_contract_activation_fails_closed(tmp_path: Path) -> None:
    harness = tmp_path / ".harness"
    harness.mkdir()
    path = harness / "review-recognition.yaml"
    path.write_text("version: review-recognition/v1\nenabled: false\n", encoding="utf-8")
    assert recognition_contract_active(tmp_path) is False

    policy = {
        "version": "review-recognition/v1",
        "enabled": True,
        "process": {
            "id": "owner-review",
            "version": "1",
            "kinds": ["plan", "code"],
            "issuers": ["owner"],
            "evidence_forms": ["json"],
            "requirements": {"substantive": ["scope", "tests"]},
        },
    }
    policy["process"]["policy_digest"] = recognition_policy_digest(policy)
    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    assert recognition_contract_active(tmp_path) is True

    assert load_recognition(tmp_path).requirements == {"substantive": ["scope", "tests"]}

    path.write_text("version: review-recognition/v1\nenabled: true\n", encoding="utf-8")
    with pytest.raises(ApprovalError):
        recognition_contract_active(tmp_path)

    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "enable recognition"], cwd=tmp_path, check=True)
    path.write_text("version: review-recognition/v1\nenabled: false\n", encoding="utf-8")
    assert recognition_contract_active(tmp_path) is True


def test_recognition_contract_uses_default_remote_head_and_skips_disabled_ref(
    tmp_path: Path,
) -> None:
    harness = tmp_path / ".harness"
    harness.mkdir()
    path = harness / "review-recognition.yaml"
    policy = {
        "version": "review-recognition/v1",
        "enabled": True,
        "process": {
            "id": "owner-review",
            "version": "1",
            "kinds": ["plan", "code"],
            "issuers": ["owner"],
            "evidence_forms": ["json"],
        },
    }
    policy["process"]["policy_digest"] = recognition_policy_digest(policy)
    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "enabled main"], cwd=tmp_path, check=True)
    main_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()

    path.write_text("version: review-recognition/v1\nenabled: false\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "disabled remote"], cwd=tmp_path, check=True)
    disabled_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", disabled_commit],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "update-ref", "refs/heads/main", main_commit], cwd=tmp_path, check=True)

    assert recognition_contract_active(tmp_path) is True

    # Enumeration can fail on a corrupt ref while the trusted main stays readable.
    (tmp_path / ".git/refs/remotes/origin/HEAD").write_text("f" * 40 + "\n")
    assert subprocess.check_output(
        ["git", "rev-parse", "--verify", "refs/heads/main^{commit}"],
        cwd=tmp_path, text=True,
    ).strip() == main_commit
    with pytest.raises(ApprovalError, match="trusted baseline refs"):
        recognition_contract_active(tmp_path)


def test_implementation_assessment_requires_auditable_references(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("# plan\n", encoding="utf-8")
    subject = make_plan_subject(
        tmp_path,
        change_id="c",
        artifacts=[("plan.md", "plan")],
        commitments=[{"id": "goal", "text": "ship it"}],
    )
    approval = approval_record(subject=subject, evidence_id="e1", evidence_digest="digest")
    valid = {
        "approval_id": approval["approval_id"],
        "change_id": "c",
        "affected_commitments": ["goal"],
        "conclusion": "implemented",
        "reasons": ["the committed change covers the goal"],
        "references": [{"path": "src/app.py"}],
    }
    assert validate_implementation_assessment(valid, approval=approval, change_id="c") == valid
    with pytest.raises(ApprovalError, match="commitment"):
        validate_implementation_assessment(
            {**valid, "affected_commitments": ["unknown"]},
            approval=approval,
            change_id="c",
        )
    with pytest.raises(ApprovalError, match="conclusion"):
        validate_implementation_assessment(
            {**valid, "conclusion": ""}, approval=approval, change_id="c"
        )
