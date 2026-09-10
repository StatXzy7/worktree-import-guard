"""Run a disposable installed-wheel wrong-worktree demonstration."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    expected: int = 0,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != expected:
        raise RuntimeError(
            f"expected exit {expected}, got {completed.returncode}: {' '.join(command)}\n"
            f"{completed.stdout}{completed.stderr}"
        )
    return completed


def console_script(venv: Path, name: str) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    path = venv / ("Scripts" if sys.platform == "win32" else "bin") / f"{name}{suffix}"
    if not path.is_file():
        raise RuntimeError(f"installed console script is missing: {path}")
    return path


def select_wheel(value: Path) -> Path:
    if value.is_file():
        return value.resolve()
    wheels = sorted(value.glob("worktree_import_guard-*.whl")) if value.is_dir() else []
    if len(wheels) != 1:
        message = f"expected one worktree-import-guard wheel at {value}, found {len(wheels)}"
        raise SystemExit(message)
    return wheels[0].resolve()


def git(cwd: Path, *args: str) -> None:
    run(["git", "-C", str(cwd), *args], cwd=cwd)


def write_fixture(main: Path) -> None:
    (main / "src/demo_pkg").mkdir(parents=True)
    (main / "src/demo_pkg/__init__.py").write_text(
        "from .core import checkout, stable_value\n", encoding="utf-8"
    )
    (main / "src/demo_pkg/core.py").write_text(
        'def checkout():\n    return "main"\n\ndef stable_value():\n    return 42\n',
        encoding="utf-8",
    )
    (main / "tests").mkdir()
    (main / "tests/test_value.py").write_text(
        "from demo_pkg import stable_value\n\ndef test_value():\n    assert stable_value() == 42\n",
        encoding="utf-8",
    )
    (main / "pyproject.toml").write_text(
        """\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-pkg"
version = "1.0.0"

[tool.setuptools.packages.find]
where = ["src"]
""",
        encoding="utf-8",
    )


def demo(wheel: Path) -> None:
    temporary = tempfile.TemporaryDirectory(prefix="wtig-demo-")
    temp = Path(temporary.name)
    print(f"Preparing a private demo repository and environment at {temp}", flush=True)
    print(
        "Setup may download pytest and setuptools. Your project environment is not used.",
        flush=True,
    )
    try:
        main = temp / "main repository"
        feature = temp / "feature worktree"
        main.mkdir()
        git(main, "init", "-b", "main")
        git(main, "config", "user.email", "demo@example.invalid")
        git(main, "config", "user.name", "Demo")
        write_fixture(main)
        git(main, "add", ".")
        git(main, "commit", "-m", "main fixture")
        git(main, "worktree", "add", "-b", "feature", str(feature), "main")
        (feature / "src/demo_pkg/core.py").write_text(
            'def checkout():\n    return "feature"\n\ndef stable_value():\n    return 42\n',
            encoding="utf-8",
        )
        git(feature, "add", "src/demo_pkg/core.py")
        git(feature, "commit", "-m", "feature fixture")

        venv = temp / "shared venv"
        run([sys.executable, "-m", "venv", str(venv)], cwd=temp)
        python = console_script(venv, "python")
        run(
            [str(python), "-m", "pip", "install", "setuptools>=68", str(wheel)],
            cwd=temp,
        )
        pytest_script = console_script(venv, "pytest")
        wt_import = console_script(venv, "wt-import")
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

        run(
            [str(python), "-m", "pip", "install", "--no-build-isolation", "-e", str(main)],
            cwd=temp,
        )
        ordinary = run([str(pytest_script), "-q"], cwd=feature, env=env)
        wrong = run(
            [
                str(wt_import),
                "--expect",
                "demo_pkg=src/demo_pkg",
                "--report-json",
                str(temp / "wrong.json"),
                "--",
                "-q",
            ],
            cwd=feature,
            env=env,
            expected=1,
        )
        wrong_report = json.loads((temp / "wrong.json").read_text(encoding="utf-8"))
        if wrong_report["pytest"]["exit_code"] != 0 or wrong_report["targets"][0]["reasons"] != [
            "CROSS_WORKTREE_IMPORT"
        ]:
            raise RuntimeError(
                f"Demo did not reproduce a passing test with wrong sources: {wrong.stdout}"
            )

        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-build-isolation",
                "--force-reinstall",
                "-e",
                str(feature),
            ],
            cwd=temp,
        )
        correct = run(
            [
                str(wt_import),
                "--expect",
                "demo_pkg=src/demo_pkg",
                "--report-json",
                str(temp / "correct.json"),
                "--",
                "-q",
            ],
            cwd=feature,
            env=env,
        )
        correct_report = json.loads((temp / "correct.json").read_text(encoding="utf-8"))
        if correct_report["guard"] != {
            "status": "pass",
            "complete": True,
            "observation_complete": True,
        }:
            raise RuntimeError(f"Demo correct-source control failed: {correct.stdout}")

        print("ORDINARY PYTEST (stale main editable, expected exit 0)")
        print(ordinary.stdout.rstrip())
        print("\nGUARD (stale main editable, expected exit 1)")
        print(wrong.stdout.rstrip())
        print("\nGUARD (feature editable, expected exit 0)")
        print(correct.stdout.rstrip())
        print("\nDemo passed: native pytest 0, wrong-source guard 1, correct-source guard 0.")
    finally:
        try:
            temporary.cleanup()
        except OSError as error:
            print(
                f"Cleanup could not finish; residual demo files: {temp} ({error})", file=sys.stderr
            )
        else:
            print(f"Removed demo files: {temp}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wheel",
        required=True,
        type=Path,
        help="built wheel file or directory containing exactly one built wheel",
    )
    options = parser.parse_args()
    demo(select_wheel(options.wheel))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
