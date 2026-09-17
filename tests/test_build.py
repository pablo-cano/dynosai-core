"""Tests for offline distribution build verification (FR-008, FR-009, FR-010, FR-011)."""

import email.parser
import subprocess
import tarfile
import zipfile
from pathlib import Path

EXPECTED_NAME = "dynosai-core"
EXPECTED_VERSION = "0.0.3"
WHEEL_NAME = f"dynosai_core-{EXPECTED_VERSION}-py3-none-any.whl"
SDIST_NAME = f"dynosai_core-{EXPECTED_VERSION}.tar.gz"
WHEEL_DIST_INFO = f"dynosai_core-{EXPECTED_VERSION}.dist-info"
SDIST_ROOT = f"dynosai_core-{EXPECTED_VERSION}"
# The sdist may carry only packaged source; development harness state must never
# leak into a product artifact (FR-010, constitution IX). Hatchling always adds
# PKG-INFO and the versioned root .gitignore, which carries only public build
# hygiene patterns.
SDIST_TOP_LEVEL = {".gitignore", "PKG-INFO", "pyproject.toml", "src", "tests"}


def _build_offline(out_dir: Path) -> None:
    completed = subprocess.run(
        ["uv", "build", "--offline", "--out-dir", str(out_dir)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_offline_build_produces_validated_artifacts(tmp_path: Path) -> None:
    _build_offline(tmp_path)

    wheel_path = tmp_path / WHEEL_NAME
    sdist_path = tmp_path / SDIST_NAME
    assert wheel_path.is_file(), f"missing wheel: {WHEEL_NAME}"
    assert sdist_path.is_file(), f"missing sdist: {SDIST_NAME}"

    with zipfile.ZipFile(wheel_path) as wheel:
        names = wheel.namelist()
        wheel_allowed = ("dynosai/", f"{WHEEL_DIST_INFO}/")
        assert all(name.startswith(wheel_allowed) for name in names), sorted(names)
        assert not [
            name for name in names if "__pycache__" in name or name.endswith(".pyc")
        ], sorted(names)
        assert "dynosai/__init__.py" in names
        assert "dynosai/cli.py" in names
        assert "dynosai/directory.py" in names
        assert "dynosai/git.py" in names

        metadata = email.parser.Parser().parsestr(
            wheel.read(f"{WHEEL_DIST_INFO}/METADATA").decode("utf-8")
        )
        entry_points = wheel.read(f"{WHEEL_DIST_INFO}/entry_points.txt").decode("utf-8")

    assert metadata["Name"] == EXPECTED_NAME
    assert metadata["Version"] == EXPECTED_VERSION
    assert metadata["Requires-Python"] == ">=3.11"
    assert not metadata.get_all("Requires-Dist")
    assert [
        line for line in entry_points.splitlines()
        if line and not line.startswith("[")
    ] == ["dynos = dynosai.cli:main"]

    with tarfile.open(sdist_path) as sdist:
        members = sdist.getnames()
        root_prefix = f"{SDIST_ROOT}/"
        assert all(name.startswith(root_prefix) for name in members), sorted(members)
        assert not [
            name for name in members if "__pycache__" in name or name.endswith(".pyc")
        ], sorted(members)
        assert f"{root_prefix}pyproject.toml" in members
        assert f"{root_prefix}src/dynosai/__init__.py" in members
        assert f"{root_prefix}src/dynosai/cli.py" in members
        assert f"{root_prefix}src/dynosai/directory.py" in members
        assert f"{root_prefix}src/dynosai/git.py" in members
        top_level = {
            name[len(root_prefix) :].split("/", 1)[0] for name in members
        }
        assert top_level == SDIST_TOP_LEVEL, sorted(top_level)

        pkg_info = sdist.extractfile(f"{root_prefix}PKG-INFO")
        assert pkg_info is not None
        sdist_metadata = email.parser.Parser().parsestr(
            pkg_info.read().decode("utf-8")
        )

    assert sdist_metadata["Name"] == EXPECTED_NAME
    assert sdist_metadata["Version"] == EXPECTED_VERSION
    assert sdist_metadata["Requires-Python"] == ">=3.11"
    assert not sdist_metadata.get_all("Requires-Dist")
