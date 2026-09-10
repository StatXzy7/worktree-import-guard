"""Best-effort discovery of Git worktrees from porcelain output."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .matcher import path_is_within
from .models import GitContext, Worktree
from .origins import canonicalize_path


def _decoded(record: dict[bytes, bytes | None], key: bytes) -> str | None:
    raw = record.get(key)
    return os.fsdecode(raw) if raw is not None else None


def parse_worktree_porcelain(data: bytes) -> tuple[Worktree, ...]:
    """Parse ``git worktree list --porcelain -z`` without line assumptions."""

    records: list[dict[bytes, bytes | None]] = []
    current: dict[bytes, bytes | None] = {}
    for field in data.split(b"\0"):
        if not field:
            if current:
                records.append(current)
                current = {}
            continue
        key, separator, value = field.partition(b" ")
        current[key] = value if separator else None
    if current:
        records.append(current)

    worktrees: list[Worktree] = []
    for record in records:
        raw_path = record.get(b"worktree")
        if raw_path is None:
            continue

        worktrees.append(
            Worktree(
                path=canonicalize_path(os.fsdecode(raw_path)),
                head=_decoded(record, b"HEAD"),
                branch=_decoded(record, b"branch"),
                detached=b"detached" in record,
                bare=b"bare" in record,
                locked=_decoded(record, b"locked"),
                prunable=_decoded(record, b"prunable"),
            )
        )
    return tuple(worktrees)


def containing_worktree(path: Path, worktrees: tuple[Worktree, ...]) -> Worktree | None:
    """Return the deepest known worktree containing a canonical path."""

    matches = [worktree for worktree in worktrees if path_is_within(path, worktree.path)]
    return max(matches, key=lambda worktree: len(worktree.path.parts), default=None)


def discover_git_context(cwd: Path, *, enabled: bool = True) -> GitContext:
    """Discover worktrees, degrading cleanly when Git or a repository is absent."""

    if not enabled:
        return GitContext(available=False)
    try:
        completed = subprocess.run(
            ["git", "-C", os.fspath(cwd), "worktree", "list", "--porcelain", "-z"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return GitContext(available=False)
    if completed.returncode != 0:
        return GitContext(available=True)
    worktrees = parse_worktree_porcelain(completed.stdout)
    current = containing_worktree(cwd, worktrees)
    return GitContext(
        available=True,
        current_worktree=current.path if current is not None else None,
        worktrees=worktrees,
    )
