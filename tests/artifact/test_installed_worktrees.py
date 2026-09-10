from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.artifact,
    pytest.mark.skipif(
        os.environ.get("WTIG_RUN_ARTIFACT_TESTS") != "1",
        reason="set WTIG_RUN_ARTIFACT_TESTS=1 to run installation smoke tests",
    ),
]


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
    )
    assert completed.returncode == expected, completed.stdout + completed.stderr
    return completed


def clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def script(venv: Path, name: str) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    path = venv / ("Scripts" if sys.platform == "win32" else "bin") / f"{name}{suffix}"
    assert path.is_file(), f"required console script was not installed: {path}"
    return path


def git(cwd: Path, *args: str) -> None:
    run(["git", "-C", str(cwd), *args], cwd=cwd)


def write_project(main: Path) -> None:
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


def guard_run(
    wt_import: Path,
    cwd: Path,
    report_name: str,
    *,
    expected: int,
    env: dict[str, str],
) -> dict[str, object]:
    report = cwd / report_name
    run(
        [
            str(wt_import),
            "--report-json",
            str(report),
            "--expect",
            "demo_pkg=src/demo_pkg",
            "--",
            "-q",
        ],
        cwd=cwd,
        env=env,
        expected=expected,
    )
    return json.loads(report.read_text(encoding="utf-8"))


def test_wheel_console_scripts_pth_and_pep660_across_worktrees(
    tmp_path: Path, project_root: Path
) -> None:
    supplied_wheel = os.environ.get("WTIG_ARTIFACT_WHEEL")
    if supplied_wheel is not None:
        wheel = Path(supplied_wheel).resolve()
        assert wheel.is_file(), f"WTIG_ARTIFACT_WHEEL does not exist: {wheel}"
    else:
        artifacts = tmp_path / "artifacts"
        run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(artifacts)],
            cwd=project_root,
        )
        wheel = next(artifacts.glob("worktree_import_guard-*.whl"))

    main = tmp_path / "main repository"
    feature = tmp_path / "feature worktree"
    main.mkdir()
    git(main, "init", "-b", "main")
    git(main, "config", "user.email", "tests@example.invalid")
    git(main, "config", "user.name", "Artifact Test")
    write_project(main)
    git(main, "add", ".")
    git(main, "commit", "-m", "main fixture")
    git(main, "worktree", "add", "-b", "feature", str(feature), "main")
    (feature / "src/demo_pkg/core.py").write_text(
        'def checkout():\n    return "feature"\n\ndef stable_value():\n    return 42\n',
        encoding="utf-8",
    )
    git(feature, "add", "src/demo_pkg/core.py")
    git(feature, "commit", "-m", "feature fixture")

    venv = tmp_path / "shared venv"
    run([sys.executable, "-m", "venv", str(venv)], cwd=tmp_path)
    python = script(venv, "python")
    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "setuptools>=68",
            str(wheel),
        ],
        cwd=tmp_path,
    )
    pytest_script = script(venv, "pytest")
    wt_import = script(venv, "wt-import")
    env = clean_env()

    # Execute audit regressions with the installed runtime, outside the checkout.
    import shutil

    regression_root = tmp_path / "wheel regressions"
    shutil.copytree(project_root / "tests", regression_root / "tests")
    regression = run(
        [str(python), "-m", "pytest", "tests/integration/test_audit_regressions.py", "-q"],
        cwd=regression_root, env=env,
    )
    assert "20 passed" in regression.stdout, regression.stdout
    first_use = run(
        [str(python), "-m", "pytest", "tests/integration/test_first_use.py", "-q"],
        cwd=regression_root, env=env,
    )
    assert "12 passed" in first_use.stdout, first_use.stdout

    site_packages_text = run(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        cwd=tmp_path,
        env=env,
    ).stdout.strip()
    site_packages = Path(site_packages_text)
    stale_pth = site_packages / "stale-main-worktree.pth"
    stale_pth.write_text(str(main / "src") + "\n", encoding="utf-8")
    run([str(pytest_script), "-q"], cwd=feature, env=env)
    pth_report = guard_run(wt_import, feature, "pth-report.json", expected=1, env=env)
    assert pth_report["targets"][0]["reasons"] == ["CROSS_WORKTREE_IMPORT"]  # type: ignore[index]
    stale_pth.unlink()

    run(
        [str(python), "-m", "pip", "install", "--no-build-isolation", "-e", str(main)],
        cwd=tmp_path,
    )
    direct_url = next(site_packages.glob("demo_pkg-*.dist-info")) / "direct_url.json"
    editable_metadata = json.loads(direct_url.read_text(encoding="utf-8"))
    assert editable_metadata["dir_info"]["editable"] is True
    run([str(pytest_script), "-q"], cwd=feature, env=env)
    stale_report = guard_run(wt_import, feature, "editable-main.json", expected=1, env=env)
    assert stale_report["targets"][0]["reasons"] == ["CROSS_WORKTREE_IMPORT"]  # type: ignore[index]

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
        cwd=tmp_path,
    )
    correct_report = guard_run(wt_import, feature, "editable-feature.json", expected=0, env=env)
    assert correct_report["guard"] == {  # type: ignore[index]
        "complete": True,
        "observation_complete": True,
        "status": "pass",
    }
