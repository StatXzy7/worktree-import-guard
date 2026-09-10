from __future__ import annotations

import builtins
import importlib
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
    observer = make_observer(tmp_path)
    try:
        observer.install()
        assert observer.observations_for("_wtig_target")[0].module == "_wtig_target"
        assert builtins.__import__ is not original_import
        observer.mark_unsupported(ReasonCode.UNSUPPORTED_RUNTIME)
        assert observer.unsupported_reason is ReasonCode.UNSUPPORTED_RUNTIME
    finally:
        observer.stop()
        sys.modules.pop(module.__name__, None)
    assert builtins.__import__ is original_import


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
        plugin.pytest_collection_finish(object())
        plugin.pytest_runtest_setup(object())
        plugin.pytest_runtest_call(object())
        plugin.pytest_runtest_teardown(object(), object())
        plugin.pytest_sessionfinish(object(), 0)
        with pytest.raises(pytest.UsageError, match="xdist"):
            plugin.pytest_configure(FakeConfig(2))
        assert observer.xdist
    finally:
        observer.stop()
