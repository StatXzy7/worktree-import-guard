from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.conftest import write_package, write_test

pytestmark = pytest.mark.compat

SAMPLE_TEST = "from compat_pkg import VALUE\n\ndef test_value():\n    assert VALUE == 42\n"


def test_pytest_cov_native_and_guarded_runs(
    tmp_path: Path, guard_command: list[str], test_runner_command: list[str]
) -> None:
    write_package(tmp_path, "compat_pkg")
    write_test(tmp_path, SAMPLE_TEST)
    native = subprocess.run(
        [*test_runner_command, "--cov=compat_pkg", "-q"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert native.returncode == 0, native.stdout + native.stderr
    assert "TOTAL" in native.stdout

    report = tmp_path / "guard-cov.json"
    guarded = subprocess.run(
        [
            *guard_command,
            "--report-json",
            str(report),
            "--expect",
            "compat_pkg=compat_pkg",
            "--",
            "--cov=compat_pkg",
            "-q",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert guarded.returncode == 0, guarded.stdout + guarded.stderr
    assert "TOTAL" in guarded.stdout
    assert json.loads(report.read_text(encoding="utf-8"))["guard"]["status"] == "pass"


def test_pytest_asyncio_guarded_run(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "compat_pkg")
    write_test(
        tmp_path,
        """\
import pytest
from compat_pkg import VALUE

@pytest.mark.asyncio
async def test_value():
    assert VALUE == 42
""",
    )
    result = run_guard(tmp_path, "--expect", "compat_pkg=compat_pkg", "--", "-q")
    assert result.completed.returncode == 0, result.completed.stdout + result.completed.stderr
    assert result.report["guard"]["status"] == "pass"


def test_importlib_mode_correct_and_wrong_origins(tmp_path: Path, run_guard) -> None:
    correct = tmp_path / "correct"
    correct.mkdir()
    write_package(correct, "compat_pkg")
    write_test(correct, SAMPLE_TEST)
    (correct / "conftest.py").write_text(
        f"import sys\nsys.path.insert(0, {str(correct)!r})\n", encoding="utf-8"
    )
    passed = run_guard(
        correct,
        "--expect",
        "compat_pkg=compat_pkg",
        "--",
        "--import-mode=importlib",
        "-q",
    )
    assert passed.completed.returncode == 0, passed.completed.stdout + passed.completed.stderr
    assert passed.report["guard"]["status"] == "pass"

    wrong = tmp_path / "wrong"
    external = tmp_path / "external"
    wrong.mkdir()
    write_package(external, "compat_pkg")
    write_test(wrong, SAMPLE_TEST)
    (wrong / "conftest.py").write_text(
        f"import sys\nsys.path.insert(0, {str(external)!r})\n", encoding="utf-8"
    )
    failed = run_guard(
        wrong,
        "--expect",
        "compat_pkg=compat_pkg",
        "--",
        "--import-mode=importlib",
        "-q",
    )
    assert failed.completed.returncode == 1, failed.completed.stdout + failed.completed.stderr
    assert failed.report["targets"][0]["reasons"] == ["OUTSIDE_EXPECTED_ROOT"]


def test_xdist_installed_inactive_n0_and_active_rejection(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "compat_pkg")
    write_test(tmp_path, SAMPLE_TEST)
    inactive = run_guard(tmp_path, "--expect", "compat_pkg=compat_pkg", "--", "-q")
    assert inactive.completed.returncode == 0, inactive.completed.stdout + inactive.completed.stderr
    n0 = run_guard(tmp_path, "--expect", "compat_pkg=compat_pkg", "--", "-n", "0", "-q")
    assert n0.completed.returncode == 0, n0.completed.stdout + n0.completed.stderr

    active = run_guard(tmp_path, "--expect", "compat_pkg=compat_pkg", "--", "-n", "2", "-q")
    assert active.completed.returncode == 4
    assert active.report["pytest"]["exit_code"] == 4
    assert active.report["guard"]["observation_complete"] is False
    assert active.report["scope"]["xdist"] is True
