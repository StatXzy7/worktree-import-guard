from __future__ import annotations

import builtins
import importlib
import importlib.util
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

import pytest

from worktree_import_guard.models import PackageContract, ReasonCode
from worktree_import_guard.observer import ImportObserver
from worktree_import_guard.pytest_plugin import GuardPytestPlugin


def make_observer(tmp_path: Path, package: str = "_wtig_target") -> ImportObserver:
    contract = PackageContract(package, package, tmp_path / package)
    return ImportObserver((contract,))


def test_observer_snapshots_loaded_module_and_restores_import(tmp_path: Path) -> None:
    module = ModuleType("_wtig_target")
    module.__file__ = str(tmp_path / "_wtig_target/__init__.py")
    module.__spec__ = ModuleSpec("_wtig_target", loader=None, origin=module.__file__)
    sys.modules[module.__name__] = module
    original_import = builtins.__import__
    original_import_module = importlib.import_module
    original_reload = importlib.reload
    observer = make_observer(tmp_path)
    try:
        observer.install()
        observer.install()
        assert observer.observations_for("_wtig_target")[0].module == "_wtig_target"
        assert builtins.__import__ is not original_import
        observer.mark_unsupported(ReasonCode.UNSUPPORTED_RUNTIME)
        assert observer.unsupported_reason is ReasonCode.UNSUPPORTED_RUNTIME
    finally:
        observer.stop()
        sys.modules.pop(module.__name__, None)
    assert builtins.__import__ is original_import
    assert importlib.import_module is original_import_module
    assert importlib.reload is original_reload


def test_cached_unrelated_imports_do_not_scan_module_table(tmp_path: Path) -> None:
    observer = make_observer(tmp_path)
    observer.install()
    try:
        initial_snapshots = observer.full_snapshots
        for _ in range(1_000):
            __import__("math")
        assert observer.import_returns >= 1_000
        assert observer.full_snapshots == initial_snapshots
        assert observer.incremental_captures == 0
    finally:
        observer.stop()


def test_metadata_capture_does_not_call_module_getattr(tmp_path: Path) -> None:
    calls: list[str] = []

    class DynamicModule(ModuleType):
        def __getattr__(self, name: str) -> object:
            calls.append(name)
            raise RuntimeError("dynamic metadata access")

    module = DynamicModule("_wtig_target")
    sys.modules[module.__name__] = module
    observer = make_observer(tmp_path)
    try:
        observer.install()
        observer.stop()
    finally:
        sys.modules.pop(module.__name__, None)
    assert calls == []


def test_import_error_and_existing_hook_are_preserved(monkeypatch, tmp_path: Path) -> None:
    original = builtins.__import__

    def existing_hook(*args, **kwargs):
        if args and args[0] == "_wtig_target":
            raise LookupError("original import failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", existing_hook)
    observer = make_observer(tmp_path)
    observer.install()
    try:
        with pytest.raises(LookupError, match="original import failure"):
            __import__("_wtig_target")
        assert observer.was_audited("_wtig_target") is False
    finally:
        observer.stop()
    assert builtins.__import__ is existing_hook


def test_lazy_module_metadata_is_observed_without_execution(tmp_path: Path) -> None:
    module_path = tmp_path / "_wtig_target.py"
    marker = tmp_path / "executed"
    module_path.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("_wtig_target", module_path)
    assert spec is not None and spec.loader is not None
    lazy_loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = lazy_loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module.__name__] = module
    lazy_loader.exec_module(module)

    observer = make_observer(tmp_path)
    try:
        observer.install()
        assert observer.observations_for("_wtig_target")
        assert not marker.exists()
    finally:
        observer.stop()
        sys.modules.pop(module.__name__, None)


def test_stop_restores_hooks_even_if_final_snapshot_breaks(monkeypatch, tmp_path: Path) -> None:
    original_import = builtins.__import__
    original_import_module = importlib.import_module
    original_reload = importlib.reload
    observer = make_observer(tmp_path)
    observer.install()

    def broken_snapshot(*args, **kwargs) -> None:
        del args, kwargs
        raise RuntimeError("observer failure")

    monkeypatch.setattr(observer, "snapshot", broken_snapshot)
    observer.stop()
    assert builtins.__import__ is original_import
    assert importlib.import_module is original_import_module
    assert importlib.reload is original_reload


def test_relative_importlib_and_reload_boundaries_are_observed(
    monkeypatch, tmp_path: Path
) -> None:
    package = tmp_path / "_wtig_target"
    package.mkdir()
    (package / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "child.py").write_text("VALUE = 2\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    observer = make_observer(tmp_path)
    try:
        observer.install()
        child = importlib.import_module(".child", "_wtig_target")
        before_reload = observer.import_returns
        assert importlib.reload(child) is child
        assert observer.import_returns > before_reload
        assert "_wtig_target.child" in {
            item.module for item in observer.observations_for("_wtig_target")
        }
        observer.snapshot("test-lifecycle-fallback")
        assert {item.module for item in observer.observations_for("_wtig_target")} == {
            "_wtig_target",
            "_wtig_target.child",
        }
    finally:
        observer.stop()
        sys.modules.pop("_wtig_target.child", None)
        sys.modules.pop("_wtig_target", None)


def test_audit_prefix_is_exact(tmp_path: Path) -> None:
    observer = make_observer(tmp_path)
    observer.install()
    try:
        observer._audit_hook("import", ("_wtig_target_other",))
        assert not observer.was_audited("_wtig_target")
        observer._audit_hook("import", ("_wtig_target.core",))
        assert observer.was_audited("_wtig_target")
        observer._audit_hook("other", ("_wtig_target",))
        observer._audit_hook("import", (object(),))
    finally:
        observer.stop()


def test_importlib_boundary_retains_a_transient_module(monkeypatch, tmp_path: Path) -> None:
    module = ModuleType("_wtig_target")
    module.__file__ = str(tmp_path / "_wtig_target/__init__.py")
    module.__spec__ = ModuleSpec("_wtig_target", loader=None, origin=module.__file__)

    def fake_import_module(name: str, package: str | None = None) -> ModuleType:
        del package
        assert name == module.__name__
        sys.modules[name] = module
        return module

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    observer = make_observer(tmp_path)
    observer.install()
    try:
        assert importlib.import_module(module.__name__) is module
        sys.modules.pop(module.__name__)
        retained = observer.observations_for(module.__name__)
        assert retained[0].phase == "importlib-return"
    finally:
        observer.stop()


class FakeConfig:
    def __init__(self, numprocesses=None) -> None:
        self.numprocesses = numprocesses

    def getoption(self, name: str, default=None):
        assert name == "numprocesses"
        return self.numprocesses if self.numprocesses is not None else default


def test_plugin_lifecycle_and_xdist_rejection(tmp_path: Path) -> None:
    observer = make_observer(tmp_path)
    observer.install()
    plugin = GuardPytestPlugin(observer)
    try:
        plugin.pytest_configure(FakeConfig())
        plugin.pytest_sessionstart(object())
        plugin.pytest_collection_finish(object())
        plugin.pytest_sessionfinish(object(), 0)
        assert plugin.collection_seconds is not None
        with pytest.raises(pytest.UsageError, match="xdist"):
            plugin.pytest_configure(FakeConfig(2))
        assert observer.xdist
    finally:
        observer.stop()
