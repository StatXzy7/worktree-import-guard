from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from worktree_import_guard.models import (
    GitContext,
    GuardResult,
    ReasonCode,
    ResolvedObservation,
    RunReport,
    Status,
    TargetResult,
)
from worktree_import_guard.report import render_human


def report_for(reason: ReasonCode, status: Status = Status.UNKNOWN) -> RunReport:
    target = TargetResult("demo_pkg", Path("src/demo_pkg"), status, (reason,))
    return RunReport(
        Path("project"),
        Path("python"),
        (),
        0,
        GuardResult(status, status is not Status.UNKNOWN, (target,)),
        GitContext(False),
    )


def test_pytest_failure_and_source_pass_are_distinct() -> None:
    report = replace(report_for(ReasonCode.MATCH, Status.PASS), pytest_exit_code=1)
    text = render_human(report)
    assert text.startswith("Tests failed.\nWORKTREE IMPORT GUARD: PASS\n")
    assert "Observed sources for the selected packages match" in text
    assert "expected: src" in text
    assert "Tests passed" not in text


@pytest.mark.parametrize(
    ("reason", "explanation"),
    [
        (ReasonCode.TARGET_NOT_OBSERVED, "No target import was observed"),
        (ReasonCode.ORIGIN_UNRESOLVED, "Source metadata could not be resolved reliably"),
        (ReasonCode.ORIGIN_METADATA_CONFLICT, "Source metadata could not be resolved reliably"),
        (ReasonCode.UNSUPPORTED_NAMESPACE_LAYOUT, "namespace layout cannot be verified"),
        (ReasonCode.UNSUPPORTED_RUNTIME, "execution mode cannot be verified"),
    ],
)
def test_unknown_explains_why_and_what_next(reason: ReasonCode, explanation: str) -> None:
    text = render_human(report_for(reason))
    assert "demo_pkg: UNKNOWN" in text
    assert "UNKNOWN is not a pass" in text
    assert explanation in text
    if reason is not ReasonCode.TARGET_NOT_OBSERVED:
        assert "<not observed>" not in text


def test_mismatch_does_not_invent_a_worktree_and_keeps_unknown_targets() -> None:
    report = report_for(ReasonCode.OUTSIDE_EXPECTED_ROOT, Status.FAIL)
    unknown = report_for(ReasonCode.TARGET_NOT_OBSERVED).guard.targets[0]
    unknown = replace(unknown, package="second_pkg")
    report = replace(
        report,
        guard=replace(report.guard, complete=False, targets=(*report.guard.targets, unknown)),
    )
    text = render_human(report)
    assert "demo_pkg: FAIL" in text and "second_pkg: UNKNOWN" in text
    assert "another worktree" not in text
    cross = render_human(report_for(ReasonCode.CROSS_WORKTREE_IMPORT, Status.FAIL))
    assert "another worktree" in cross


def test_incomplete_failure_keeps_unresolved_evidence_visible() -> None:
    report = report_for(ReasonCode.OUTSIDE_EXPECTED_ROOT, Status.FAIL)
    observation = ResolvedObservation(
        "demo_pkg.dynamic", None, None, "test", "unit", issue=ReasonCode.ORIGIN_UNRESOLVED
    )
    target = replace(report.guard.targets[0], observations=(observation,))
    report = replace(
        report,
        guard=replace(report.guard, targets=(target,), complete=False, observation_complete=False),
    )
    text = render_human(report)
    assert "issue:    ORIGIN_UNRESOLVED" in text
    assert "Observation was incomplete" in text
    assert "guard:      FAIL" in text


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ([], "no package settings; run --setup"),
        (["--expect", "demo_pkg"], "demo_pkg=src/demo_pkg"),
        (["--expect", "demo_pkg=src/demo_pkg", "--cwd", "missing directory"], "check --cwd"),
    ],
)
def test_configuration_errors_are_actionable(tmp_path: Path, run_guard, args, expected) -> None:
    result = run_guard(tmp_path, *args, report=False).completed
    assert result.returncode == 2
    assert expected in result.stderr
    assert "Traceback" not in result.stderr


def test_help_teaches_layout_and_environment(tmp_path: Path, run_guard) -> None:
    result = run_guard(tmp_path, "--help", report=False).completed
    assert result.returncode == 0
    assert "demo_pkg=src/demo_pkg" in result.stdout
    assert "demo_pkg=demo_pkg" in result.stdout
    assert "pytest environment" in result.stdout
