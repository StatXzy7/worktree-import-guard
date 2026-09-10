"""Small, declarative package contracts confined to the current project/worktree."""

from __future__ import annotations

import json
import os
from pathlib import Path, PureWindowsPath

from .contracts import ContractError, parse_contracts
from .models import PackageContract

CONFIG_NAME = ".wt-import.json"


def project_boundary(directory: Path) -> Path:
    """Find a Git boundary without invoking Git or searching outside it for config."""
    directory = directory.resolve()
    for parent in (directory, *directory.parents):
        if (parent / ".git").exists():
            return parent
    return directory


def find_config(directory: Path) -> Path | None:
    directory = directory.resolve()
    boundary = project_boundary(directory)
    while True:
        candidate = directory / CONFIG_NAME
        if candidate.exists() or candidate.is_symlink():
            if candidate.is_symlink():
                raise ContractError(f"refusing symlink configuration: {candidate}")
            return candidate
        if directory == boundary:
            return None
        directory = directory.parent


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate configuration key: {key}")
        result[key] = value
    return result


def validate_config(data: object, directory: Path) -> tuple[PackageContract, ...]:
    if not isinstance(data, dict) or set(data) != {"schema_version", "expect"}:
        raise ContractError("configuration must contain only schema_version and expect")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ContractError("configuration schema_version must be 1")
    expectations = data["expect"]
    if not isinstance(expectations, dict) or not expectations:
        raise ContractError("configuration expect must be a nonempty package-to-directory object")
    values: list[str] = []
    boundary = project_boundary(directory)
    for package, value in expectations.items():
        if not isinstance(package, str) or not isinstance(value, str) or not value:
            raise ContractError("configuration package names and paths must be nonempty strings")
        if Path(value).is_absolute() or PureWindowsPath(value).drive or value.startswith("~"):
            raise ContractError("configuration paths must be relative to the configuration file")
        if not (directory / value).resolve().is_relative_to(boundary):
            raise ContractError(f"configuration path leaves this project/worktree: {value}")
        values.append(f"{package}={value}")
    return parse_contracts(values, directory)


def load_config(path: Path) -> tuple[PackageContract, ...]:
    try:
        if path.is_symlink():
            raise ContractError(f"refusing symlink configuration: {path}")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        return validate_config(data, path.parent.resolve())
    except (OSError, ValueError, RuntimeError) as error:
        raise ContractError(f"could not read {path}: {error}") from error


def config_data(contracts: tuple[PackageContract, ...], directory: Path) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": 1,
        "expect": {
            c.package: Path(os.path.relpath(c.expected_root, directory)).as_posix()
            for c in contracts
        },
    }
    validate_config(data, directory)
    return data


def save_config(directory: Path, data: dict[str, object]) -> Path:
    """Exclusively create a confirmed file; never follow or replace an existing link/file."""
    validate_config(data, directory)
    path = directory / CONFIG_NAME
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise ContractError(
            f"could not create {path}; existing files are never overwritten: {error}"
        ) from error
    return path
