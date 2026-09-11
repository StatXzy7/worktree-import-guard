"""Shared detector revision checks for CLI and Skill helpers."""

from __future__ import annotations

import json
from importlib.metadata import Distribution

from . import __version__

VERIFIED_PREVIEW_COMMIT = "edae3e6fa9a0b065385a080c371c9c17728b4656"


def direct_url_commit(dist: Distribution) -> str | None:
    try:
        direct = json.loads(dist.read_text("direct_url.json") or "null")
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(direct, dict):
        return None
    vcs = direct.get("vcs_info")
    if not isinstance(vcs, dict):
        return None
    commit = vcs.get("commit_id")
    return commit if isinstance(commit, str) and commit else None


def distribution_compatible(dist: Distribution) -> bool:
    """Accept the 0.1.1 candidate or the verified 0.1.0 source preview."""

    if dist.version == "0.1.1":
        return dist.version == __version__
    if dist.version == "0.1.0":
        return direct_url_commit(dist) == VERIFIED_PREVIEW_COMMIT
    return False
