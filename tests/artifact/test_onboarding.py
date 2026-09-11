from __future__ import annotations

import json
import os
import runpy
import shlex
import shutil
import sys
from pathlib import Path

import pytest
from test_installed_worktrees import clean_env, run, script

pytestmark = [
    pytest.mark.artifact,
    pytest.mark.skipif(
        os.environ.get("WTIG_RUN_ARTIFACT_TESTS") != "1",
        reason="set WTIG_RUN_ARTIFACT_TESTS=1 to run installation smoke tests",
    ),
]


def shell_run(command: list[str], cwd: Path, expected: int = 0):
    """Execute the README quoting syntax in the platform's real shell."""
    if sys.platform == "win32":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        assert shell, "PowerShell is required for Windows README smoke"
        line = "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in command)
        invocation = [shell, "-NoProfile", "-Command", line + "; exit $LASTEXITCODE"]
    else:
        invocation = ["sh", "-c", shlex.join(command)]
    return run(invocation, cwd=cwd, env=clean_env(), expected=expected)


@pytest.mark.parametrize("layout", ["src", "flat"])
def test_readme_in_existing_environment(tmp_path: Path, project_root: Path, layout: str) -> None:
    wheel_value = os.environ.get("WTIG_ARTIFACT_WHEEL")
    if wheel_value:
        wheel = Path(wheel_value).resolve()
    else:
        run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path / "dist")],
            cwd=project_root,
        )
        wheel = next((tmp_path / "dist").glob("*.whl"))
    project = tmp_path / "project with spaces"
    project.mkdir()
    # Use the Hero Demo's package/test fixture; only its directory layout changes here.
    demo = runpy.run_path(str(project_root / "examples/cross-worktree-demo/run.py"))
    demo["write_fixture"](project)
    if layout == "flat":
        (project / "src/demo_pkg").rename(project / "demo_pkg")
        path = project / "pyproject.toml"
        path.write_text(
            path.read_text(encoding="utf-8").replace('where = ["src"]', 'where = ["."]'),
            encoding="utf-8",
        )
    venv = project / ".venv"
    run([sys.executable, "-m", "venv", str(venv)], cwd=tmp_path)
    python = script(venv, "python")
    # Fixture preparation represents the user's already working project, before tool installation.
    run([str(python), "-m", "pip", "install", "pytest>=8.2,<10", "-e", str(project)], cwd=project)
    shell_run([str(script(venv, "pytest")), "-q"], project)
    missing = venv / ("Scripts/wt-import.exe" if sys.platform == "win32" else "bin/wt-import")
    assert not missing.exists(), "fixture unexpectedly contains the guard already"
    shell_run([str(python), "-m", "pip", "show", "worktree-import-guard"], project, expected=1)
    shell_run([str(python), "-m", "pip", "install", str(wheel)], project)
    guard = script(venv, "wt-import")
    expected_path = "src/demo_pkg" if layout == "src" else "demo_pkg"
    base = [str(guard), "--expect", f"demo_pkg={expected_path}"]
    passed = shell_run([*base, "--", "-q"], project)
    assert "WORKTREE IMPORT GUARD: PASS" in passed.stdout
    assert "demo_pkg: PASS" in passed.stdout
    assert "Tests passed." in passed.stdout
    details = shell_run([*base, "--show-all", "--report-json", "report.json", "--", "-q"], project)
    data = json.loads((project / "report.json").read_text(encoding="utf-8"))
    assert Path(data["run"]["sys_prefix"]) == venv
    assert Path(data["run"]["python"]) == python
    assert str(project / expected_path) in details.stdout
    # --cwd changes expected-path base, not report-path base.
    shell_run(
        [
            str(guard),
            "--cwd",
            str(project),
            "--expect",
            f"demo_pkg={expected_path}",
            "--report-json",
            "parent.json",
            "--",
            "-q",
        ],
        tmp_path,
    )
    assert (tmp_path / "parent.json").is_file()
    unknown = shell_run(
        [str(guard), "--expect", "unused_pkg=unused_pkg", "--", "-q"], project, expected=2
    )
    assert "No target import was observed" in unknown.stdout
    assert "UNKNOWN is not a pass" in unknown.stdout
    test = project / "tests/test_value.py"
    test.write_text(test.read_text(encoding="utf-8").replace("== 42", "== 0"), encoding="utf-8")
    failed = shell_run([*base, "--", "-q"], project, expected=1)
    assert "Tests failed.\nWORKTREE IMPORT GUARD: PASS" in failed.stdout
    test.write_text(test.read_text(encoding="utf-8").replace("== 0", "== 42"), encoding="utf-8")
    unwritable = shell_run([*base, "--report-json", str(project), "--", "-q"], project, expected=2)
    assert "Choose a writable file path" in unwritable.stderr
    assert "Traceback" not in unwritable.stderr
    versions = shell_run([str(guard), "--version"], project)
    assert versions.stdout.strip() == "wt-import 0.1.2"
    packages = run([str(python), "-m", "pip", "list", "--format=json"], cwd=project)
    names = {p["name"].lower() for p in json.loads(packages.stdout)}
    assert not names & {"build", "mypy", "ruff", "pytest-cov", "pytest-xdist", "twine"}
    print(
        f"README {layout}: shell quoting, runtime-only wheel, "
        "PASS/UNKNOWN/test failure/errors passed"
    )
