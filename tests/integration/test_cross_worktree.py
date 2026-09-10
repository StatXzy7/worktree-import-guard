from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from worktree_import_guard.origins import canonicalize_path

pytestmark = pytest.mark.integration


def git(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def test_real_cross_worktree_import_is_caught(
    tmp_path: Path,
    run_guard,
    test_runner_command: list[str],
) -> None:
    main = tmp_path / "repository with spaces"
    feature = tmp_path / "feature worktree"
    main.mkdir()
    git(main, "init", "-b", "main")
    git(main, "config", "user.email", "tests@example.invalid")
    git(main, "config", "user.name", "Integration Test")

    package = main / "src/demo_pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from .core import source_checkout, stable_value\n")
    (package / "core.py").write_text(
        'def stable_value():\n    return 42\n\ndef source_checkout():\n    return "main"\n'
    )
    tests = main / "tests"
    tests.mkdir()
    # This intentionally models a stale environment path. The guard itself never changes sys.path.
    (main / "conftest.py").write_text(
        f"import sys\nsys.path.insert(0, {str(main / 'src')!r})\n",
        encoding="utf-8",
    )
    (tests / "test_value.py").write_text(
        "from demo_pkg.core import stable_value\n\n"
        "def test_stable():\n"
        "    assert stable_value() == 42\n",
        encoding="utf-8",
    )
    git(main, "add", ".")
    git(main, "commit", "-m", "main fixture")
    git(main, "worktree", "add", "-b", "feature", str(feature), "main")

    (feature / "src/demo_pkg/core.py").write_text(
        'def stable_value():\n    return 42\n\ndef source_checkout():\n    return "feature"\n'
    )
    git(feature, "add", "src/demo_pkg/core.py")
    git(feature, "commit", "-m", "feature fixture")

    ordinary = subprocess.run(
        [*test_runner_command, "-q"],
        cwd=feature,
        check=False,
        capture_output=True,
        text=True,
    )
    assert ordinary.returncode == 0, ordinary.stdout + ordinary.stderr
    assert "1 passed" in ordinary.stdout

    guarded = run_guard(feature, "--expect", "demo_pkg=src/demo_pkg", "--", "-q")
    assert guarded.completed.returncode == 1, guarded.completed.stdout + guarded.completed.stderr
    assert guarded.report["pytest"]["exit_code"] == 0
    assert guarded.report["guard"]["status"] == "fail"
    assert guarded.report["targets"][0]["reasons"] == ["CROSS_WORKTREE_IMPORT"]
    observations = guarded.report["targets"][0]["observations"]
    assert any(item["containing_worktree"] == str(canonicalize_path(main)) for item in observations)
    assert "CROSS_WORKTREE_IMPORT" in guarded.completed.stdout
