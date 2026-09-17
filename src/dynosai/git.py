"""Read-only Git working-tree relationship inspection."""

from __future__ import annotations

import os
import pathlib
import subprocess
from dataclasses import dataclass
from typing import Literal


_Relationship = Literal["none", "root", "descendant"]
_OUTSIDE_REPOSITORY_ERROR = (
    "fatal: not a git repository (or any of the parent directories): .git\n"
)


@dataclass(frozen=True, slots=True)
class GitInspectionResult:
    """Immutable result for one already-resolved operating directory."""

    git_available: bool
    relationship: _Relationship | None
    repository_root: pathlib.Path | None

    def __post_init__(self) -> None:
        if not self.git_available:
            if self.relationship is not None or self.repository_root is not None:
                raise ValueError("unavailable Git results cannot contain relationship data")
            return
        if self.relationship not in {"none", "root", "descendant"}:
            raise ValueError("available Git results require a valid relationship")
        if self.relationship == "none" and self.repository_root is not None:
            raise ValueError("a no-relationship result cannot contain a repository root")
        if self.relationship in {"root", "descendant"}:
            if self.repository_root is None or not self.repository_root.is_absolute():
                raise ValueError("working-tree relationships require an absolute repository root")


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    return environment


def _run_git(operating_directory: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(operating_directory), *arguments],
        capture_output=True,
        text=True,
        env=_environment(),
        check=False,
        shell=False,
    )


def _raise_completed_failure(result: subprocess.CompletedProcess[str]) -> None:
    raise subprocess.CalledProcessError(
        result.returncode,
        result.args,
        output=result.stdout,
        stderr=result.stderr,
    )


def _without_one_terminator(output: str) -> str | None:
    if not output.endswith("\n"):
        return None
    return output[:-1]


def inspect_git_relationship(operating_directory: pathlib.Path) -> GitInspectionResult:
    """Inspect the Git working-tree relationship of a resolved directory.

    The caller supplies the resolved SPEC-002 operating directory. Git itself
    performs repository discovery; this function neither walks parents nor
    interprets Git's administrative files, and it persists no inspection state.
    """
    try:
        probe = _run_git(operating_directory, "rev-parse", "--is-inside-work-tree")
    except OSError:
        return GitInspectionResult(False, None, None)

    if probe.returncode == 0:
        token = _without_one_terminator(probe.stdout)
        if token == "false":
            return GitInspectionResult(True, "none", None)
        if token != "true":
            raise ValueError("malformed Git working-tree probe output")
    elif (
        probe.returncode == 128
        and probe.stdout == ""
        and probe.stderr == _OUTSIDE_REPOSITORY_ERROR
    ):
        return GitInspectionResult(True, "none", None)
    else:
        _raise_completed_failure(probe)

    root_result = _run_git(operating_directory, "rev-parse", "--show-toplevel")
    if root_result.returncode != 0:
        _raise_completed_failure(root_result)
    root_text = _without_one_terminator(root_result.stdout)
    if not root_text or "\n" in root_text or "\r" in root_text:
        raise ValueError("malformed Git working-tree root output")
    reported_root = pathlib.Path(root_text)
    if not reported_root.is_absolute():
        raise ValueError("Git reported a non-absolute working-tree root")
    repository_root = reported_root.resolve()
    if repository_root == operating_directory:
        relationship: _Relationship = "root"
    else:
        try:
            operating_directory.relative_to(repository_root)
        except ValueError as error:
            raise ValueError("Git reported a root that does not contain the operating directory") from error
        relationship = "descendant"
    return GitInspectionResult(True, relationship, repository_root)
