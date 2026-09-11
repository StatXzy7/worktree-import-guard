import json
import subprocess
import sys

import pytest

from tests.conftest import write_package, write_test


@pytest.mark.parametrize("layout", ["src", "."])
def test_setup_then_repeat_checks(tmp_path, run_guard, layout):
    project = tmp_path / "中文 project"
    project.mkdir()
    write_package(project / layout, "demo_pkg")
    (project / "conftest.py").write_text(
        f"import sys\nsys.path.insert(0, {str(project / layout)!r})\n", encoding="utf-8"
    )
    write_test(project, "import demo_pkg\ndef test_value():\n    assert demo_pkg.VALUE == 42\n")
    # A scripted terminal exercises exactly the interactive entry, without a TTY dependency.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdin.isatty = lambda: True; "
            "from worktree_import_guard.cli import main; "
            "raise SystemExit(main(['--setup','--','-q']))",
        ],
        input="y\n1\ny\n",
        cwd=project,
        text=True,
        encoding="utf-8",
        capture_output=True,
        env={**__import__("os").environ, "PYTHONUTF8": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1/3" in result.stdout and "3/3" in result.stdout
    config = json.loads((project / ".wt-import.json").read_text(encoding="utf-8"))
    assert list(config["expect"]) == ["demo_pkg"]
    repeated = run_guard(project, "--", "-q")
    assert repeated.completed.returncode == 0
    # Explicit targets replace, rather than append to, the saved contract.
    explicit = run_guard(project, "--expect", "absent=absent", "--", "-q")
    assert [t["package"] for t in explicit.report["targets"]] == ["absent"]
    assert explicit.report["guard"]["status"] == "unknown"
    write_test(project, "import demo_pkg\ndef test_value():\n    assert False\n")
    failed = run_guard(project, "--", "-q")
    assert failed.completed.returncode == 1
    assert failed.report["guard"]["status"] == "pass"
    assert failed.report["pytest"]["exit_code"] == 1


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--setup"],
        ["--demo", "--setup"],
        ["--demo", "--expect", "p=p"],
        ["--demo", "--", "-q"],
        ["--demo", "--cwd", "other"],
    ],
)
def test_noninteractive_and_mixed_modes_fail_without_running(tmp_path, guard_command, args):
    completed = subprocess.run(
        [*guard_command, *args], cwd=tmp_path, input="", capture_output=True, text=True, timeout=10
    )
    assert completed.returncode == 2
    assert not list(tmp_path.iterdir())


def test_installed_demo_has_all_three_results(tmp_path, guard_command):
    result = subprocess.run(
        [*guard_command, "--demo"], cwd=tmp_path, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WORKTREE IMPORT GUARD: FAIL" in result.stdout
    assert "WORKTREE IMPORT GUARD: PASS" in result.stdout
    assert "Demo complete" in result.stdout
    assert not list(tmp_path.iterdir())


def test_doctor_without_config_prompts_like_setup(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdin.isatty = lambda: True; "
            "from worktree_import_guard.cli import main; "
            "raise SystemExit(main(['--doctor','--','-q']))",
        ],
        cwd=tmp_path,
        input="n\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    assert result.returncode == 2
    assert "1/3" in result.stdout
    assert not list(tmp_path.iterdir())


def test_doctor_with_config_reuses_settings(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("VALUE=42\n", encoding="utf-8")
    (tmp_path / ".wt-import.json").write_text(
        '{"schema_version": 1, "expect": {"pkg": "pkg"}}',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdin.isatty = lambda: True; "
            "from worktree_import_guard.cli import main; "
            "raise SystemExit(main(['--doctor','--','-q']))",
        ],
        cwd=tmp_path,
        input="n\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    assert result.returncode == 2
    assert "reuses saved settings" in result.stdout
    assert "1/3" not in result.stdout


def test_broken_config_is_ignored_only_for_explicit_targets(tmp_path, run_guard):
    (tmp_path / ".wt-import.json").write_text("{", encoding="utf-8")
    write_test(tmp_path, "def test_value():\n    pass\n")
    broken = run_guard(tmp_path, "--", "-q")
    assert broken.completed.returncode == 2 and broken.report is None
    assert "could not read" in broken.completed.stderr
    explicit = run_guard(tmp_path, "--expect", "absent=absent", "--", "-q")
    assert explicit.report["pytest"]["exit_code"] == 0


@pytest.mark.parametrize("test_fails", [False, True])
def test_legacy_console_keeps_unicode_json_and_native_exit(
    tmp_path, run_guard, monkeypatch, test_fails
):
    project = tmp_path / "中文 project"
    project.mkdir()
    write_package(project, "pkg")
    write_test(project, f"import pkg\ndef test_value():\n    assert {not test_fails!r}\n")
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")
    result = run_guard(project, "--expect", "pkg=pkg", "--", "-q")
    assert result.completed.returncode == int(test_fails), result.completed.stderr
    assert "UnicodeEncodeError" not in result.completed.stderr
    assert result.report["guard"]["status"] == "pass"
    assert "中文" in result.report["targets"][0]["expected_root"]
