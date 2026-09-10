from __future__ import annotations

import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType

from worktree_import_guard.models import PackageContract
from worktree_import_guard.observer import ImportObserver


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
