"""Deterministic, disposable tests for Spec Kit inspection."""

from pathlib import Path
import os
import stat
import subprocess

import pytest

import dynosai.specify as specify_module
from dynosai.specify import SpecKitInspectionResult, inspect_spec_kit

SCRIPT_FILES = {
    "bash": (
        "check-prerequisites.sh", "common.sh", "create-new-feature.sh",
        "resolve-template.sh", "setup-plan.sh", "setup-tasks.sh",
    ),
    "powershell": (
        "check-prerequisites.ps1", "common.ps1", "create-new-feature.ps1",
        "resolve-template.ps1", "setup-plan.ps1", "setup-tasks.ps1",
    ),
    "python": (
        "check_prerequisites.py", "common.py", "create_new_feature.py",
        "resolve_template.py", "setup_plan.py", "setup_tasks.py",
    ),
}
TEMPLATES = (
    "checklist-template.md", "constitution-template.md", "plan-template.md",
    "spec-template.md", "tasks-template.md",
)


def make_fixture(operating: Path, variant: str = "python") -> Path:
    root = operating / ".specify"
    scripts = root / "scripts" / variant
    templates = root / "templates"
    scripts.mkdir(parents=True)
    templates.mkdir()
    (root / "init-options.json").write_text("{}", encoding="utf-8")
    for name in SCRIPT_FILES[variant]:
        (scripts / name).write_text("", encoding="utf-8")
    for name in TEMPLATES:
        (templates / name).write_text("", encoding="utf-8")
    return root


def test_complete_direct_child_is_usable_and_result_is_immutable(tmp_path: Path) -> None:
    operating = tmp_path / "project with spaces"
    operating.mkdir()
    root = make_fixture(operating)
    result = inspect_spec_kit(operating)
    assert result == SpecKitInspectionResult("usable", root.resolve())
    assert result.specify_root == root.resolve()
    with pytest.raises(AttributeError):
        result.state = "absent"  # type: ignore[misc]
    assert set(result.__dataclass_fields__) == {"state", "specify_root"}


