"""The built-in demo must confine all setup writes to disposable directories."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from worktree_import_guard import demo


def test_demo_ignores_external_git_routing_and_hooks(monkeypatch, tmp_path):
    git = shutil.which("git")
    if git is None:
        pytest.skip("Git unavailable")
    clean_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    victim = tmp_path / "user repository"
    victim.mkdir()
    subprocess.run(
        [git, "init", "-b", "main"], cwd=victim, env=clean_env, capture_output=True, check=True
    )
    untouched = victim / "user-untracked.txt"
    untouched.write_text("User content must stay untracked.\n", encoding="utf-8")
    hooks = tmp_path / "user hooks"
    hooks.mkdir()
    marker = tmp_path / "user-hook-ran"
    hook = hooks / "pre-commit"
    hook.write_text(f"#!/bin/sh\necho changed > '{marker.as_posix()}'\n", encoding="utf-8")
    hook.chmod(0o755)
    global_config = tmp_path / "user.gitconfig"
    global_config.write_text(f'[core]\n\thooksPath = "{hooks.as_posix()}"\n', encoding="utf-8")
    monkeypatch.setenv("GIT_DIR", str(victim / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(victim))
    monkeypatch.setenv("GIT_INDEX_FILE", str(victim / ".git" / "index"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(hooks))
    monkeypatch.chdir(tmp_path)
    environment_before = os.environ.copy()

    result = demo.run_demo()

    tracked = subprocess.run(
        [git, "ls-files"], cwd=victim, env=clean_env, capture_output=True, text=True, check=True
    )
    head = subprocess.run(
        [git, "rev-parse", "--verify", "HEAD"],
        cwd=victim,
        env=clean_env,
        capture_output=True,
        check=False,
    )
    assert tracked.stdout == "", "Demo must not stage or commit the user's files"
    assert head.returncode != 0, "Demo must not create a commit in the user's repository"
    assert not marker.exists(), "Demo must not execute user-configured Git hooks"
    assert untouched.read_text(encoding="utf-8") == "User content must stay untracked.\n"
    assert dict(os.environ) == environment_before
    assert result == 0


def test_failed_demo_cleans_up_private_directory(monkeypatch):
    actual_temporary_directory = demo.tempfile.TemporaryDirectory
    created: list[Path] = []

    def temporary_directory(*args, **kwargs):
        temporary = actual_temporary_directory(*args, **kwargs)
        created.append(Path(temporary.name))
        return temporary

    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("controlled-demo-child", 120)

    monkeypatch.setattr(demo.tempfile, "TemporaryDirectory", temporary_directory)
    monkeypatch.setattr(demo.shutil, "which", lambda name: None)
    monkeypatch.setattr(demo, "_run", timed_out)
    assert demo.run_demo() == 1
    assert len(created) == 1
    assert not created[0].exists()


def test_unwritable_temporary_directory_reports_failure(monkeypatch, capsys):
    def unavailable(*args, **kwargs):
        raise OSError("controlled temporary-directory failure")

    monkeypatch.setattr(demo.tempfile, "TemporaryDirectory", unavailable)
    assert demo.run_demo() == 1
    assert "Cannot create private demo directory" in capsys.readouterr().err


def test_without_git_demo_labels_two_directories(monkeypatch, capsys):
    monkeypatch.setattr(demo.shutil, "which", lambda name: None)
    assert demo.run_demo() == 0
    output = capsys.readouterr().out
    assert "two ordinary directories" in output
    assert "CROSS_WORKTREE_IMPORT" not in output


def test_demo_does_not_disable_user_site(monkeypatch):
    monkeypatch.delenv("PYTHONNOUSERSITE", raising=False)

    def stop_after_environment_check(args, directory, env):
        assert "PYTHONNOUSERSITE" not in env
        assert env["PYTHONIOENCODING"] == "utf-8"
        raise RuntimeError("done checking child environment")

    monkeypatch.setattr(demo, "_run", stop_after_environment_check)
    assert demo.run_demo() == 1
