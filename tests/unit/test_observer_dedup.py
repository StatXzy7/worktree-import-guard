from __future__ import annotations

import sys
import weakref
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

import worktree_import_guard.observer as observer_module
from worktree_import_guard.models import GitContext, PackageContract, ReasonCode, Status
from worktree_import_guard.observer import ImportObserver
from worktree_import_guard.report import classify


def test_cached_target_metadata_is_frozen_once_but_changes_are_retained(tmp_path: Path) -> None:
    package = "_wtig_dedup_target"
    contract = PackageContract(package, package, tmp_path / package)
    module = ModuleType(package)
    first = str(tmp_path / package / "__init__.py")
    second = str(tmp_path / "other" / "__init__.py")
    module.__file__ = first
    module.__spec__ = ModuleSpec(package, loader=None, origin=first)
    sys.modules[package] = module
    observer = ImportObserver((contract,))
    try:
        observer.install()
        for _ in range(100):
            __import__(package)
        assert len(observer.observations_for(package)) == 1

        module.__file__ = second
        assert module.__spec__ is not None
        module.__spec__.origin = second
        __import__(package)
        assert len(observer.observations_for(package)) == 2
    finally:
        observer.stop()
        sys.modules.pop(package, None)


def test_reused_module_id_does_not_reuse_frozen_origin(monkeypatch, tmp_path: Path) -> None:
    package = "_wtig_reused_identity"
    expected = tmp_path / "expected"
    outside = tmp_path / "outside"
    expected.mkdir()
    outside.mkdir()
    contracts = (PackageContract(package, package, expected),)
    observer = ImportObserver(contracts)
    # Deterministically model CPython assigning a collected module's ID to its replacement.
    monkeypatch.setattr(observer_module, "id", lambda value: 123, raising=False)

    def record_module() -> weakref.ReferenceType[ModuleType]:
        module = ModuleType(package)
        module.__file__ = "module.py"
        module.__spec__ = ModuleSpec(package, loader=None, origin=module.__file__)
        observer._record(package, package, module, "import-return", "sys.modules")
        return weakref.ref(module)

    monkeypatch.chdir(expected)
    previous = record_module()
    assert previous() is None, "Observation must not retain unloaded user modules"
    monkeypatch.chdir(outside)
    record_module()
    observations = observer.observations_for(package)
    assert len(observations) == 2
    assert Path(observations[0].canonical_file).parent == expected
    assert Path(observations[1].canonical_file).parent == outside
    result = classify(contracts, observer, GitContext(available=False))
    assert result.status is Status.FAIL
    assert result.targets[0].reasons == (ReasonCode.MIXED_ORIGINS,)