def test_absent_and_parent_only_state_are_absent(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    operating = parent / "nested"
    operating.mkdir(parents=True)
    make_fixture(parent)
    result = inspect_spec_kit(operating)
    assert result.state == "absent"
    assert result.specify_root is None


def test_incomplete_and_wrong_types_are_unusable(tmp_path: Path) -> None:
    operating = tmp_path / "project"
    operating.mkdir()
    root = operating / ".specify"
    root.write_text("not a directory", encoding="utf-8")
    assert inspect_spec_kit(operating) == SpecKitInspectionResult("unusable", root.resolve())
    root.unlink()
    root.mkdir()
    assert inspect_spec_kit(operating) == SpecKitInspectionResult("unusable", root.resolve())

    (root / "init-options.json").mkdir()
    assert inspect_spec_kit(operating).state == "unusable"

    root = operating / "typed"
    root.mkdir()
    (root / "scripts").write_text("", encoding="utf-8")
    (operating / ".specify").rename(operating / ".specify-old")
    root.rename(operating / ".specify")
    assert inspect_spec_kit(operating).state == "unusable"


def test_each_supported_script_variant_is_accepted(tmp_path: Path) -> None:
    for variant in SCRIPT_FILES:
        operating = tmp_path / variant
        operating.mkdir()
        make_fixture(operating, variant)
        assert inspect_spec_kit(operating).state == "usable"


@pytest.mark.parametrize("variant", list(SCRIPT_FILES))
def test_incomplete_supported_script_variants_are_unusable(
    tmp_path: Path, variant: str
) -> None:
    operating = tmp_path / variant
    operating.mkdir()
    root = make_fixture(operating, variant)
    (root / "scripts" / variant / SCRIPT_FILES[variant][0]).unlink()
    assert inspect_spec_kit(operating).state == "unusable"


def test_scripts_root_wrong_type_is_unusable(tmp_path: Path) -> None:
    operating = tmp_path / "scripts-file"
    operating.mkdir()
    root = make_fixture(operating)
    scripts = root / "scripts"
    for child in scripts.iterdir():
        if child.is_dir():
            for file in child.iterdir():
                file.unlink()
            child.rmdir()
        else:
            child.unlink()
    scripts.rmdir()
    scripts.write_text("not a directory", encoding="utf-8")
    assert inspect_spec_kit(operating).state == "unusable"


def test_templates_root_wrong_type_is_unusable(tmp_path: Path) -> None:
    operating = tmp_path / "templates-file"
    operating.mkdir()
    root = make_fixture(operating)
    templates = root / "templates"
    for file in templates.iterdir():
        file.unlink()
    templates.rmdir()
    templates.write_text("not a directory", encoding="utf-8")
    assert inspect_spec_kit(operating).state == "unusable"


def test_extra_optional_content_is_ignored(tmp_path: Path) -> None:
    operating = tmp_path / "project"
    operating.mkdir()
    root = make_fixture(operating)
    (root / "workflows").mkdir()
    (root / "workflows" / "workflow.yml").write_text("", encoding="utf-8")
    (root / "unrelated.txt").write_text("", encoding="utf-8")
    assert inspect_spec_kit(operating).state == "usable"


@pytest.mark.parametrize("missing", ["init", "scripts", "templates", "script", "template"])
def test_each_required_category_can_make_state_unusable(tmp_path: Path, missing: str) -> None:
    operating = tmp_path / missing
    operating.mkdir()
    root = make_fixture(operating)
    if missing == "init":
        (root / "init-options.json").unlink()
    elif missing == "scripts":
        for child in (root / "scripts").iterdir():
            if child.is_dir():
                for file in child.iterdir():
                    file.unlink()
                child.rmdir()
        (root / "scripts").rmdir()
    elif missing == "templates":
        for file in (root / "templates").iterdir():
            file.unlink()
        (root / "templates").rmdir()
    elif missing == "script":
        (root / "scripts" / "python" / SCRIPT_FILES["python"][0]).unlink()
    else:
        (root / "templates" / TEMPLATES[0]).unlink()
    assert inspect_spec_kit(operating).state == "unusable"


@pytest.mark.parametrize("template", TEMPLATES)
def test_each_missing_template_is_unusable(tmp_path: Path, template: str) -> None:
    operating = tmp_path / "missing-template"
    operating.mkdir()
    root = make_fixture(operating)
    (root / "templates" / template).unlink()
    assert inspect_spec_kit(operating).state == "unusable"


@pytest.mark.parametrize("template", TEMPLATES)
def test_each_wrong_template_type_is_unusable(tmp_path: Path, template: str) -> None:
    operating = tmp_path / "wrong-template"
    operating.mkdir()
    root = make_fixture(operating)
    (root / "templates" / template).unlink()
    (root / "templates" / template).mkdir()
    assert inspect_spec_kit(operating).state == "unusable"


def test_valid_and_broken_links_have_expected_states(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    make_fixture(target)
    operating = tmp_path / "link project"
    operating.mkdir()
    link = operating / ".specify"
    try:
        link.symlink_to(target / ".specify", target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")
    result = inspect_spec_kit(operating)
    assert result.state == "usable"
    assert result.specify_root == (target / ".specify").resolve()

    broken_operating = tmp_path / "broken"
    broken_operating.mkdir()
    (broken_operating / ".specify").symlink_to(tmp_path / "missing", target_is_directory=True)
    assert inspect_spec_kit(broken_operating).state == "unusable"


def test_windows_junction_target_is_supported_when_available(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("junctions are Windows-specific")
    target = tmp_path / "junction-target"
    target.mkdir()
    make_fixture(target)
    operating = tmp_path / "junction-project"
    operating.mkdir()
    link = operating / ".specify"
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target / ".specify")],
        capture_output=True,
    )
    if completed.returncode != 0:
        pytest.skip("junction unavailable")
    result = inspect_spec_kit(operating)
    assert result.state == "usable"
    assert result.specify_root == (target / ".specify").resolve()


def test_required_asset_links_follow_targets_and_broken_links_fail(tmp_path: Path) -> None:
    operating = tmp_path / "project"
    operating.mkdir()
    root = make_fixture(operating)
    external = tmp_path / "external-init-options.json"
    external.write_text("{}", encoding="utf-8")
    init_options = root / "init-options.json"
    init_options.unlink()
    try:
        init_options.symlink_to(external)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"file symlink unavailable: {exc}")
    assert inspect_spec_kit(operating).state == "usable"

    script_target = tmp_path / "external-script.py"
    script_target.write_text("", encoding="utf-8")
    script_file = root / "scripts" / "python" / "common.py"
    script_file.unlink()
    script_file.symlink_to(script_target)
    template_target = tmp_path / "external-template.md"
    template_target.write_text("", encoding="utf-8")
    template_file = root / "templates" / "spec-template.md"
    template_file.unlink()
    template_file.symlink_to(template_target)
    assert inspect_spec_kit(operating).state == "usable"

    init_options.unlink()
    init_options.symlink_to(tmp_path / "missing-init-options.json")
    assert inspect_spec_kit(operating).state == "unusable"


