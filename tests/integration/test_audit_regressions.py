"""Audit counterexamples run through the real pytest CLI (also against the wheel)."""
from pathlib import Path

import pytest

from tests.conftest import write_package, write_test
from tests.integration.test_cross_worktree import git


@pytest.mark.parametrize("reload_code", [False, True])
def test_redirected_link_only_changes_execution_on_reload(tmp_path, run_guard, reload_code):
    main = tmp_path / "main"
    feature = tmp_path / "feature"
    main.mkdir()
    write_package(main, "audit_pkg", "VALUE = 'main-wrong'\n")
    git(main, "init", "-b", "main")
    git(main, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "add", ".")
    git(main, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-m", "fixture")
    git(main, "worktree", "add", "-b", "feature", str(feature))
    (feature / "audit_pkg/__init__.py").write_text("VALUE = 'feature-correct'\n", encoding="utf-8")
    link = tmp_path / "active"
    try:
        link.symlink_to(feature, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable on this host")
    (feature / "conftest.py").write_text(
        f"import sys\nsys.path.insert(0, {str(link)!r})\n", encoding="utf-8")
    write_test(feature, f"""
import importlib
import sys
from pathlib import Path
def test_switch():
    sys.path.insert(0, {str(link)!r})
    import audit_pkg
    assert audit_pkg.VALUE == 'feature-correct'
    link = Path({str(link)!r})
    link.unlink()
    link.symlink_to({str(main)!r}, target_is_directory=True)
    if {reload_code!r}:
        importlib.invalidate_caches()
        assert importlib.reload(audit_pkg) is audit_pkg
        assert audit_pkg.VALUE == 'main-wrong'
    else:
        assert audit_pkg.VALUE == 'feature-correct'
""")
    result = run_guard(feature, "--expect", "audit_pkg=audit_pkg", "--", "-q")
    assert result.report["pytest"]["exit_code"] == 0, result.completed.stdout
    assert result.report["guard"]["status"] == ("fail" if reload_code else "pass")
    if reload_code:
        assert result.report["targets"][0]["reasons"] == ["MIXED_ORIGINS"]


@pytest.mark.parametrize("style", ["absolute", "relative", "builtin", "from"])
@pytest.mark.parametrize("warm", [False, True])
def test_transient_external_child_in_pytest_fixture(tmp_path, run_guard, style, warm):
    write_package(tmp_path, "audit_pkg")
    external = tmp_path / "external"
    external.mkdir()
    (external / "child.py").write_text("import math\nVALUE = 'external'\n", encoding="utf-8")
    statements = {
        "absolute": "child = importlib.import_module('audit_pkg.child')",
        "relative": "child = importlib.import_module('.child', 'audit_pkg')",
        "builtin": "child = __import__('audit_pkg.child', fromlist=['VALUE'])",
        "from": "from audit_pkg import child",
    }
    write_test(tmp_path, f"""
import importlib
import sys
import pytest
import audit_pkg
@pytest.fixture
def foreign():
    audit_pkg.__path__.append({str(external)!r})
    if {warm!r}:
        importlib.import_module('audit_pkg.child')
    {statements[style]}
    value = child.VALUE
    del sys.modules['audit_pkg.child']
    return value
def test_foreign(foreign):
    assert foreign == 'external'
""")
    result = run_guard(tmp_path, "--expect", "audit_pkg=audit_pkg", "--", "-q")
    assert result.report["pytest"]["exit_code"] == 0, result.completed.stdout
    assert result.report["guard"]["status"] == "fail"
    assert result.report["targets"][0]["reasons"] == ["MIXED_ORIGINS"]


@pytest.mark.parametrize("outside", [False, True])
@pytest.mark.parametrize("boundary", ["snapshot", "incremental"])
def test_observation_failure_cannot_pass(tmp_path, run_guard, outside, boundary):
    write_package(tmp_path, "audit_pkg")
    write_test(tmp_path, f"""
import audit_pkg
import pytest
from worktree_import_guard.observer import ImportObserver
def test_fault(monkeypatch):
    def broken(*args, **kwargs):
        raise OSError('controlled observation failure')
    monkeypatch.setattr(ImportObserver, '_record', broken)
    if {boundary!r} == 'incremental':
        __import__('audit_pkg')
    else:
        # Find the installed observer via the bound import wrapper closure.
        for cell in __import__('builtins').__import__.__closure__:
            if isinstance(cell.cell_contents, ImportObserver):
                cell.cell_contents.snapshot('fault-injection')
""")
    expected = "elsewhere" if outside else "audit_pkg"
    result = run_guard(tmp_path, "--expect", f"audit_pkg={expected}", "--", "-q")
    assert result.report["pytest"]["exit_code"] == 0, result.completed.stdout
    assert result.report["guard"]["status"] == ("fail" if outside else "unknown")
    assert result.report["guard"]["observation_complete"] is False
    assert result.report["guard"]["complete"] is False


@pytest.mark.parametrize("failure", ["before-execution", "partial-execution"])
def test_failed_reload_preserves_frozen_evidence(tmp_path, run_guard, failure):
    correct = tmp_path / "correct"
    outside = tmp_path / "outside"
    write_package(correct, "audit_pkg", "VALUE = 'correct'\n")
    write_package(outside, "audit_pkg", "VALUE = 'partial'\nraise RuntimeError('reload failed')\n")
    link = tmp_path / "active"
    try:
        link.symlink_to(correct, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable on this host")
    (tmp_path / "conftest.py").write_text(
        f"import sys\nsys.path.insert(0, {str(link)!r})\n", encoding="utf-8"
    )
    write_test(tmp_path, f"""
import importlib
import sys
from pathlib import Path
import pytest

def test_failed_reload():
    import audit_pkg
    assert audit_pkg.VALUE == 'correct'
    link = Path({str(link)!r})
    link.unlink()
    link.symlink_to({str(outside)!r}, target_is_directory=True)
    class BrokenFinder:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == 'audit_pkg':
                raise RuntimeError('reload failed')
    finder = BrokenFinder()
    if {failure!r} == 'before-execution':
        sys.meta_path.insert(0, finder)
    try:
        with pytest.raises(RuntimeError, match='reload failed'):
            importlib.reload(audit_pkg)
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
    assert audit_pkg.VALUE == ({failure!r} == 'partial-execution' and 'partial' or 'correct')
""")
    result = run_guard(tmp_path, "--expect", "audit_pkg=correct/audit_pkg", "--", "-q")
    assert result.report["pytest"]["exit_code"] == 0, result.completed.stdout
    assert result.completed.returncode == 2
    assert result.report["guard"]["status"] == "unknown"
    assert result.report["guard"]["complete"] is False
    assert result.report["guard"]["observation_complete"] is False
    target = result.report["targets"][0]
    assert target["reasons"] == ["ORIGIN_UNRESOLVED"]
    assert target["observations"]
    assert all(
        Path(item["canonical_origin"]).is_relative_to(correct.resolve())
        for item in target["observations"]
        if item["canonical_origin"] is not None
    )


@pytest.mark.parametrize("caught", [False, True])
@pytest.mark.parametrize("missing", ["module", "dependency"])
def test_missing_optional_import_is_not_observer_failure(tmp_path, run_guard, caught, missing):
    write_package(tmp_path, "audit_pkg")
    missing_name = "audit_pkg.optional"
    if missing == "dependency":
        missing_name = "_deliberately_missing_audit_dependency_827463"
        (tmp_path / "audit_pkg/optional.py").write_text(
            f"import {missing_name}\n", encoding="utf-8"
        )
    write_test(tmp_path, f"""
import importlib
import pytest

def test_optional():
    if {caught!r}:
        with pytest.raises(ModuleNotFoundError, match={missing_name!r}):
            importlib.import_module('audit_pkg.optional')
    else:
        importlib.import_module('audit_pkg.optional')
""")
    result = run_guard(
        tmp_path, "--expect", "audit_pkg.optional=audit_pkg/optional", "--", "-q"
    )
    assert result.report["pytest"]["exit_code"] == (0 if caught else 1)
    assert result.completed.returncode == (2 if caught else 1)
    assert result.report["guard"]["status"] == "unknown"
    assert result.report["guard"]["observation_complete"] is True
    assert "observation_errors" not in result.report["guard"]
    if missing == "module":
        assert result.report["targets"][0]["observations"] == []
