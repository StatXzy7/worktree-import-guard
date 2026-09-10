"""Filesystem-aware normalization and module-origin resolution."""

from __future__ import annotations

import os
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


def _is_filesystem_origin(value: str | None) -> bool:
    if value is None or value in _NON_FILESYSTEM_ORIGINS:
        return False
    return not (value.startswith("<") and value.endswith(">"))


def resolve_observation(observation: ObservedModule) -> ResolvedObservation:
    """Resolve raw import metadata without guessing through conflicts."""

    spec_is_path = _is_filesystem_origin(observation.spec_origin)
    file_is_path = _is_filesystem_origin(observation.file)
    spec_path = (
        canonicalize_path(observation.spec_origin)
        if spec_is_path and observation.spec_origin is not None
        else None
    )
    file_path = (
        canonicalize_path(observation.file)
        if file_is_path and observation.file is not None
        else None
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
        if _is_filesystem_origin(location):
            return ResolvedObservation(
                module=observation.module,
                origin=location,
                canonical_origin=canonicalize_path(location),
                phase=observation.phase,
                source=observation.source,
            )

    metadata = (observation.spec_origin, observation.file)
    issue = (
        ReasonCode.NON_FILESYSTEM_ORIGIN
        if any(value is not None for value in metadata)
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
