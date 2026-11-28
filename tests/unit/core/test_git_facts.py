"""Operation-scoped reuse of immutable Git facts (plan C4)."""

import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from keepsail.core import git_facts, git_objects
from keepsail.core.approval import ApprovalError
from keepsail.core.git_facts import GitFactCache, git_fact_scope, memoized
from keepsail.core.git_objects import (
    optional_regular_blob_bytes,
    regular_blob_text,
    regular_blob_texts,
)
from keepsail.core.scope_match import (
    GitScopeError,
    is_ancestor,
    merge_base_commit,
    resolve_commit,
)
from tests.git_counter import count_git


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def repo(tmp_path):
    harness = tmp_path / ".harness"
    harness.mkdir()
    (harness / "review-recognition.yaml").write_bytes(b"enabled: false\n")
    (harness / "verification.yaml").write_bytes(b"checks: []\n")
    (harness / "bad.yaml").write_bytes(b"\xff\xfe")
    (harness / "nested").mkdir()
    (harness / "nested/file.txt").write_bytes(b"nested\n")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "fixture")
    git(tmp_path, "config", "core.autocrlf", "false")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "one")
    first = git(tmp_path, "rev-parse", "HEAD")
    (harness / "verification.yaml").write_bytes(b"checks: [] # two\n")
    git(tmp_path, "commit", "-qam", "two")
    return tmp_path, first, git(tmp_path, "rev-parse", "HEAD")


def test_no_scope_means_no_caching(repo, monkeypatch):
    root, first, _ = repo
    with count_git(monkeypatch) as calls:
        for _ in range(2):
            regular_blob_text(root, first, ".harness/verification.yaml")
            resolve_commit(root, first)
    assert calls.total == 6  # ls-tree + cat-file + rev-parse, twice
    assert git_facts.active_cache() is None


def test_object_ids_are_reused_but_refs_are_always_reread(repo, monkeypatch):
    root, first, second = repo
    with count_git(monkeypatch) as calls, git_fact_scope():
        for _ in range(3):
            assert regular_blob_text(root, first, ".harness/verification.yaml") == "checks: []\n"
            assert regular_blob_text(root, first, ".harness/review-recognition.yaml")
            assert resolve_commit(root, first) == first
            assert is_ancestor(root, first, second)
            assert merge_base_commit(root, first, second) == first
        once = calls.total
        for _ in range(3):
            assert resolve_commit(root, "HEAD") == second
            assert regular_blob_text(root, "HEAD", ".harness/verification.yaml")
    # One .harness listing, one persistent cat-file, rev-parse, is-ancestor, merge-base.
    assert once == 5
    assert calls.named("cat-file") == 1
    # HEAD is mutable: every read re-runs rev-parse and ls-tree (blobs are OID-keyed).
    assert calls.total - once == 3 + 3


def test_missing_paths_are_cached_and_failures_are_not(repo, monkeypatch):
    root, first, _ = repo
    with count_git(monkeypatch) as calls, git_fact_scope():
        assert optional_regular_blob_bytes(root, first, ".harness/absent.yaml") is None
        assert optional_regular_blob_bytes(root, first, ".harness/absent.yaml") is None
        assert calls.total == 1
        for _ in range(2):
            with pytest.raises(GitScopeError):
                resolve_commit(root, "f" * 40)
        assert calls.named("rev-parse") == 2


def test_successive_scopes_share_nothing_and_close_the_reader(repo, monkeypatch):
    root, first, _ = repo
    with git_fact_scope() as cache:
        regular_blob_text(root, first, ".harness/verification.yaml")
        reader = cache.resource(git_facts.root_key(root), lambda: None)
        assert reader is not None and reader._process.poll() is None
        assert len(cache)
    assert reader._process.poll() is not None  # closed at the end of the operation
    with count_git(monkeypatch) as calls, git_fact_scope() as fresh:
        assert len(fresh) == 0
        regular_blob_text(root, first, ".harness/verification.yaml")
    assert calls.total == 2


def test_nested_scope_reuses_the_outer_operation(repo):
    with git_fact_scope() as outer, git_fact_scope() as inner:
        assert outer is inner


def test_entry_and_byte_limits_evict_least_recently_used():
    cache = GitFactCache(max_entries=3, max_bytes=10)
    for index in range(4):
        cache.put(("k", index), b"x")
    assert len(cache) == 3 and cache.get(("k", 0)) is git_facts._MISSING
    cache.get(("k", 1))
    cache.put(("big",), b"123456789")
    assert cache.size_bytes <= 10 and cache.get(("big",)) == b"123456789"
    cache.put(("huge",), b"x" * 11)  # larger than the whole budget: never cached
    assert cache.get(("huge",)) is git_facts._MISSING


def test_concurrent_reads_and_writes_keep_limits_consistent():
    cache = GitFactCache(max_entries=50, max_bytes=500)

    def work(thread):
        for index in range(500):
            cache.put((thread, index % 80), b"abcde")
            cache.get((thread, (index * 7) % 80))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(work, range(8)))
    assert len(cache) <= 50 and cache.size_bytes <= 500
    assert cache.size_bytes == 5 * len(cache)


