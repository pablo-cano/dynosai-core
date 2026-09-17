"""Tests for dynosai.directory operating-directory resolution (SPEC-002 US1)."""

import errno
import os
import pathlib
import subprocess
import sys

import pytest

from dynosai.directory import resolve_operating_directory


class _StringPathLike:
    """Minimal ``os.PathLike[str]`` whose fspath form is a fixed string (test-only)."""

    def __init__(self, value: str) -> None:
        self._value = value

    def __fspath__(self) -> str:
        return self._value


def test_explicit_absolute_directory_returns_resolved_path(
    tmp_path: pathlib.Path,
) -> None:
    target = tmp_path / "sub"
    target.mkdir()
    result = resolve_operating_directory(str(target))
    assert isinstance(result, pathlib.Path)
    assert result == target.resolve()
    assert result.is_absolute()


def test_relative_path_resolves_against_call_working_directory(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "sub"
    target.mkdir()
    monkeypatch.chdir(tmp_path)
    assert resolve_operating_directory("sub") == target.resolve()


def test_path_with_spaces_resolves_and_preserves_spaces(
    tmp_path: pathlib.Path,
) -> None:
    target = tmp_path / "sub dir"
    target.mkdir()
    result = resolve_operating_directory(str(target))
    assert result == target.resolve()
    assert " " in str(result)


def test_dot_dotdot_and_redundant_separators_normalize(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "sub dir"
    target.mkdir()
    monkeypatch.chdir(tmp_path)
    sep = os.sep
    spellings = [
        "sub dir",
        f".{sep}sub dir",
        f"sub dir{sep}..{sep}sub dir",
        f"sub dir{sep}",
        f"sub dir{sep}{sep}",
    ]
    expected = target.resolve()
    for spelling in spellings:
        assert resolve_operating_directory(spelling) == expected


def test_str_and_pathlike_inputs_accepted(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "sub"
    target.mkdir()
    expected = target.resolve()
    assert resolve_operating_directory(str(target)) == expected
    assert resolve_operating_directory(target) == expected


def test_repeated_resolution_returns_identical_value(
    tmp_path: pathlib.Path,
) -> None:
    target = tmp_path / "sub dir"
    target.mkdir()
    first = resolve_operating_directory(str(target))
    assert resolve_operating_directory(str(target)) == first
    assert resolve_operating_directory(str(target)) == first


@pytest.mark.parametrize("invalid", ["", " ", "   ", "\t", " \t \n "])
def test_empty_or_whitespace_string_raises_valueerror(invalid: str) -> None:
    with pytest.raises(ValueError, match="empty or whitespace"):
        resolve_operating_directory(invalid)


@pytest.mark.parametrize("invalid", ["", "   "])
def test_pathlike_with_empty_or_whitespace_fspath_raises_valueerror(
    invalid: str,
) -> None:
    stub = _StringPathLike(invalid)
    assert isinstance(stub, os.PathLike)
    with pytest.raises(ValueError, match="empty or whitespace"):
        resolve_operating_directory(stub)


# US2: omission resolves the current working directory of the call.


def test_omitted_and_none_use_call_working_directory(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_operating_directory() == tmp_path.resolve()
    assert resolve_operating_directory(None) == tmp_path.resolve()


def test_omission_answers_for_each_call_working_directory(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_cwd = tmp_path / "alpha"
    second_cwd = tmp_path / "beta"
    first_cwd.mkdir()
    second_cwd.mkdir()
    monkeypatch.chdir(first_cwd)
    first = resolve_operating_directory()
    monkeypatch.chdir(second_cwd)
    second = resolve_operating_directory()
    assert first == first_cwd.resolve()
    assert second == second_cwd.resolve()
    assert first != second


def test_nonexistent_directory_raises_file_not_found(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing dir"
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError) as first_info:
        resolve_operating_directory("missing dir")
    with pytest.raises(FileNotFoundError) as second_info:
        resolve_operating_directory(missing)
    assert first_info.value.errno == second_info.value.errno == errno.ENOENT
    assert first_info.value.filename == second_info.value.filename == str(missing.resolve())
    assert not missing.exists()


def test_existing_file_raises_not_a_directory(tmp_path: pathlib.Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")
    with pytest.raises(NotADirectoryError) as first_info:
        resolve_operating_directory(file_path)
    with pytest.raises(NotADirectoryError) as second_info:
        resolve_operating_directory(file_path)
    assert first_info.value.errno == second_info.value.errno == errno.ENOTDIR
    assert first_info.value.filename == second_info.value.filename == str(file_path.resolve())
    assert not isinstance(first_info.value, FileNotFoundError)


def test_windows_junction_resolves_to_target(tmp_path: pathlib.Path) -> None:
    if sys.platform != "win32":
        pytest.skip("Windows junctions are platform-specific")
    target = tmp_path / "target"
    junction = tmp_path / "junction"
    target.mkdir()
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
    )
    if completed.returncode != 0:
        pytest.skip("junction creation is unavailable")
    assert resolve_operating_directory(junction) == target.resolve()


def test_symlink_directory_and_file_behavior(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    directory_link = tmp_path / "directory-link"
    try:
        directory_link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    assert resolve_operating_directory(directory_link) == target.resolve()

    file_path = tmp_path / "file.txt"
    file_path.write_text("content")
    file_link = tmp_path / "file-link"
    try:
        file_link.symlink_to(file_path)
    except (OSError, NotImplementedError):
        pytest.skip("file symlink creation is unavailable")
    with pytest.raises(NotADirectoryError):
        resolve_operating_directory(file_link)


def _tree_snapshot(root: pathlib.Path) -> dict[str, tuple[int, int, int]]:
    snapshot: dict[str, tuple[int, int, int]] = {}
    for directory, names, files in os.walk(root):
        for name in [*names, *files]:
            path = pathlib.Path(directory) / name
            stat = path.stat()
            snapshot[str(path.relative_to(root))] = (
                stat.st_mode,
                stat.st_size,
                stat.st_mtime_ns,
            )
    return snapshot


def test_resolution_is_read_only_and_creates_no_dynos_state(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.chdir(tmp_path)
    before = _tree_snapshot(tmp_path)
    before_cwd = sorted(path.name for path in pathlib.Path.cwd().iterdir())
    assert resolve_operating_directory(target) == target.resolve()
    with pytest.raises(FileNotFoundError):
        resolve_operating_directory(tmp_path / "missing")
    after = _tree_snapshot(tmp_path)
    after_cwd = sorted(path.name for path in pathlib.Path.cwd().iterdir())
    assert before == after
    assert before_cwd == after_cwd
    assert ".dynos" not in after


def test_marker_directories_do_not_change_resolution(
    tmp_path: pathlib.Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    before = resolve_operating_directory(target)
    markers = [
        target / ".git",
        target / ".specify",
        target / ".grok",
        tmp_path / ".git",
        tmp_path / ".specify",
        tmp_path / ".grok",
    ]
    for marker in markers:
        marker.mkdir()
    try:
        with_markers = resolve_operating_directory(target)
    finally:
        for marker in reversed(markers):
            marker.rmdir()
    after = resolve_operating_directory(target)
    assert before == with_markers == after
