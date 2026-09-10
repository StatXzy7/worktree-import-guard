from __future__ import annotations

import json
from pathlib import Path

from worktree_import_guard.cli import composite_exit_code
from worktree_import_guard.models import (
    GitContext,
    ObservedModule,
    PackageContract,
    RunReport,
    Status,
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
    assert data["schema_version"] == 1
    assert data["scope"] == {
        "process": "current-pytest-process",
        "xdist": False,
        "child_process_imports": False,
    }
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
