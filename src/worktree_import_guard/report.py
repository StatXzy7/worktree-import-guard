"""Classification plus deterministic human and JSON rendering."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from . import __version__
from .git_worktrees import containing_worktree
from .matcher import path_is_within
from .models import (
    GitContext,
    GuardResult,
    PackageContract,
    ReasonCode,
    ResolvedObservation,
    RunReport,
    Status,
    TargetResult,
)
from .observer import ImportObserver
from .origins import resolve_observation

_REASON_ORDER = {reason: index for index, reason in enumerate(ReasonCode)}


def _ordered_reasons(reasons: set[ReasonCode]) -> tuple[ReasonCode, ...]:
    return tuple(sorted(reasons, key=_REASON_ORDER.__getitem__))


def _resolve_target(
    contract: PackageContract,
    observer: ImportObserver,
    git: GitContext,
) -> tuple[ResolvedObservation, ...]:
    resolved: list[ResolvedObservation] = []
    for raw in observer.observations_for(contract.package):
        item = resolve_observation(raw)
        if item.canonical_origin is not None:
            worktree = containing_worktree(item.canonical_origin, git.worktrees)
            item = replace(
                item,
                inside_expected=path_is_within(item.canonical_origin, contract.expected_root),
                containing_worktree=worktree.path if worktree is not None else None,
            )
        resolved.append(item)
    return tuple(
        sorted(
            resolved,
            key=lambda item: (
                item.module,
                item.origin or "",
                item.issue.value if item.issue is not None else "",
                item.phase,
            ),
        )
    )


def _is_cross_worktree(
    contract: PackageContract,
    observations: tuple[ResolvedObservation, ...],
    git: GitContext,
) -> bool:
    expected = containing_worktree(contract.expected_root, git.worktrees)
    if expected is None:
        return False
    return any(
        item.inside_expected is False
        and item.containing_worktree is not None
        and item.containing_worktree != expected.path
        for item in observations
    )


def classify(
    contracts: tuple[PackageContract, ...],
    observer: ImportObserver,
    git: GitContext,
) -> GuardResult:
    """Classify retained evidence according to the public V0.1 status model."""

    targets: list[TargetResult] = []
    for contract in contracts:
        observations = _resolve_target(contract, observer, git)
        reasons: tuple[ReasonCode, ...]
        if observer.unsupported_reason is not None:
            status = Status.UNKNOWN
            reasons = (observer.unsupported_reason,)
        else:
            inside = any(item.inside_expected is True for item in observations)
            outside = any(item.inside_expected is False for item in observations)
            issues = {item.issue for item in observations if item.issue is not None}
            if outside:
                status = Status.FAIL
                if inside:
                    reasons = (ReasonCode.MIXED_ORIGINS,)
                elif _is_cross_worktree(contract, observations, git):
                    reasons = (ReasonCode.CROSS_WORKTREE_IMPORT,)
                else:
                    reasons = (ReasonCode.OUTSIDE_EXPECTED_ROOT,)
            elif issues:
                status = Status.UNKNOWN
                reasons = _ordered_reasons(issues)
            elif inside:
                status = Status.PASS
                reasons = (ReasonCode.MATCH,)
            elif observer.was_audited(contract.package):
                status = Status.UNKNOWN
                reasons = (ReasonCode.ORIGIN_UNRESOLVED,)
            else:
                status = Status.UNKNOWN
                reasons = (ReasonCode.TARGET_NOT_OBSERVED,)
        targets.append(
            TargetResult(
                package=contract.package,
                expected_root=contract.expected_root,
                status=status,
                reasons=reasons,
                observations=observations,
            )
        )

    statuses = {target.status for target in targets}
    if Status.FAIL in statuses:
        overall = Status.FAIL
    elif Status.UNKNOWN in statuses:
        overall = Status.UNKNOWN
    else:
        overall = Status.PASS
    return GuardResult(
        status=overall,
        complete=observer.unsupported_reason is None,
        targets=tuple(targets),
    )


def _observation_dict(observation: ResolvedObservation) -> dict[str, object]:
    return {
        "module": observation.module,
        "origin": observation.origin,
        "canonical_origin": (
            str(observation.canonical_origin) if observation.canonical_origin is not None else None
        ),
        "phase": observation.phase,
        "source": observation.source,
        "containing_worktree": (
            str(observation.containing_worktree)
            if observation.containing_worktree is not None
            else None
        ),
        "issue": observation.issue.value if observation.issue is not None else None,
    }


def report_dict(report: RunReport) -> dict[str, object]:
    """Return the stable schema-versioned JSON-compatible shape."""

    return {
        "schema_version": 1,
        "tool": {"name": "worktree-import-guard", "version": __version__},
        "run": {
            "cwd": str(report.cwd),
            "python": str(report.python),
            "pytest_args": list(report.pytest_args),
        },
        "pytest": {"exit_code": report.pytest_exit_code},
        "guard": {
            "status": report.guard.status.value,
            "complete": report.guard.complete,
        },
        "targets": [
            {
                "package": target.package,
                "expected_root": str(target.expected_root),
                "status": target.status.value,
                "reasons": [reason.value for reason in target.reasons],
                "observations": [
                    _observation_dict(observation) for observation in target.observations
                ],
            }
            for target in report.guard.targets
        ],
        "git": {
            "available": report.git.available,
            "current_worktree": (
                str(report.git.current_worktree)
                if report.git.current_worktree is not None
                else None
            ),
            "worktrees": [
                {
                    "path": str(worktree.path),
                    "head": worktree.head,
                    "branch": worktree.branch,
                    "detached": worktree.detached,
                    "bare": worktree.bare,
                    "locked": worktree.locked,
                    "prunable": worktree.prunable,
                }
                for worktree in report.git.worktrees
            ],
        },
        "scope": {
            "process": "current-pytest-process",
            "xdist": report.xdist,
            "child_process_imports": False,
        },
    }


def render_json(report: RunReport) -> str:
    """Render stable, newline-terminated JSON."""

    return json.dumps(report_dict(report), indent=2, sort_keys=True) + "\n"


def render_human(report: RunReport, *, show_all: bool = False) -> str:
    """Render compact terminal text from exactly the JSON report model."""

    lines = [f"WORKTREE IMPORT GUARD: {report.guard.status.value.upper()}", ""]
    visible = [
        target for target in report.guard.targets if show_all or target.status is not Status.PASS
    ]
    if not visible:
        lines.append(f"targets: {', '.join(target.package for target in report.guard.targets)}")
        lines.append("")
    for target in visible:
        lines.extend([target.package, f"expected: {target.expected_root}"])
        mixed = ReasonCode.MIXED_ORIGINS in target.reasons
        shown_observations = [
            item
            for item in target.observations
            if show_all or mixed or item.inside_expected is not True or item.issue is not None
        ]
        if shown_observations:
            for item in shown_observations:
                lines.append(f"observed: {item.origin or '<unresolved>'} ({item.module})")
                if item.containing_worktree is not None:
                    lines.append(f"worktree: {item.containing_worktree}")
        else:
            lines.append("observed: <not observed>")
        lines.append(f"reason:   {', '.join(reason.value for reason in target.reasons)}")
        lines.append("")
    lines.extend(
        [
            f"pytest exit: {report.pytest_exit_code}",
            f"guard:      {report.guard.status.value.upper()}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json_report(path: Path, report: RunReport) -> None:
    """Write the stable report without implicitly creating directories."""

    path.write_text(render_json(report), encoding="utf-8")
