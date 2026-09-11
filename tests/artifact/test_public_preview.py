"""Execute the exact public PyPI install route from README, not a local wheel substitute."""

import json
import os
import subprocess
import sys

import pytest
from test_installed_worktrees import clean_env, run, script
from test_onboarding import shell_run

pytestmark = [
    pytest.mark.artifact,
    pytest.mark.skipif(
        os.environ.get("WTIG_RUN_ARTIFACT_TESTS") != "1",
        reason="set WTIG_RUN_ARTIFACT_TESTS=1 for public PyPI installation",
    ),
]

PYPI_SPEC = "worktree-import-guard==0.1.2"


def test_public_readme_pypi_install_demo_setup_and_repeat(tmp_path, project_root, monkeypatch):
    for key in list(os.environ):
        if key.upper() in {
            "PIP_TARGET",
            "PIP_PREFIX",
            "PIP_USER",
            "PIP_ROOT",
        } or key.upper().startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("PIP_CONFIG_FILE", os.devnull)
    english = (project_root / "README.md").read_text(encoding="utf-8")
    chinese = (project_root / "README.zh-CN.md").read_text(encoding="utf-8")
    assert english.count(PYPI_SPEC) >= 2 and chinese.count(PYPI_SPEC) >= 2
    project = tmp_path / "public project"
    project.mkdir()
    venv = project / ".venv"
    run([sys.executable, "-m", "venv", str(venv)], cwd=project)
    python, guard = (
        script(venv, "python"),
        venv / ("Scripts/wt-import.exe" if sys.platform == "win32" else "bin/wt-import"),
    )
    shell_run([str(python), "-m", "pip", "install", "pytest==8.2.0"], project)
    wheel_value = os.environ.get("WTIG_ARTIFACT_WHEEL")
    if wheel_value:
        from pathlib import Path

        shell_run([str(python), "-m", "pip", "install", str(Path(wheel_value).resolve())], project)
    else:
        shell_run([str(python), "-m", "pip", "install", PYPI_SPEC], project)
    assert "pytest 8.2.0" in shell_run([str(python), "-m", "pytest", "--version"], project).stdout
    assert shell_run([str(guard), "--version"], project).stdout.strip() == "wt-import 0.1.2"
    shell_run([str(guard), "--help"], project)
    assert "Demo complete" in shell_run([str(guard), "--demo"], project).stdout
    package = project / "src/demo_pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE=42\n", encoding="utf-8")
    (project / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0,str(Path(__file__).parent/'src'))\n",
        encoding="utf-8",
    )
    (project / "test_sample.py").write_text(
        "import demo_pkg\ndef test_value():\n    assert demo_pkg.VALUE==42\n",
        encoding="utf-8",
    )
    setup = subprocess.run(
        [
            str(python),
            "-c",
            "import sys; sys.stdin.isatty=lambda:True; "
            "from worktree_import_guard.cli import main; raise SystemExit(main(['--setup']))",
        ],
        cwd=project,
        env=clean_env(),
        input="y\n1\ny\n",
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert setup.returncode == 0, setup.stdout + setup.stderr
    assert "WORKTREE IMPORT GUARD: PASS" in shell_run([str(guard), "--", "-q"], project).stdout
    doctor = subprocess.run(
        [
            str(python),
            "-c",
            "import sys; sys.stdin.isatty=lambda:True; "
            "from worktree_import_guard.cli import main; "
            "raise SystemExit(main(['--doctor','--','-q']))",
        ],
        cwd=project,
        env=clean_env(),
        input="y\n",
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    installed = json.loads(
        run([str(python), "-m", "pip", "list", "--format=json"], cwd=project).stdout
    )
    assert not ({p["name"] for p in installed} & {"build", "mypy", "ruff", "pytest-cov"})
    print(
        f"Public README PyPI {PYPI_SPEC}: "
        "install/demo/setup/doctor/repeat passed without dev extras"
    )


def test_legacy_preview_refresh_then_pypi_upgrade(tmp_path, project_root, monkeypatch):
    preview = "edae3e6fa9a0b065385a080c371c9c17728b4656"
    url = f"git+https://github.com/StatXzy7/worktree-import-guard.git@{preview}"
    for key in list(os.environ):
        if key.upper().startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("PIP_CONFIG_FILE", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    project = tmp_path / "legacy preview"
    project.mkdir()
    venv = project / ".venv"
    run([sys.executable, "-m", "venv", str(venv)], cwd=project)
    python = script(venv, "python")
    guard = venv / ("Scripts/wt-import.exe" if sys.platform == "win32" else "bin/wt-import")
    shell_run([str(python), "-m", "pip", "install", "pytest==8.2.0"], project)
    shell_run([str(python), "-m", "pip", "install", url], project)
    shell_run([str(python), "-m", "pip", "install", "--force-reinstall", "--no-deps", url], project)
    shell_run([str(python), "-m", "pip", "install", "--upgrade", PYPI_SPEC], project)
    assert shell_run([str(guard), "--version"], project).stdout.strip() == "wt-import 0.1.2"
    assert "Demo complete" in shell_run([str(guard), "--demo"], project).stdout
    print(f"Legacy preview {preview} -> {PYPI_SPEC} upgrade passed")
