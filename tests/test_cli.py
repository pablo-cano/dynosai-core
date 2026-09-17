"""Tests for the `dynos --version` CLI contract (FR-003, FR-004, FR-005)."""

import shutil
import subprocess

EXPECTED_OUTPUT_LINE = b"dynos 0.0.2"
ACCEPTED_TERMINATIONS = tuple(
    EXPECTED_OUTPUT_LINE + terminator for terminator in (b"\n", b"\r\n")
)


def _run_version() -> subprocess.CompletedProcess[bytes]:
    executable = shutil.which("dynos")
    assert executable is not None, "dynos console script not found on PATH"
    return subprocess.run([executable, "--version"], capture_output=True)


def test_version_output_exit_status_and_streams() -> None:
    result = _run_version()
    assert result.returncode == 0
    assert result.stdout in ACCEPTED_TERMINATIONS
    assert result.stderr == b""


def test_version_output_is_deterministic_in_same_environment() -> None:
    first = _run_version()
    second = _run_version()
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == b""
