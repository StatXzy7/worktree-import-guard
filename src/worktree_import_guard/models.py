"""Typed data shared by observation, classification, and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Status(str, Enum):
    """A target or overall guard result."""

    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class ReasonCode(str, Enum):
    """Stable public reason codes."""

    MATCH = "MATCH"
    CROSS_WORKTREE_IMPORT = "CROSS_WORKTREE_IMPORT"
    OUTSIDE_EXPECTED_ROOT = "OUTSIDE_EXPECTED_ROOT"
    MIXED_ORIGINS = "MIXED_ORIGINS"
    TARGET_NOT_OBSERVED = "TARGET_NOT_OBSERVED"
    ORIGIN_UNRESOLVED = "ORIGIN_UNRESOLVED"
    ORIGIN_METADATA_CONFLICT = "ORIGIN_METADATA_CONFLICT"
    NON_FILESYSTEM_ORIGIN = "NON_FILESYSTEM_ORIGIN"
    UNSUPPORTED_NAMESPACE_LAYOUT = "UNSUPPORTED_NAMESPACE_LAYOUT"
    UNSUPPORTED_RUNTIME = "UNSUPPORTED_RUNTIME"
    OBSERVATION_ERROR = "OBSERVATION_ERROR"


@dataclass(frozen=True)
class PackageContract:
    """A declared package and the canonical directory it must come from."""

    package: str
    declared_path: str
    expected_root: Path


@dataclass(frozen=True)
class ObservedModule:
    """Raw import metadata captured at one observation boundary."""

    module: str
    spec_origin: str | None
    file: str | None
    search_locations: tuple[str, ...]
    phase: str
    source: str
    capture_cwd: str | None = None
    canonical_spec_origin: str | None = None
    canonical_file: str | None = None
    canonical_search_locations: tuple[str, ...] = ()
    paths_frozen: bool = False


@dataclass(frozen=True)
class ResolvedObservation:
    """An observation resolved into conservative filesystem evidence."""

    module: str
    origin: str | None
    canonical_origin: Path | None
    phase: str
    source: str
    issue: ReasonCode | None = None
    inside_expected: bool | None = None
    containing_worktree: Path | None = None


@dataclass(frozen=True)
class Worktree:
    """One record from Git's NUL-delimited worktree porcelain output."""

    path: Path
    head: str | None = None
    branch: str | None = None
    detached: bool = False
    bare: bool = False
    locked: str | None = None
    prunable: str | None = None


@dataclass(frozen=True)
class GitContext:
    """Best-effort Git context; path checking does not depend on it."""

    available: bool
    current_worktree: Path | None = None
    worktrees: tuple[Worktree, ...] = ()


@dataclass(frozen=True)
class TargetResult:
    """The deterministic result for one package contract."""

    package: str
    expected_root: Path
    status: Status
    reasons: tuple[ReasonCode, ...]
    observations: tuple[ResolvedObservation, ...] = ()


@dataclass(frozen=True)
class GuardResult:
    """Aggregate guard result."""

    status: Status
    complete: bool
    targets: tuple[TargetResult, ...]
    observation_complete: bool = True
    observation_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunReport:
    """The single source for both human and JSON reports."""

    cwd: Path
    python: Path
    pytest_args: tuple[str, ...]
    pytest_exit_code: int
    guard: GuardResult
    git: GitContext
    xdist: bool = False
    python_resolved: Path | None = None
    sys_prefix: str | None = None
    sys_base_prefix: str | None = None
    python_version: str | None = None
    pytest_version: str | None = None
    metrics: dict[str, int | float] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)
