"""Early import observation using CPython audit events and module snapshots."""

from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Callable
from types import ModuleType
from typing import Any

from .matcher import module_matches
from .models import ObservedModule, PackageContract, ReasonCode


class ImportObserver:
    """Retain target module metadata across imports and lifecycle snapshots."""

    def __init__(self, contracts: tuple[PackageContract, ...]) -> None:
        self._contracts = contracts
        self._observations: dict[str, list[ObservedModule]] = {
            contract.package: [] for contract in contracts
        }
        self._keys: dict[str, set[tuple[object, ...]]] = {
            contract.package: set() for contract in contracts
        }
        self._audit_names: dict[str, set[str]] = {contract.package: set() for contract in contracts}
        self._original_import: Callable[..., object] | None = None
        self._import_wrapper: Callable[..., object] | None = None
        self._original_import_module: Callable[[str, str | None], ModuleType] | None = None
        self._import_module_wrapper: Callable[[str, str | None], ModuleType] | None = None
        self._active = False
        self._snapshotting = False
        self.xdist = False
        self.unsupported_reason: ReasonCode | None = None

    def install(self) -> None:
        """Install instrumentation before pytest itself is imported."""

        if self._active:
            return
        self._active = True
        self._original_import = builtins.__import__
        self._original_import_module = importlib.import_module
        sys.addaudithook(self._audit_hook)

        def observed_import(
            name: str,
            globals: dict[str, object] | None = None,
            locals: dict[str, object] | None = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> object:
            assert self._original_import is not None
            try:
                return self._original_import(name, globals, locals, fromlist, level)
            finally:
                self.snapshot("import-return", source="sys.modules")

        self._import_wrapper = observed_import
        builtins.__import__ = observed_import  # type: ignore[assignment]

        def observed_import_module(name: str, package: str | None = None) -> ModuleType:
            assert self._original_import_module is not None
            try:
                return self._original_import_module(name, package)
            finally:
                self.snapshot("importlib-return", source="sys.modules")

        self._import_module_wrapper = observed_import_module
        importlib.import_module = observed_import_module
        self.snapshot("observer-installed", source="sys.modules")

    def stop(self) -> None:
        """Restore the import function; audit hooks are permanent but become inert."""

        self.snapshot("observer-stopped", source="sys.modules")
        self._active = False
        if self._original_import is not None and builtins.__import__ is self._import_wrapper:
            builtins.__import__ = self._original_import  # type: ignore[assignment]
        if (
            self._original_import_module is not None
            and importlib.import_module is self._import_module_wrapper
        ):
            importlib.import_module = self._original_import_module  # type: ignore[assignment]

    def mark_unsupported(self, reason: ReasonCode, *, xdist: bool = False) -> None:
        self.unsupported_reason = reason
        self.xdist = self.xdist or xdist

    def observations_for(self, package: str) -> tuple[ObservedModule, ...]:
        return tuple(self._observations[package])

    def was_audited(self, package: str) -> bool:
        return bool(self._audit_names[package])

    def _matching_contracts(self, module_name: str) -> tuple[PackageContract, ...]:
        return tuple(
            contract
            for contract in self._contracts
            if module_matches(module_name, contract.package)
        )

    def _audit_hook(self, event: str, args: tuple[Any, ...]) -> None:
        if not self._active or event != "import" or not args:
            return
        try:
            module_name = args[0]
            if not isinstance(module_name, str):
                return
            for contract in self._matching_contracts(module_name):
                self._audit_names[contract.package].add(module_name)
        except Exception:
            # Observation must never change the import being measured.
            return

    def snapshot(self, phase: str, *, source: str = "sys.modules") -> None:
        """Scan only entries relevant to the small explicit target set."""

        if not self._active or self._snapshotting:
            return
        self._snapshotting = True
        try:
            modules = sorted(sys.modules.items())
            for module_name, module in modules:
                if module is None:
                    continue
                for contract in self._matching_contracts(module_name):
                    self._record(contract.package, module_name, module, phase, source)
        finally:
            self._snapshotting = False

    def _record(
        self,
        package: str,
        module_name: str,
        module: ModuleType,
        phase: str,
        source: str,
    ) -> None:
        try:
            spec = getattr(module, "__spec__", None)
            spec_origin_value = getattr(spec, "origin", None)
            file_value = getattr(module, "__file__", None)
            locations_value = getattr(spec, "submodule_search_locations", None)
            spec_origin = str(spec_origin_value) if spec_origin_value is not None else None
            file = str(file_value) if file_value is not None else None
            locations = (
                tuple(str(location) for location in locations_value)
                if locations_value is not None
                else ()
            )
        except Exception:
            spec_origin = None
            file = None
            locations = ()
        key: tuple[object, ...] = (module_name, spec_origin, file, locations)
        if key in self._keys[package]:
            return
        self._keys[package].add(key)
        self._observations[package].append(
            ObservedModule(
                module=module_name,
                spec_origin=spec_origin,
                file=file,
                search_locations=locations,
                phase=phase,
                source=source,
            )
        )
