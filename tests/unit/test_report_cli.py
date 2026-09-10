from __future__ import annotations

import json
from pathlib import Path

from worktree_import_guard.cli import composite_exit_code, report_write_failure_exit_code
from worktree_import_guard.models import (
    GitContext,
    GuardResult,
    ObservedModule,
    PackageContract,
    ReasonCode,
    ResolvedObservation,
    RunReport,
    Status,
    TargetResult,
    Worktree,
)
from worktree_import_guard.observer import ImportObserver
from worktree_import_guard.origins import canonicalize_path
from worktree_import_guard.report import classify, render_human, render_json, report_dict


def observer_with(
    contract: PackageContract,
    observations: list[ObservedModule],
    *,
    audited: bool = False,
) -> ImportObserver:
    observer = ImportObserver((contract,))
    observer._observations[contract.package] = observations
    if audited:
        observer._audit_names[contract.package].add(contract.package)
    return observer


def raw(module: str, path: Path) -> ObservedModule:
    return ObservedModule(module, str(path), str(path), (), "test", "unit")


def test_classification_pass_fail_mixed_and_unknown(tmp_path: Path) -> None:
    root = canonicalize_path(tmp_path / "expected/pkg")
    contract = PackageContract("pkg", "expected/pkg", root)
    inside = tmp_path / "expected/pkg/__init__.py"
    outside = tmp_path / "external/pkg/__init__.py"

    passed = classify((contract,), observer_with(contract, [raw("pkg", inside)]), GitContext(False))
    assert passed.status is Status.PASS

    failed = classify(
        (contract,), observer_with(contract, [raw("pkg", outside)]), GitContext(False)
    )
    assert failed.status is Status.FAIL
    assert failed.targets[0].reasons[0].value == "OUTSIDE_EXPECTED_ROOT"

    mixed = classify(
        (contract,),
        observer_with(contract, [raw("pkg", inside), raw("pkg.foreign", outside)]),
        GitContext(False),
    )
    assert mixed.targets[0].reasons[0].value == "MIXED_ORIGINS"
    mixed_human = render_human(RunReport(tmp_path, Path("python"), (), 0, mixed, GitContext(False)))
    assert str(inside) in mixed_human
    assert str(outside) in mixed_human

    unseen_observer = observer_with(contract, [])
    unseen = classify((contract,), unseen_observer, GitContext(False))
    assert unseen.status is Status.UNKNOWN
    assert unseen.targets[0].reasons[0].value == "TARGET_NOT_OBSERVED"

    audited = classify((contract,), observer_with(contract, [], audited=True), GitContext(False))
    assert audited.targets[0].reasons[0].value == "ORIGIN_UNRESOLVED"


def test_cross_worktree_classification(tmp_path: Path) -> None:
    main = canonicalize_path(tmp_path / "main")
    feature = canonicalize_path(tmp_path / "feature")
    contract = PackageContract("pkg", "src/pkg", feature / "src/pkg")
    context = GitContext(
        True,
        feature,
        (Worktree(main, branch="refs/heads/main"), Worktree(feature, branch="refs/heads/feature")),
    )
    result = classify(
        (contract,), observer_with(contract, [raw("pkg", main / "src/pkg/__init__.py")]), context
    )
    assert result.targets[0].reasons[0].value == "CROSS_WORKTREE_IMPORT"
    assert result.targets[0].observations[0].containing_worktree == main


def test_json_and_human_share_result_model(tmp_path: Path) -> None:
    root = canonicalize_path(tmp_path / "pkg")
    contract = PackageContract("pkg", "pkg", root)
    guard = classify(
        (contract,), observer_with(contract, [raw("pkg", root / "__init__.py")]), GitContext(False)
    )
    report = RunReport(tmp_path, Path("python"), ("-q",), 0, guard, GitContext(False))
    data = report_dict(report)
    assert data["schema_version"] == 2
    assert data["scope"] == {
        "process": "current-pytest-process",
        "xdist": False,
        "child_process_imports": False,
    }
    assert data["guard"] == {
        "complete": True,
        "observation_complete": True,
        "status": "pass",
    }
    assert data["run"]["python"] == "python"
    assert data["run"]["python_resolved"] is None
    assert json.loads(render_json(report)) == data
    assert render_json(report) == render_json(report)
    human = render_human(report)
    assert "WORKTREE IMPORT GUARD: PASS" in human
    assert "guard:      PASS" in human
    assert str(root / "__init__.py") not in human
    assert str(root / "__init__.py") in render_human(report, show_all=True)


def test_composite_exit_code_policy() -> None:
    assert composite_exit_code(0, Status.PASS) == 0
    assert composite_exit_code(0, Status.FAIL) == 1
    assert composite_exit_code(0, Status.UNKNOWN) == 2
    for native in (1, 2, 3, 4, 5, 17):
        assert composite_exit_code(native, Status.PASS) == native


