"""Execute the exact public pinned-source install route, not a local wheel substitute."""

import json
import os
import re
import subprocess
import sys

import pytest
from test_installed_worktrees import clean_env, run, script
from test_onboarding import shell_run

pytestmark = [
    pytest.mark.artifact,
    pytest.mark.skipif(
        os.environ.get("WTIG_RUN_ARTIFACT_TESTS") != "1",
        reason="set WTIG_RUN_ARTIFACT_TESTS=1 for public source installation",
    ),
]


def test_public_readme_install_demo_setup_and_repeat(tmp_path, project_root, monkeypatch):
    # Test installation must not inherit a destination outside its disposable venv.
    for key in list(os.environ):
        if key.upper() in {
            "PIP_TARGET",
            "PIP_PREFIX",
            "PIP_USER",
            "PIP_ROOT",
        } or key.upper().startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("PIP_CONFIG_FILE", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    pattern = r"git\+https://github\.com/StatXzy7/worktree-import-guard\.git@([a-f0-9]{40})"
    english = (project_root / "README.md").read_text(encoding="utf-8")
    chinese = (project_root / "README.zh-CN.md").read_text(encoding="utf-8")
    commits = set(re.findall(pattern, english))
    assert len(commits) == 1 and commits == set(re.findall(pattern, chinese))
    commit = commits.pop()
    url = f"git+https://github.com/StatXzy7/worktree-import-guard.git@{commit}"
    project = tmp_path / "public project"
    project.mkdir()
    venv = project / ".venv"
    run([sys.executable, "-m", "venv", str(venv)], cwd=project)
    python, guard = (
        script(venv, "python"),
        venv / ("Scripts/wt-import.exe" if sys.platform == "win32" else "bin/wt-import"),
    )
    # Model an existing supported test environment, not a freshly upgraded pytest.
    shell_run([str(python), "-m", "pip", "install", "pytest==8.2.0"], project)
    shell_run([str(python), "-m", "pip", "install", url], project)
    shell_run([str(python), "-m", "pip", "install", "--force-reinstall", "--no-deps", url], project)
    assert "pytest 8.2.0" in shell_run([str(python), "-m", "pytest", "--version"], project).stdout
    identity = run(
        [
            str(python),
            "-c",
            "from importlib.metadata import distribution; "
            "print(distribution('worktree-import-guard').read_text('direct_url.json'))",
        ],
        cwd=project,
    )
    assert json.loads(identity.stdout)["vcs_info"]["commit_id"] == commit
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
    installed = json.loads(
        run([str(python), "-m", "pip", "list", "--format=json"], cwd=project).stdout
    )
    assert not ({p["name"] for p in installed} & {"build", "mypy", "ruff", "pytest-cov"})
    print(f"Public README source {commit}: install/demo/setup/repeat passed without dev extras")
