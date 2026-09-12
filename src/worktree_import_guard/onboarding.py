"""Three explicit decisions for first use; discovery never imports project code."""

from __future__ import annotations

import json
import shlex
import sys
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path

from .contracts import ContractError, parse_contracts
from .environment_probe import choose_default_candidate, probe_candidates
from .launcher import command_for_path, console_script
from .models import PackageContract
from .project_config import CONFIG_NAME, config_data, find_config, load_config, save_config

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


def _bound_next_check_command(extra_argument: str) -> str:
    try:
        script = console_script(distribution("worktree-import-guard"))
    except Exception:
        command = _python_command(
            Path(sys.executable),
            "-m",
            "worktree_import_guard.cli",
            extra_argument,
        )
        return f"Next time: {command}"
    return f"Next time: {command_for_path(script, [extra_argument])}"


def _bound_next_doctor_command() -> str:
    return _bound_next_check_command("-- -q")


def _environment_banner(directory: Path) -> None:
    print(f"Project: {directory}")
    candidates = [*probe_candidates(directory)]
    if not candidates:
        print(
            "No direct interpreter candidates were detected. "
            "Please provide an interpreter command and rerun this command there."
        )
        return

    print("Detected interpreter candidates:")
    for index, candidate in enumerate(candidates, 1):
        status = []
        if candidate.get("pytest_available"):
            status.append("pytest:ok")
        else:
            status.append("pytest:unavailable")
        if candidate.get("detector_installed"):
            compat = "compatible" if candidate.get("detector_compatible") else "incompatible"
            status.append(f"worktree-import-guard:{compat}")
        else:
            status.append("worktree-import-guard:not-installed")
        error = candidate.get("error")
        line = (
            f"{index:>2}. {candidate['label']}: python={candidate['python']} "
            f"python_version={candidate['python_version']} status=[{', '.join(status)}]"
        )
        if error:
            line += f" error={error}"
        print(line)

    alt_envs = [item for item in candidates if item["label"] != "current interpreter"]
    if alt_envs:
        print("If one of these is your real test environment, verify installation there first:")
        print("  {python} -m pip show worktree-import-guard".format(python=alt_envs[0]["python"]))
        print("Then continue with the README installation in that environment.")

    recommended, ambiguous = choose_default_candidate(candidates)
    if recommended is not None:
        print(
            "Most likely test environment (inference, not automatic selection): "
            f"{recommended['label']}"
        )
        print("Copy-paste command for this project:")
        print(f"  {recommended['command_setup']}")
        if ambiguous:
            print("Evidence is not conclusive; confirm interpreter before continuing.")
    else:
        print(
            "No candidate has both pytest>=8.2 and a compatible installed detector. "
            "Please install the tool in the existing test environment first."
        )


def _require_pytest() -> None:
    if not pytest_available():
        raise ContractError(
            "this environment needs pytest >=8.2,<10; use your existing test environment"
        )


def doctor(directory: Path) -> tuple[PackageContract, ...] | None:
    """Reuse saved settings for repeat checks, or run first-time setup when none exist."""

    if not sys.stdin.isatty():
        print(
            "The guided check confirms this is the project and Python environment "
            "used by your tests."
        )
        raise ContractError(
            "--doctor needs an interactive terminal; use wt-import -- -q, "
            "or --expect PACKAGE=PATH in CI"
        )
    config_path = find_config(directory)
    if config_path is None:
        return setup(directory)
    try:
        contracts = load_config(config_path)
    except ContractError as error:
        print(f"Configuration file: {config_path}")
        raise ContractError(f"saved settings cannot be used: {error}") from error
    _require_pytest()
    print(f"Configuration file: {config_path}")
    for contract in contracts:
        print(f"  {contract.package} = {contract.declared_path}")
    print("This reuses saved settings; it does not overwrite your configuration.")
    print("Then run pytest in this project. Your tests may have side effects.")
    try:
        if input("Run the check now with these settings? [y/N] ").lower() not in {"y", "yes"}:
            print("Check cancelled; tests were not started.")
            return None
    except (EOFError, KeyboardInterrupt):
        print("Check cancelled; tests were not started.")
        return None
    print(_bound_next_doctor_command())
    return contracts


def setup(directory: Path) -> tuple[PackageContract, ...] | None:
    if not sys.stdin.isatty():
        print(
            "The guided check confirms this is the project and Python environment "
            "used by your tests."
        )
        raise ContractError(
            "--setup needs an interactive terminal; use --expect PACKAGE=PATH in CI"
        )
    _environment_banner(directory)
    _require_pytest()
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
        try:
            if input("3/3 Save these settings and run tests now? [y/N] ").lower() not in {
                "y",
                "yes",
            }:
                return None
        except (EOFError, KeyboardInterrupt):
            print("Setup cancelled; tests were not started.")
            return None
        save_config(directory, data)
        print(_bound_next_check_command("-- -q"))
        return contracts
    except (EOFError, KeyboardInterrupt):
        print("Setup cancelled; tests were not started.")
        return None
    except (OSError, RuntimeError) as error:
        raise ContractError(f"could not inspect project directories: {error}") from error
