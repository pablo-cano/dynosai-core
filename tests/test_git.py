"""Deterministic tests for SPEC-003 Git relationship inspection."""

from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

import dynosai.git as git_module
from dynosai.git import GitInspectionResult, inspect_git_relationship


@pytest.fixture
def git_fixtures(tmp_path: pathlib.Path) -> dict[str, pathlib.Path]:
    """Create disposable local repositories, including paths containing spaces."""
    root = tmp_path / "fixture with spaces"
    root.mkdir()
    repository = root / "repository with spaces"
    repository.mkdir()
    outside = root / "outside directory"
    outside.mkdir()
    bare = root / "bare repository"
    worktree = root / "linked worktree"
    _git(repository, "init", "-q")
    nested = repository / "nested directory" / "deeper directory"
    nested.mkdir(parents=True)
    (repository / "tracked.txt").write_text("fixture\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(
        repository,
        "-c",
        "user.name=DynosAI Test",
        "-c",
        "user.email=dynosai-test@example.invalid",
        "-c",
        "commit.gpgSign=false",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    _git(root, "init", "--bare", "-q", str(bare))
    _git(repository, "worktree", "add", "--detach", "-q", str(worktree), "HEAD")
    return {
        "root": repository,
        "nested": nested,
        "outside": outside,
        "bare": bare,
        "worktree": worktree,
    }


def _git(directory: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=True,
            shell=False,
        )
    except FileNotFoundError:
        pytest.skip("Git is unavailable for disposable fixture setup")
    return result


def _tree_snapshot(directory: pathlib.Path) -> dict[str, tuple[int, int, int]]:
    snapshot: dict[str, tuple[int, int, int]] = {}
    for current, names, files in os.walk(directory):
        for name in [*names, *files]:
            path = pathlib.Path(current) / name
            stat = path.stat()
            snapshot[str(path.relative_to(directory))] = (
                stat.st_mode,
                stat.st_size,
                stat.st_mtime_ns,
            )
    return snapshot


def test_root_descendant_spaces_and_repeated_calls(
    git_fixtures: dict[str, pathlib.Path],
) -> None:
    repository = git_fixtures["root"].resolve()
    nested = git_fixtures["nested"].resolve()
    root_result = inspect_git_relationship(repository)
    nested_result = inspect_git_relationship(nested)
    assert root_result == GitInspectionResult(True, "root", repository)
    assert nested_result == GitInspectionResult(True, "descendant", repository)
    assert inspect_git_relationship(nested) == nested_result
    assert " " in str(repository)


def test_linked_worktree_reports_its_own_root(
    git_fixtures: dict[str, pathlib.Path],
) -> None:
    linked = git_fixtures["worktree"].resolve()
    main = git_fixtures["root"].resolve()
    result = inspect_git_relationship(linked)
    assert result == GitInspectionResult(True, "root", linked)
    assert result.repository_root != main


def test_outside_repository_and_bare_repository_have_no_relationship(
    git_fixtures: dict[str, pathlib.Path],
) -> None:
    assert inspect_git_relationship(git_fixtures["outside"].resolve()) == GitInspectionResult(
        True, "none", None
    )
    assert inspect_git_relationship(git_fixtures["bare"].resolve()) == GitInspectionResult(
        True, "none", None
    )


def test_inspection_does_not_consume_development_overlays(
    git_fixtures: dict[str, pathlib.Path],
) -> None:
    repository = git_fixtures["root"].resolve()
    fixture_root = repository.parent

    result = inspect_git_relationship(repository)

    assert result == GitInspectionResult(True, "root", repository)
    assert not (fixture_root / ".dynos").exists()
    assert not (fixture_root / ".specify").exists()
    assert not (fixture_root / ".grok").exists()
    assert not (fixture_root / "specs").exists()


@pytest.mark.parametrize(
    "stdout, stderr",
    [
        ("", "fatal: not a git repository\\n"),
        ("unexpected\\n", "fatal: not a git repository (or any of the parent directories): .git\\n"),
    ],
)
def test_near_miss_outside_repository_result_is_unexpected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    stdout: str,
    stderr: str,
) -> None:
    completed = subprocess.CompletedProcess([], 128, stdout, stderr)
    monkeypatch.setattr(git_module, "_run_git", lambda *args, **kwargs: completed)
    with pytest.raises(subprocess.CalledProcessError):
        inspect_git_relationship(tmp_path.resolve())