def test_threads_sharing_the_batch_reader_each_get_their_own_object(repo):
    root, first, second = repo
    expected = {first: "checks: []\n", second: "checks: [] # two\n"}
    with git_fact_scope() as cache:
        oids = {}
        for commit in expected:
            listing = git(root, "ls-tree", commit, "--", ".harness/verification.yaml")
            oids[commit] = listing.split()[2]
        reader = cache.resource(git_facts.root_key(root), lambda: git_objects._BatchReader(root))
        barrier = threading.Barrier(8)

        def fetch(index):
            commit = list(expected)[index % 2]
            barrier.wait(timeout=30)
            results = []
            for _ in range(25):
                kind, data = reader.read(oids[commit])
                results.append((commit, kind, data.decode("utf-8")))
            return results

        with ThreadPoolExecutor(max_workers=8) as pool:
            batches = list(pool.map(fetch, range(8), timeout=120))
    for batch in batches:
        for commit, kind, text in batch:
            assert kind == b"blob" and text == expected[commit]


@pytest.mark.parametrize("scoped", [False, True])
def test_batch_and_persistent_reads_fail_as_before(repo, scoped):
    root, first, _ = repo
    import contextlib

    context = git_fact_scope() if scoped else contextlib.nullcontext()
    with context:
        with pytest.raises(ApprovalError, match="not a regular blob"):
            regular_blob_text(root, first, ".harness/nested")
        with pytest.raises(ApprovalError, match="missing"):
            regular_blob_text(root, first, ".harness/absent.yaml")
        with pytest.raises(ApprovalError, match="not UTF-8"):
            regular_blob_text(root, first, ".harness/bad.yaml")
        with pytest.raises(ApprovalError, match=r"not exact regular blobs|not a regular blob"):
            regular_blob_texts(root, first, [".harness/nested", ".harness/verification.yaml"])
        with pytest.raises(ApprovalError, match="missing"):
            regular_blob_texts(root, first, [".harness/absent.yaml"])
        with pytest.raises(ApprovalError, match="not UTF-8"):
            regular_blob_texts(root, first, [".harness/bad.yaml"])
        with pytest.raises(ApprovalError, match="unique"):
            regular_blob_texts(root, first, [".harness/bad.yaml", ".harness/bad.yaml"])
        assert regular_blob_texts(root, first, [".harness/verification.yaml"]) == {
            ".harness/verification.yaml": "checks: []\n"}


class _FakeProcess:
    def __init__(self, output):
        import io

        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO(output)
        self.exited = False

    def poll(self):
        return 0 if self.exited else None


@pytest.mark.parametrize(("output", "message"), [
    (b"", "ended before answering"),
    (b"deadbeef missing\n", "missing"),
    (b"other blob 3\nabc\n", "header"),
    (b"OID blob 10\nabc", "truncated"),
    (b"OID blob x\n", "batch failed"),
])
def test_persistent_reader_protocol_anomalies_fail_closed(repo, output, message):
    root, _, _ = repo
    reader = git_objects._BatchReader(root)
    reader.close()
    oid = "a" * 40
    reader._process = _FakeProcess(output.replace(b"OID", oid.encode()).replace(
        b"deadbeef", oid.encode()))
    with pytest.raises(ApprovalError, match=message):
        reader.read(oid)
    reader._process.exited = True
    with pytest.raises(ApprovalError, match="exited"):
        reader.read(oid)


def test_memoized_caches_only_successful_results():
    attempts = []

    def compute():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("transient")
        return "value"

    with git_fact_scope():
        with pytest.raises(RuntimeError):
            memoized(("k",), compute, cacheable=True)
        assert memoized(("k",), compute, cacheable=True) == "value"
        assert memoized(("k",), compute, cacheable=True) == "value"
    assert len(attempts) == 2


def test_cli_operations_and_thread_pool_tasks_run_in_the_scope(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from keepsail.cli import main

    seen = {}
    original = git_facts.active_cache

    def report_cmd(*args, **kwargs):
        seen["report"] = original()
        raise SystemExit(0)

    monkeypatch.setattr("keepsail.cli.report.build_value_report", report_cmd)
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness/events.jsonl").touch()
    CliRunner().invoke(main, ["--workspace", str(tmp_path), "report"])
    assert isinstance(seen["report"], GitFactCache)
    assert original() is None

    from keepsail.sensors import verification_runner

    tasks_seen = []
    with git_fact_scope() as cache:
        import contextvars

        with ThreadPoolExecutor(max_workers=2) as pool:
            for future in [pool.submit(contextvars.copy_context().run, original)
                           for _ in range(4)]:
                tasks_seen.append(future.result())
    assert all(item is cache for item in tasks_seen)
    source = (verification_runner.__file__)
    text = open(source, encoding="utf-8").read()
    assert "pool.submit(contextvars.copy_context().run, run_task, task)" in text
    from keepsail.sensors import dispatcher

    assert "contextvars.copy_context().run, self._safe_run" in open(
        dispatcher.__file__, encoding="utf-8").read()
    assert sys.modules["keepsail.core.git_facts"] is git_facts