def test_unknown_is_not_complete_and_report_failure_preserves_pytest() -> None:
    root = Path("expected")
    contract = PackageContract("pkg", "expected", root)
    unknown = classify((contract,), observer_with(contract, []), GitContext(False))
    assert unknown.status is Status.UNKNOWN
    assert unknown.complete is False
    assert unknown.observation_complete is True

    unsupported_observer = observer_with(contract, [])
    unsupported_observer.mark_unsupported(ReasonCode.UNSUPPORTED_RUNTIME)
    unsupported = classify((contract,), unsupported_observer, GitContext(False))
    assert unsupported.status is Status.UNKNOWN
    assert unsupported.complete is False
    assert unsupported.observation_complete is False
    assert unsupported.targets[0].reasons == (ReasonCode.UNSUPPORTED_RUNTIME,)

    assert report_write_failure_exit_code(0) == 2
    for native in (1, 2, 3, 4, 5, 17):
        assert report_write_failure_exit_code(native) == native


def test_definite_wrong_origin_survives_incomplete_evidence_and_observation(tmp_path: Path) -> None:
    root = canonicalize_path(tmp_path / "expected/pkg")
    contract = PackageContract("pkg", "expected/pkg", root)
    outside = raw("pkg", tmp_path / "external/pkg/__init__.py")
    unresolved = ObservedModule("pkg.dynamic", None, None, (), "test", "unit")

    evidence_incomplete = classify(
        (contract,), observer_with(contract, [outside, unresolved]), GitContext(False)
    )
    assert evidence_incomplete.status is Status.FAIL
    assert evidence_incomplete.complete is False
    assert evidence_incomplete.observation_complete is True
    assert evidence_incomplete.targets[0].reasons == (ReasonCode.OUTSIDE_EXPECTED_ROOT,)
    assert evidence_incomplete.targets[0].observations[1].issue is ReasonCode.ORIGIN_UNRESOLVED

    unsupported_observer = observer_with(contract, [outside])
    unsupported_observer.mark_unsupported(ReasonCode.UNSUPPORTED_RUNTIME)
    observation_incomplete = classify((contract,), unsupported_observer, GitContext(False))
    assert observation_incomplete.status is Status.FAIL
    assert observation_incomplete.complete is True
    assert observation_incomplete.observation_complete is False
    assert observation_incomplete.targets[0].reasons == (ReasonCode.OUTSIDE_EXPECTED_ROOT,)


def test_schema_v2_golden_reports() -> None:
    golden_dir = Path(__file__).parents[1] / "golden"
    cases = {
        "pass": (Status.PASS, True, "MATCH", 0),
        "fail": (Status.FAIL, True, "OUTSIDE_EXPECTED_ROOT", 0),
        "unknown": (Status.UNKNOWN, False, "TARGET_NOT_OBSERVED", 0),
        "pytest-interrupted": (Status.PASS, True, "MATCH", 2),
        "pytest-usage-error": (Status.UNKNOWN, False, "TARGET_NOT_OBSERVED", 4),
        "pytest-no-tests": (Status.UNKNOWN, False, "TARGET_NOT_OBSERVED", 5),
        "observation-incomplete": (Status.UNKNOWN, False, "UNSUPPORTED_RUNTIME", 4),
    }
    for name, (status, complete, reason, pytest_exit_code) in cases.items():
        target = TargetResult(
            package="pkg",
            expected_root=Path("expected"),
            status=status,
            reasons=(next(item for item in ReasonCode if item.value == reason),),
        )
        guard = GuardResult(
            status,
            complete,
            (target,),
            observation_complete=name != "observation-incomplete",
        )
        report = RunReport(
            cwd=Path("cwd"),
            python=Path("python"),
            pytest_args=("-q",),
            pytest_exit_code=pytest_exit_code,
            guard=guard,
            git=GitContext(False),
            python_resolved=Path("resolved-python"),
            sys_prefix="prefix",
            sys_base_prefix="base-prefix",
            python_version="3.13.5",
            pytest_version="9.1.1",
        )
        expected = json.loads((golden_dir / f"schema-v2-{name}.json").read_text())
        assert json.loads(render_json(report)) == expected

    unresolved = ResolvedObservation(
        module="pkg.dynamic",
        origin=None,
        canonical_origin=None,
        phase="test",
        source="unit",
        issue=ReasonCode.ORIGIN_UNRESOLVED,
    )
    failed_target = TargetResult(
        package="pkg",
        expected_root=Path("expected"),
        status=Status.FAIL,
        reasons=(ReasonCode.OUTSIDE_EXPECTED_ROOT,),
        observations=(unresolved,),
    )
    incomplete_report = RunReport(
        cwd=Path("cwd"),
        python=Path("python"),
        pytest_args=("-q",),
        pytest_exit_code=0,
        guard=GuardResult(Status.FAIL, False, (failed_target,), observation_complete=True),
        git=GitContext(False),
        python_resolved=Path("resolved-python"),
        sys_prefix="prefix",
        sys_base_prefix="base-prefix",
        python_version="3.13.5",
        pytest_version="9.1.1",
    )
    incomplete_expected = json.loads(
        (golden_dir / "schema-v2-fail-evidence-incomplete.json").read_text()
    )
    assert json.loads(render_json(incomplete_report)) == incomplete_expected
