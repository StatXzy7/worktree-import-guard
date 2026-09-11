"""Three explicit decisions for first use; discovery never imports project code."""

from __future__ import annotations

import json
import shlex
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .contracts import ContractError, parse_contracts
from .models import PackageContract
from .project_config import CONFIG_NAME, config_data, save_config

_EXCLUDED = {
    "tests",
    "test",
    "docs",
    "examples",
    "build",
    "dist",
    "venv",
    "env",
    "site-packages",
    "__pycache__",
    "node_modules",
    "benchmarks",
}


def candidates(directory: Path) -> tuple[PackageContract, ...]:
    results: list[PackageContract] = []
    for base in (directory / "src", directory):
        if (
            not base.is_dir()
            or base.is_symlink()
            or not base.resolve().is_relative_to(directory.resolve())
        ):
            continue
        for path in sorted(base.iterdir()):
            if (
                path.name.startswith((".", "_"))
                or path.name in _EXCLUDED
                or path.is_symlink()
                or not path.is_dir()
                or not path.resolve().is_relative_to(directory.resolve())
            ):
                continue
            if not (path / "__init__.py").is_file() or (path / "__init__.py").is_symlink():
                continue
            try:
                results.extend(
                    parse_contracts([f"{path.name}={path.relative_to(directory)}"], directory)
                )
            except ContractError:
                continue
    return tuple(results)


def pytest_available() -> bool:
    try:
        parts = version("pytest").split(".")
        return (8, 2) <= (int(parts[0]), int(parts[1])) < (10, 0)
    except (PackageNotFoundError, ValueError, IndexError):
        return False


def _python_command(python: Path, *args: str) -> str:
    words = [str(python), *args]
    if sys.platform == "win32":
        return "& " + " ".join("'" + word.replace("'", "''") + "'" for word in words)
    return shlex.join(words)


def setup(directory: Path) -> tuple[PackageContract, ...] | None:
    if not sys.stdin.isatty():
        print("The guided check confirms this is the project and Python environment used by your tests.")
        raise ContractError(
            "--setup needs an interactive terminal; use --expect PACKAGE=PATH in CI"
        )
    print(f"Project: {directory}\nPython: {sys.executable}\nEnvironment: {sys.prefix}")
    print("This checks that pytest imports the code you just edited, in this Python environment.")
    print("It diagnoses the source location; it does not install, activate, or repair anything.")
    venv_python = (
        directory / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    if (
        venv_python.is_file()
        and Path(sys.prefix).absolute() != venv_python.parent.parent.absolute()
    ):
        print(f"Possible project environment (not selected automatically): {venv_python}")
        print("If that is your test environment, cancel here. Check whether guard is installed:")
        print(_python_command(venv_python, "-m", "pip", "show", "worktree-import-guard"))
        print(
            "If missing, follow the README installation command using that Python. "
            "Then restart setup there:"
        )
        print(_python_command(venv_python, "-m", "worktree_import_guard.cli", "--setup"))
    if not pytest_available():
        raise ContractError(
            "this environment needs pytest >=8.2,<10; use your existing test environment"
        )
    if (directory / CONFIG_NAME).exists() or (directory / CONFIG_NAME).is_symlink():
        raise ContractError(
            f"{CONFIG_NAME} already exists; inspect it before changing your contract"
        )
    try:
        if input(
            "1/3 Is this the project and Python environment used by your tests? [y/N] "
        ).lower() not in {"y", "yes"}:
            return None
        choices = candidates(directory)
        if not choices:
            print(
                "No unambiguous src/flat packages found. Enter an explicit import name=directory."
            )
        for index, contract in enumerate(choices, 1):
            print(f"  {index}: {contract.package} = {contract.declared_path}")
        print("Suggestions are directories, not verified import sources.")
        selection = input(
            "2/3 Choose package number(s), comma separated; or enter PACKAGE=PATH "
            "(separate multiple mappings with ;): "
        ).strip()
        if "=" in selection:
            contracts = parse_contracts([v.strip() for v in selection.split(";")], directory)
        else:
            try:
                indices = [int(value.strip()) for value in selection.split(",")]
                if not indices or any(i < 1 or i > len(choices) for i in indices):
                    raise ValueError
                contracts = parse_contracts(
                    [f"{choices[i - 1].package}={choices[i - 1].declared_path}" for i in indices],
                    directory,
                )
            except (ValueError, IndexError) as error:
                raise ContractError(
                    "choose listed package numbers or explicit PACKAGE=PATH mappings"
                ) from error
        data = config_data(contracts, directory)
        if any(not contract.expected_root.is_dir() for contract in contracts):
            raise ContractError("choose existing source package directories before saving settings")
        print(f"Save {directory / CONFIG_NAME}:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        print("Then run pytest in this project. Your tests may have side effects.")
        if input("3/3 Save these settings and run tests now? [y/N] ").lower() not in {"y", "yes"}:
            return None
        save_config(directory, data)
        print("Saved. Next time: wt-import -- -q")
        return contracts
    except (EOFError, KeyboardInterrupt):
        print("Setup cancelled; tests were not started.")
        return None
    except (OSError, RuntimeError) as error:
        raise ContractError(f"could not inspect project directories: {error}") from error
