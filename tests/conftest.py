from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


@dataclass(frozen=True)
class CommandResult:
    completed: subprocess.CompletedProcess[str]
    report: dict[str, Any] | None


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def guard_command() -> list[str]:
    sibling = Path(sys.executable).with_name(
        "wt-import.exe" if sys.platform == "win32" else "wt-import"
    )
    if sibling.is_file():
        return [str(sibling)]
    executable = shutil.which("wt-import")
    if executable is not None:
        return [executable]
    launcher = "from worktree_import_guard.cli import main; raise SystemExit(main())"
    return [sys.executable, "-c", launcher]


@pytest.fixture(scope="session")
def test_runner_command() -> list[str]:
    sibling = Path(sys.executable).with_name("pytest.exe" if sys.platform == "win32" else "pytest")
    if sibling.is_file():
        return [str(sibling)]
    executable = shutil.which("pytest")
    if executable is None:
        pytest.fail("the pytest console script is required for integration tests")
    return [executable]


@pytest.fixture
def run_guard(guard_command: list[str]):
    def run(cwd: Path, *arguments: str, report: bool = True) -> CommandResult:
        report_path = cwd / "guard-report.json"
        command = [*guard_command, *arguments]
        if report:
            command[len(guard_command) : len(guard_command)] = ["--report-json", str(report_path)]
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        data = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        return CommandResult(completed=completed, report=data)

    return run


def write_package(root: Path, package: str, body: str = "VALUE = 42\n") -> Path:
    package_path = root.joinpath(*package.split("."))
    package_path.mkdir(parents=True)
    (package_path / "__init__.py").write_text(body, encoding="utf-8")
    return package_path


def write_test(root: Path, body: str, name: str = "test_sample.py") -> Path:
    path = root / name
    path.write_text(body, encoding="utf-8")
    return path
