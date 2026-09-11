"""Early import observation using CPython audit events and module snapshots."""

from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Callable, Iterable
from importlib.util import resolve_name
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from weakref import ReferenceType, ref

from .matcher import module_matches
from .models import ObservedModule, PackageContract, ReasonCode
from .origins import freeze_path


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
        self._raw_keys: dict[str, set[tuple[object, ...]]] = {
            contract.package: set() for contract in contracts
        }
        self._module_instances: dict[tuple[str, str], ReferenceType[ModuleType]] = {}
        self._audit_names: dict[str, set[str]] = {contract.package: set() for contract in contracts}
        self._pending_names: set[str] = set()
        self._original_import: Callable[..., object] | None = None
        self._import_wrapper: Callable[..., object] | None = None
        self._original_import_module: Callable[[str, str | None], ModuleType] | None = None
        self._import_module_wrapper: Callable[[str, str | None], ModuleType] | None = None
        self._original_reload: Callable[[ModuleType], ModuleType] | None = None
        self._reload_wrapper: Callable[[ModuleType], ModuleType] | None = None
        self._active = False
        self._snapshotting = False
        self.import_returns = 0
        self.incremental_captures = 0
        self.full_snapshots = 0
        self.xdist = False
        self.unsupported_reason: ReasonCode | None = None
        self.observation_errors: list[str] = []

    def install(self) -> None:
        """Install instrumentation before pytest itself is imported."""

        if self._active:
            return
        self._active = True
        self._original_import = builtins.__import__
        self._original_import_module = importlib.import_module
        self._original_reload = importlib.reload
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
                self.import_returns += 1
                # A nested import may have drained the request before insertion.
                self._queue_import_request(name, globals, level)
                if fromlist:
                    for child in fromlist:
                        if isinstance(child, str) and child != "*":
                            self._queue_import_request(
                                f"{name}.{child}" if name else child, globals, level
                            )
                self._capture_pending("import-return", source="sys.modules")

        self._import_wrapper = observed_import
        builtins.__import__ = observed_import  # type: ignore[assignment]

        def observed_import_module(name: str, package: str | None = None) -> ModuleType:
            assert self._original_import_module is not None
            try:
                return self._original_import_module(name, package)
            finally:
                self.import_returns += 1
                self._queue_import_module_request(name, package)
                self._capture_pending("importlib-return", source="sys.modules")

        self._import_module_wrapper = observed_import_module
        importlib.import_module = observed_import_module

        def observed_reload(module: ModuleType) -> ModuleType:
            assert self._original_reload is not None
            module_name = self._static_module_name(module)
            if module_name is not None:
                self._queue_name(module_name, audited=True)
            try:
                result = self._original_reload(module)
            except BaseException:
                # A failed reload may have executed only part of the module, or
                # nothing at all. Do not reattribute the old frozen evidence.
                if module_name is not None and self._matching_contracts(module_name):
                    self.mark_unsupported(ReasonCode.ORIGIN_UNRESOLVED)
                raise
            else:
                # Reload can execute new code with the same object and raw path.
                # Only this execution boundary invalidates the frozen-path cache.
                if module_name is not None:
                    for contract in self._matching_contracts(module_name):
                        self._raw_keys[contract.package] = {
                            key for key in self._raw_keys[contract.package]
                            if key[0] != module_name
                        }
                    self._queue_name(module_name, audited=True)
                return result
            finally:
                self.import_returns += 1
                self._capture_pending("reload-return", source="sys.modules")

        self._reload_wrapper = observed_reload
        importlib.reload = observed_reload
        self.snapshot("observer-installed", source="sys.modules")

    def stop(self) -> None:
        """Restore the import function; audit hooks are permanent but become inert."""

        try:
            self.snapshot("observer-stopped", source="sys.modules")
        except Exception as error:
            # Cleanup must not replace an import or pytest failure already in flight.
            self._observation_failed("observer-stopped", error)
        finally:
            self._active = False
            if self._original_import is not None and builtins.__import__ is self._import_wrapper:
                builtins.__import__ = self._original_import  # type: ignore[assignment]
            if (
                self._original_import_module is not None
                and importlib.import_module is self._import_module_wrapper
            ):
                importlib.import_module = self._original_import_module  # type: ignore[assignment]
            if self._original_reload is not None and importlib.reload is self._reload_wrapper:
                importlib.reload = self._original_reload  # type: ignore[assignment]

    def mark_unsupported(self, reason: ReasonCode, *, xdist: bool = False) -> None:
        self.unsupported_reason = reason
        self.xdist = self.xdist or xdist

    def _observation_failed(self, phase: str, error: Exception) -> None:
        # Bounded, static context: do not call arbitrary exception __str__ hooks.
        if len(self.observation_errors) < 20:
            self.observation_errors.append(f"{phase}: {type(error).__name__}")

    def observations_for(self, package: str) -> tuple[ObservedModule, ...]:
        return tuple(self._observations[package])

    def was_audited(self, package: str) -> bool:
        return bool(self._audit_names[package])

    def metrics(self) -> dict[str, int]:
        """Return counters suitable for reproducible benchmark reports."""

        return {
            "import_returns": self.import_returns,
            "incremental_captures": self.incremental_captures,
            "full_snapshots": self.full_snapshots,
            "observations": sum(len(items) for items in self._observations.values()),
        }

    def _matching_contracts(self, module_name: str) -> tuple[PackageContract, ...]:
        return tuple(
            contract
            for contract in self._contracts
            if module_matches(module_name, contract.package)
        )

    @staticmethod
    def _static_dict(value: object) -> dict[str, object]:
        try:
            namespace = object.__getattribute__(value, "__dict__")
        except Exception:
            return {}
        return namespace if isinstance(namespace, dict) else {}

    def _static_module_name(self, module: object) -> str | None:
        name = self._static_dict(module).get("__name__")
        return name if isinstance(name, str) else None

    @staticmethod
    def _static_locations(value: object) -> tuple[str, ...]:
        value_type = type(value)
        supported = isinstance(value, list | tuple) or (
            value_type.__name__ == "_NamespacePath"
            and value_type.__module__ == "_frozen_importlib_external"
        )
        if not supported:
            return ()
        try:
            return tuple(
                location for location in cast(Iterable[object], value) if isinstance(location, str)
            )
        except Exception:
            return ()

    def _queue_name(self, module_name: str, *, audited: bool = False) -> None:
        for contract in self._matching_contracts(module_name):
            self._pending_names.add(module_name)
            if audited:
                self._audit_names[contract.package].add(module_name)

    def _queue_import_request(
        self,
        name: str,
        globals: dict[str, object] | None,
        level: int,
    ) -> None:
        try:
            if level:
                package = globals.get("__package__") if globals is not None else None
                if not isinstance(package, str) or not package:
                    return
                name = resolve_name(f"{'.' * level}{name}", package)
            self._queue_name(name)
        except Exception:
            return

    def _queue_import_module_request(self, name: str, package: str | None) -> None:
        try:
            if name.startswith("."):
                if package is None:
                    return
                name = resolve_name(name, package)
            self._queue_name(name)
        except Exception:
            return

    def _audit_hook(self, event: str, args: tuple[Any, ...]) -> None:
        if not self._active or event != "import" or not args:
            return
        try:
            module_name = args[0]
            if not isinstance(module_name, str):
                return
            self._queue_name(module_name, audited=True)
        except Exception:
            # Observation must never change the import being measured.
            return

    def snapshot(self, phase: str, *, source: str = "sys.modules") -> None:
        """Scan only entries relevant to the small explicit target set."""

        if not self._active or self._snapshotting:
            return
        self._snapshotting = True
        try:
            self.full_snapshots += 1
            modules = tuple(sys.modules.items())
            for module_name, module in modules:
                if module is None:
                    continue
                for contract in self._matching_contracts(module_name):
                    self._record(contract.package, module_name, module, phase, source)
        except Exception as error:
            # Lifecycle instrumentation must remain observational.
            self._observation_failed(phase, error)
        finally:
            self._snapshotting = False

    def _capture_pending(self, phase: str, *, source: str) -> None:
        """Record only target names made relevant by this import boundary."""

        if not self._active or self._snapshotting or not self._pending_names:
            return
        self._snapshotting = True
        try:
            self.incremental_captures += 1
            pending = tuple(self._pending_names)
            self._pending_names.clear()
            for module_name in pending:
                module = sys.modules.get(module_name)
                if module is None:
                    continue
                for contract in self._matching_contracts(module_name):
                    self._record(contract.package, module_name, module, phase, source)
        except Exception as error:
            # A finally-boundary observer must not replace the import's own result/error.
            self._observation_failed(phase, error)
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
            module_dict = self._static_dict(module)
            spec = module_dict.get("__spec__")
            spec_dict = self._static_dict(spec) if spec is not None else {}
            spec_origin_value = spec_dict.get("origin")
            file_value = module_dict.get("__file__")
            locations_value = spec_dict.get("submodule_search_locations")
            spec_origin = spec_origin_value if isinstance(spec_origin_value, str) else None
            file = file_value if isinstance(file_value, str) else None
            locations = self._static_locations(locations_value)
        except Exception:
            spec_origin = None
            file = None
            locations = ()
        raw_key: tuple[object, ...] = (module_name, id(module), spec_origin, file, locations)
        instance_key = (package, module_name)
        previous_instance = self._module_instances.get(instance_key)
        if previous_instance is None or previous_instance() is not module:
            # Integer IDs can be reused after an unloaded module is collected.
            # Only the same live instance may reuse frozen raw-path evidence.
            self._raw_keys[package] = {
                key for key in self._raw_keys[package] if key[0] != module_name
            }
            self._module_instances[instance_key] = ref(module)
        if raw_key in self._raw_keys[package]:
            return
        self._raw_keys[package].add(raw_key)
        try:
            capture_cwd = Path.cwd()
        except OSError:
            capture_cwd = Path(".")
        canonical_spec_origin = freeze_path(spec_origin, cwd=capture_cwd)
        canonical_file = freeze_path(file, cwd=capture_cwd)
        canonical_locations = tuple(
            frozen
            for location in locations
            if (frozen := freeze_path(location, cwd=capture_cwd)) is not None
        )
        key: tuple[object, ...] = (
            module_name,
            spec_origin,
            file,
            locations,
            canonical_spec_origin,
            canonical_file,
            canonical_locations,
        )
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
                capture_cwd=str(capture_cwd),
                canonical_spec_origin=canonical_spec_origin,
                canonical_file=canonical_file,
                canonical_search_locations=canonical_locations,
                paths_frozen=True,
            )
        )

