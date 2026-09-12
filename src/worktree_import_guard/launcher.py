"""Bound entrypoint helpers for the installed ``wt-import`` command."""

from __future__ import annotations

import os
import shlex
import sysconfig
from collections.abc import Sequence
from importlib.metadata import Distribution
from pathlib import Path


def console_script(dist: Distribution) -> Path:
    """Resolve the installed ``wt-import`` script for this distribution.

    Prefer the current interpreter's configured script directory, but fall back to a
    unique recorded script when that path is not the one used for this distribution.
    """

    candidate_name = "wt-import.exe" if os.name == "nt" else "wt-import"
    preferred = Path(sysconfig.get_path("scripts")) / candidate_name
    recorded = {
        Path(str(dist.locate_file(path))).resolve()
        for path in (dist.files or ())
        if Path(path).name == candidate_name
    }
    if preferred.resolve() in recorded and preferred.is_file():
        return preferred
    existing = sorted(path for path in recorded if path.is_file())
    if len(existing) != 1:
        raise ValueError("Cannot identify one installed console script in this environment")
    return existing[0]


def quote_for_shell(value: str) -> str:
    """Quote one command token for the current shell."""

    if os.name == "nt":
        return "'" + value.replace("'", "''") + "'"
    return shlex.quote(value)


def command_for_path(script: Path, args: Sequence[str] | None = None) -> str:
    """Return a copy-ready command line bound to one concrete script path."""

    args = tuple(args or ())
    if os.name == "nt":
        return "& " + " ".join((quote_for_shell(str(script)), *map(quote_for_shell, args)))
    return " ".join((quote_for_shell(str(script)), *map(quote_for_shell, args)))