def test_subprocess_boundary_uses_argument_list_and_only_locale_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        if args[-1] == "--is-inside-work-tree":
            return subprocess.CompletedProcess(args, 0, "true\n", "")
        return subprocess.CompletedProcess(args, 0, str(tmp_path.resolve()) + "\n", "")

    monkeypatch.setattr(git_module.subprocess, "run", run)
    result = inspect_git_relationship(tmp_path.resolve())

    assert result == GitInspectionResult(True, "root", tmp_path.resolve())
    assert len(calls) == 2
    assert calls[0][0] == [
        "git",
        "-C",
        str(tmp_path.resolve()),
        "rev-parse",
        "--is-inside-work-tree",
    ]
    assert all(call[1]["shell"] is False for call in calls)
    expected_environment = os.environ.copy()
    expected_environment["LC_ALL"] = "C"
    assert all(call[1]["env"] == expected_environment for call in calls)



def test_initial_process_start_failure_is_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr("dynosai.git._run_git", fail)
    assert inspect_git_relationship(tmp_path.resolve()) == GitInspectionResult(False, None, None)


def test_unexpected_completed_failure_preserves_subprocess_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    completed = subprocess.CompletedProcess(
        ["git", "-C", str(tmp_path), "rev-parse", "--is-inside-work-tree"],
        73,
        "partial",
        "synthetic failure\n",
    )
    monkeypatch.setattr("dynosai.git._run_git", lambda *args, **kwargs: completed)
    with pytest.raises(subprocess.CalledProcessError) as info:
        inspect_git_relationship(tmp_path.resolve())
    error = info.value
    assert error.returncode == 73
    assert error.cmd == completed.args
    assert error.stdout == completed.stdout
    assert error.stderr == completed.stderr


def test_later_process_start_failure_propagates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    calls = 0

    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return subprocess.CompletedProcess(args, 0, "true\n", "")
        raise FileNotFoundError("git")

    monkeypatch.setattr("dynosai.git._run_git", run)
    with pytest.raises(FileNotFoundError):
        inspect_git_relationship(tmp_path.resolve())


@pytest.mark.parametrize("stdout", ["TRUE\n", "true\nextra\n", "", "1\n"])
def test_malformed_probe_output_raises_valueerror(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, stdout: str
) -> None:
    completed = subprocess.CompletedProcess([], 0, stdout, "")
    monkeypatch.setattr("dynosai.git._run_git", lambda *args, **kwargs: completed)
    with pytest.raises(ValueError):
        inspect_git_relationship(tmp_path.resolve())


@pytest.mark.parametrize("stdout", ["", "one\ntwo\n", ".\n"])
def test_malformed_root_output_raises_valueerror(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path, stdout: str
) -> None:
    calls = 0

    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(args, 0, "true\n" if calls == 1 else stdout, "")

    monkeypatch.setattr("dynosai.git._run_git", run)
    with pytest.raises(ValueError):
        inspect_git_relationship(tmp_path.resolve())


def test_inconsistent_root_output_raises_valueerror(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    calls = 0

    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(
            args,
            0,
            "true\n" if calls == 1 else str(tmp_path.parent / "unrelated") + "\n",
            "",
        )

    monkeypatch.setattr("dynosai.git._run_git", run)
    with pytest.raises(ValueError):
        inspect_git_relationship(tmp_path.resolve())


def test_result_is_frozen_and_validates_invariants(tmp_path: pathlib.Path) -> None:
    result = GitInspectionResult(True, "none", None)
    with pytest.raises(AttributeError):
        result.relationship = "root"  # type: ignore[misc]

    with pytest.raises(ValueError):
        GitInspectionResult(False, "none", None)
    with pytest.raises(ValueError):
        GitInspectionResult(False, None, tmp_path)
    with pytest.raises(ValueError):
        GitInspectionResult(True, "none", tmp_path)
    with pytest.raises(ValueError):
        GitInspectionResult(True, "root", None)
    with pytest.raises(ValueError):
        GitInspectionResult(True, "root", pathlib.Path("relative"))
    with pytest.raises(ValueError):
        GitInspectionResult(True, "descendant", None)
    with pytest.raises(ValueError):
        GitInspectionResult(True, "descendant", pathlib.Path("relative"))
    with pytest.raises(ValueError):
        GitInspectionResult(True, "unsupported", None)  # type: ignore[arg-type]


def test_inspection_is_read_only(git_fixtures: dict[str, pathlib.Path]) -> None:
    repository = git_fixtures["root"].resolve()
    before = _tree_snapshot(repository.parent)
    first = inspect_git_relationship(repository)
    second = inspect_git_relationship(repository)
    after = _tree_snapshot(repository.parent)
    assert first == second
    assert before == after
    assert not (repository.parent / ".dynos").exists()
