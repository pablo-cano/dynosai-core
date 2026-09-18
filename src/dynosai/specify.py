"""Read-only inspection of a direct-child Spec Kit workspace."""

from dataclasses import dataclass
import os
from pathlib import Path
import stat
from typing import Literal


_SpecKitState = Literal["absent", "usable", "unusable"]


@dataclass(frozen=True, slots=True)
class SpecKitInspectionResult:
    """The observable state of an operating directory's direct ``.specify``."""

    state: _SpecKitState
    specify_root: Path | None

    def __post_init__(self) -> None:
        if self.state not in {"absent", "usable", "unusable"}:
            raise ValueError(f"invalid Spec Kit state: {self.state!r}")
        if self.state == "absent":
            if self.specify_root is not None:
                raise ValueError("absent Spec Kit state cannot have a location")
        elif (
            self.specify_root is None
            or not self.specify_root.is_absolute()
            or self.specify_root != self.specify_root.resolve()
        ):
            raise ValueError(
                "present Spec Kit state requires an absolute resolved location"
            )


_SCRIPT_FILES = {
    "bash": (
        "check-prerequisites.sh",
        "common.sh",
        "create-new-feature.sh",
        "resolve-template.sh",
        "setup-plan.sh",
        "setup-tasks.sh",
    ),
    "powershell": (
        "check-prerequisites.ps1",
        "common.ps1",
        "create-new-feature.ps1",
        "resolve-template.ps1",
        "setup-plan.ps1",
        "setup-tasks.ps1",
    ),
    "python": (
        "check_prerequisites.py",
        "common.py",
        "create_new_feature.py",
        "resolve_template.py",
        "setup_plan.py",
        "setup_tasks.py",
    ),
}
_TEMPLATE_FILES = (
    "checklist-template.md",
    "constitution-template.md",
    "plan-template.md",
    "spec-template.md",
    "tasks-template.md",
)


def _is_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(os.stat(path).st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False


def _is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(os.stat(path).st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False


def _has_variant(scripts_root: Path) -> bool:
    for variant, filenames in _SCRIPT_FILES.items():
        variant_root = scripts_root / variant
        if _is_directory(variant_root) and all(
            _is_regular_file(variant_root / filename) for filename in filenames
        ):
            return True
    return False


def inspect_spec_kit(operating_directory: Path) -> SpecKitInspectionResult:
    """Inspect only ``operating_directory/.specify`` without side effects."""
    candidate = operating_directory / ".specify"
    try:
        os.lstat(candidate)
    except (FileNotFoundError, NotADirectoryError):
        return SpecKitInspectionResult("absent", None)

    specify_root = candidate.resolve()
    usable = _is_directory(specify_root)
    if usable:
        usable = _is_regular_file(specify_root / "init-options.json")
    scripts_root = specify_root / "scripts"
    if usable:
        usable = _is_directory(scripts_root) and _has_variant(scripts_root)
    templates_root = specify_root / "templates"
    if usable:
        usable = _is_directory(templates_root) and all(
            _is_regular_file(templates_root / filename)
            for filename in _TEMPLATE_FILES
        )
    return SpecKitInspectionResult(
        "usable" if usable else "unusable",
        specify_root,
    )
