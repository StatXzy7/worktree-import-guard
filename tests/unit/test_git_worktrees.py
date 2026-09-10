from __future__ import annotations

import subprocess
from pathlib import Path

from worktree_import_guard.git_worktrees import (
    containing_worktree,
    discover_git_context,
    parse_worktree_porcelain,
)
from worktree_import_guard.origins import canonicalize_path


def test_parse_nul_porcelain_with_spaces_and_flags(tmp_path: Path) -> None:
    first = tmp_path / "main worktree"
    second = tmp_path / "feature\nworktree"
    payload = (
        b"worktree "
        + str(first).encode()
        + b"\0HEAD abc\0branch refs/heads/main\0\0worktree "
        + str(second).encode()
        + b"\0HEAD def\0detached\0locked reason with spaces\0\0"
    )
    worktrees = parse_worktree_porcelain(payload)
    assert len(worktrees) == 2
    assert worktrees[0].path == canonicalize_path(first)
    assert worktrees[0].branch == "refs/heads/main"
    assert worktrees[1].detached
    assert worktrees[1].locked == "reason with spaces"
    assert containing_worktree(worktrees[0].path / "src/pkg.py", worktrees) == worktrees[0]


def test_git_unavailable_and_disabled(monkeypatch, tmp_path: Path) -> None:
    def missing(*args, **kwargs):
        del args, kwargs
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing)
    assert not discover_git_context(tmp_path).available

    def forbidden(*args, **kwargs):
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(subprocess, "run", forbidden)
    disabled = discover_git_context(tmp_path, enabled=False)
    assert not disabled.available
    assert disabled.worktrees == ()


def test_non_repository_still_reports_git_executable(monkeypatch, tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess([], 128, stdout=b"", stderr=b"")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)
    context = discover_git_context(tmp_path)
    assert context.available
    assert context.current_worktree is None
