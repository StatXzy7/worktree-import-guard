"""Parsing and validation for explicit PACKAGE=PATH contracts."""

from __future__ import annotations

import keyword
from pathlib import Path

from .models import PackageContract
from .origins import canonicalize_path


class ContractError(ValueError):
    """A user-facing contract validation error."""


def _valid_package(package: str) -> bool:
    parts = package.split(".")
    return bool(package) and all(
        part.isidentifier() and not keyword.iskeyword(part) for part in parts
    )


def parse_contract(value: str, cwd: Path) -> PackageContract:
    """Parse and canonicalize one PACKAGE=PATH value."""

    if "=" not in value:
        raise ContractError(f"malformed expectation {value!r}; expected PACKAGE=PATH")
    package, declared_path = value.split("=", 1)
    if not _valid_package(package):
        raise ContractError(f"invalid package prefix {package!r} in expectation {value!r}")
    if not declared_path:
        raise ContractError(f"empty path in expectation {value!r}")
    return PackageContract(
        package=package,
        declared_path=declared_path,
        expected_root=canonicalize_path(declared_path, base=cwd),
    )


def parse_contracts(values: list[str], cwd: Path) -> tuple[PackageContract, ...]:
    """Parse contracts while rejecting duplicate package declarations."""

    contracts: list[PackageContract] = []
    seen: set[str] = set()
    for value in values:
        contract = parse_contract(value, cwd)
        if contract.package in seen:
            raise ContractError(f"duplicate expectation for package {contract.package!r}")
        seen.add(contract.package)
        contracts.append(contract)
    return tuple(contracts)
