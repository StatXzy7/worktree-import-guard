"""Installed, offline demonstration using the same interpreter and guard runtime."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(args: list[str], directory: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def _fixture(root: Path) -> None:
    package = root / "src/demo_pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 42\n", encoding="utf-8")
    (root / "test_demo.py").write_text(
        "import demo_pkg\ndef test_value():\n    assert demo_pkg.VALUE == 42\n", encoding="utf-8"
    )


def run_demo() -> int:
    try:
        temporary = tempfile.TemporaryDirectory(prefix="wt-import-demo-")
    except OSError as error:
        print(f"Cannot create private demo directory: {error}", file=sys.stderr)
        return 1
    root = Path(temporary.name)
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(key, None)
    for key in list(env):
        if key.upper().startswith("GIT_"):
            del env[key]
    env.update(
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
    )
    print("Demo: tests pass even when Python loads another copy of the source.")
    print(f"Private example directory: {root}")
    print("This fixture deliberately selects an import path; no project environment is repaired.")
    exit_code = 1
    try:
        main, feature = root / "main", root / "feature"
        _fixture(main)
        git = shutil.which("git")
        if git:
            empty = root / "empty-git-template"
            empty.mkdir()
            for args in (
                ["init", "--template", str(empty), "-b", "main"],
                ["add", "."],
                [
                    "-c",
                    "user.name=Demo",
                    "-c",
                    "user.email=demo@example.invalid",
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "-m",
                    "Demo fixture",
                ],
                ["worktree", "add", "-b", "feature", str(feature)],
            ):
                completed = _run([git, "-c", f"core.hooksPath={empty}", *args], main, env)
                if completed.returncode:
                    raise RuntimeError(f"Git demo setup failed: {completed.stderr}")
            print(
                "Two real Git worktrees; simplified path-selection fixture, not a PEP 660 install."
            )
        else:
            _fixture(feature)
            print("Git unavailable: using two ordinary directories; no cross-worktree claim.")
        conftest = feature / "conftest.py"

        def select_source(source: Path) -> None:
            # Path injection belongs exclusively to this disposable demonstration fixture.
            conftest.write_text(
                f"import sys\nsys.path.insert(0, {str(source / 'src')!r})\n", encoding="utf-8"
            )
            # Avoid timestamp/size pyc reuse when the fixture is rewritten rapidly.
            cache = feature / "__pycache__"
            if cache.is_dir():
                for pyc in cache.glob("conftest.*.pyc"):
                    pyc.unlink()

        select_source(main)
        ordinary = _run([sys.executable, "-m", "pytest", "-q"], feature, env)
        print("1. Ordinary pytest:")
        print(ordinary.stdout, end="")
        if ordinary.returncode:
            raise RuntimeError(f"expected ordinary tests to pass: {ordinary.stderr}")
        for label, source, expected_exit, status in (
            ("2. Check wrong source", main, 1, "fail"),
            ("3. Select correct source inside this example", feature, 0, "pass"),
        ):
            select_source(source)
            report = root / f"{status}.json"
            completed = _run(
                [
                    sys.executable,
                    "-m",
                    "worktree_import_guard.cli",
                    "--expect",
                    "demo_pkg=src/demo_pkg",
                    "--report-json",
                    str(report),
                    "--",
                    "-q",
                ],
                feature,
                env,
            )
            print(label + ":")
            print(completed.stdout, end="")
            data = json.loads(report.read_text(encoding="utf-8"))
            if (
                completed.returncode != expected_exit
                or data["pytest"]["exit_code"] != 0
                or data["guard"]["status"] != status
                or not data["guard"]["complete"]
                or not data["guard"]["observation_complete"]
            ):
                raise RuntimeError(f"unexpected demo result: {completed.stderr}")
        print("Demo complete: passing tests, wrong-source FAIL, then correct-source PASS.")
        exit_code = 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Demo could not complete: {error}", file=sys.stderr)
    finally:
        try:
            temporary.cleanup()
        except OSError as error:
            print(f"Could not clean up demo directory {root}: {error}", file=sys.stderr)
            exit_code = 1
    return exit_code
