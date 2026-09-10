"""Filesystem-aware normalization and module-origin resolution."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .models import ObservedModule, ReasonCode, ResolvedObservation

_NON_FILESYSTEM_ORIGINS = {"built-in", "frozen", "namespace"}


def canonicalize_path(value: str | os.PathLike[str], *, base: Path | None = None) -> Path:
    """Resolve dot segments/symlinks and normalize platform case conventions."""

    path = Path(value).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    resolved = path.resolve(strict=False)
    return Path(os.path.normcase(str(resolved)))


_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")


def is_filesystem_origin(value: str | None) -> bool:
    """Reject import sentinels and URI-like loader origins conservatively."""

    if value is None or value in _NON_FILESYSTEM_ORIGINS:
        return False
    if value.startswith("<") and value.endswith(">"):
        return False
    return not (_URI_SCHEME.match(value) and not _WINDOWS_DRIVE.match(value))


def freeze_path(value: str | None, *, cwd: Path) -> str | None:
    """Canonicalize filesystem evidence at observation time."""

    if not is_filesystem_origin(value):
        return None
    assert value is not None
    try:
        return str(canonicalize_path(value, base=cwd))
    except (OSError, RuntimeError, ValueError):
        return None


def _observation_path(
    raw: str | None,
    frozen: str | None,
    *,
    capture_cwd: str | None,
    paths_frozen: bool,
) -> Path | None:
    if paths_frozen:
        return Path(frozen) if frozen is not None else None
    if not is_filesystem_origin(raw) or raw is None:
        return None
    return canonicalize_path(raw, base=Path(capture_cwd) if capture_cwd is not None else None)


def resolve_observation(observation: ObservedModule) -> ResolvedObservation:
    """Resolve raw import metadata without guessing through conflicts."""

    spec_path = _observation_path(
        observation.spec_origin,
        observation.canonical_spec_origin,
        capture_cwd=observation.capture_cwd,
        paths_frozen=observation.paths_frozen,
    )
    file_path = _observation_path(
        observation.file,
        observation.canonical_file,
        capture_cwd=observation.capture_cwd,
        paths_frozen=observation.paths_frozen,
    )

    if spec_path is not None and file_path is not None and spec_path != file_path:
        detail = f"spec={observation.spec_origin}; file={observation.file}"
        return ResolvedObservation(
            module=observation.module,
            origin=detail,
            canonical_origin=None,
            phase=observation.phase,
            source=observation.source,
            issue=ReasonCode.ORIGIN_METADATA_CONFLICT,
        )

    concrete = spec_path or file_path
    reported = observation.spec_origin if spec_path is not None else observation.file
    if concrete is not None:
        return ResolvedObservation(
            module=observation.module,
            origin=reported,
            canonical_origin=concrete,
            phase=observation.phase,
            source=observation.source,
        )

    if observation.search_locations:
        if len(observation.search_locations) != 1:
            return ResolvedObservation(
                module=observation.module,
                origin="; ".join(observation.search_locations),
                canonical_origin=None,
                phase=observation.phase,
                source=observation.source,
                issue=ReasonCode.UNSUPPORTED_NAMESPACE_LAYOUT,
            )
        location = observation.search_locations[0]
        if is_filesystem_origin(location):
            frozen_location = next(iter(observation.canonical_search_locations), None)
            canonical_location = _observation_path(
                location,
                frozen_location,
                capture_cwd=observation.capture_cwd,
                paths_frozen=observation.paths_frozen,
            )
            if canonical_location is not None:
                return ResolvedObservation(
                    module=observation.module,
                    origin=location,
                    canonical_origin=canonical_location,
                    phase=observation.phase,
                    source=observation.source,
                )

    metadata = (observation.spec_origin, observation.file)
    issue = (
        ReasonCode.NON_FILESYSTEM_ORIGIN
        if any(value is not None and not is_filesystem_origin(value) for value in metadata)
        or any(not is_filesystem_origin(value) for value in observation.search_locations)
        else ReasonCode.ORIGIN_UNRESOLVED
    )
    return ResolvedObservation(
        module=observation.module,
        origin=observation.spec_origin or observation.file,
        canonical_origin=None,
        phase=observation.phase,
        source=observation.source,
        issue=issue,
    )
