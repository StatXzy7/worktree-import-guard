from __future__ import annotations

import json
import subprocess
import sys
import sysconfig
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
    sibling = Path(sysconfig.get_path("scripts")) / (
        "wt-import.exe" if sys.platform == "win32" else "wt-import"
    )
    if sibling.is_file():
        return [str(sibling)]
    pytest.fail(f"the wt-import console script for {sys.executable} is required at {sibling}")


@pytest.fixture(scope="session")
def test_runner_command() -> list[str]:
    sibling = Path(sysconfig.get_path("scripts")) / (
        "pytest.exe" if sys.platform == "win32" else "pytest"
    )
    if sibling.is_file():
        return [str(sibling)]
    pytest.fail(f"the pytest console script for {sys.executable} is required at {sibling}")


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