@pytest.mark.parametrize(
    "relative",
    [
        Path("scripts") / "python" / "common.py",
        Path("templates") / "spec-template.md",
    ],
)
def test_broken_required_asset_links_are_unusable(
    tmp_path: Path, relative: Path
) -> None:
    operating = tmp_path / "project"
    operating.mkdir()
    root = make_fixture(operating)
    target = root / relative
    target.unlink()
    target.symlink_to(tmp_path / "missing-required-asset")
    assert inspect_spec_kit(operating).state == "unusable"


@pytest.mark.parametrize("variant", list(SCRIPT_FILES))
def test_required_script_file_wrong_type_is_unusable(
    tmp_path: Path, variant: str
) -> None:
    operating = tmp_path / variant
    operating.mkdir()
    root = make_fixture(operating, variant)
    target = root / "scripts" / variant / SCRIPT_FILES[variant][0]
    target.unlink()
    target.mkdir()
    assert inspect_spec_kit(operating).state == "unusable"


def test_wrong_target_and_broken_required_links_are_unusable(tmp_path: Path) -> None:
    operating = tmp_path / "project"
    operating.mkdir()
    root = make_fixture(operating)
    (root / "scripts" / "python").rename(root / "scripts" / "python-real")
    (root / "scripts" / "python").symlink_to(root / "init-options.json", target_is_directory=True)
    assert inspect_spec_kit(operating).state == "unusable"


def test_access_failures_propagate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    operating = tmp_path / "project"
    operating.mkdir()
    expected = PermissionError("inspection denied")

    def denied(path: object) -> os.stat_result:
        raise expected

    monkeypatch.setattr("dynosai.specify.os.lstat", denied)
    with pytest.raises(PermissionError) as raised:
        inspect_spec_kit(operating)
    assert raised.value is expected


@pytest.mark.parametrize(
    "relative",
    [
        Path("init-options.json"),
        Path("scripts"),
        Path("scripts") / "python",
        Path("scripts") / "python" / "common.py",
        Path("templates"),
        Path("templates") / "spec-template.md",
    ],
)
def test_required_asset_access_failures_propagate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, relative: Path
) -> None:
    operating = tmp_path / "project"
    operating.mkdir()
    root = make_fixture(operating)
    target = root / relative
    expected = PermissionError(f"inspection denied: {target}")
    original_stat = specify_module.os.stat

    def denied(path: object) -> os.stat_result:
        if Path(path) == target:
            raise expected
        return original_stat(path)

    monkeypatch.setattr(specify_module.os, "stat", denied)
    with pytest.raises(PermissionError) as raised:
        inspect_spec_kit(operating)
    assert raised.value is expected


def _snapshot(path: Path) -> tuple[tuple[str, str, int, int, int], ...]:
    entries = []
    for item in sorted(path.rglob("*")):
        relative = item.relative_to(path).as_posix()
        info = item.lstat()
        kind = "dir" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "other"
        entries.append((relative, kind, stat.S_IMODE(info.st_mode), info.st_size, info.st_mtime_ns))
    return tuple(entries)


def test_repeated_results_and_filesystem_snapshot_are_stable(tmp_path: Path) -> None:
    operating = tmp_path / "stable project"
    operating.mkdir()
    make_fixture(operating)
    before = _snapshot(operating)
    first = inspect_spec_kit(operating)
    second = inspect_spec_kit(operating)
    assert first == second
    assert _snapshot(operating) == before
    assert not (operating / ".dynos").exists()


def test_result_invariants_reject_invalid_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SpecKitInspectionResult("other", None)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        SpecKitInspectionResult("absent", tmp_path)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        SpecKitInspectionResult("unusable", None)
    with pytest.raises(ValueError):
        SpecKitInspectionResult("usable", Path("relative"))
    with pytest.raises(ValueError):
        SpecKitInspectionResult("unusable", Path("relative"))

    target = tmp_path / "resolved-target"
    target.mkdir()
    non_resolved = tmp_path / "alias" / ".." / "resolved-target"
    with pytest.raises(ValueError):
        SpecKitInspectionResult("usable", non_resolved)
    with pytest.raises(ValueError):
        SpecKitInspectionResult("unusable", non_resolved)

    alias = tmp_path / "alias-link"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        alias = None
    if alias is not None:
        with pytest.raises(ValueError):
            SpecKitInspectionResult("usable", alias)
        with pytest.raises(ValueError):
            SpecKitInspectionResult("unusable", alias)
