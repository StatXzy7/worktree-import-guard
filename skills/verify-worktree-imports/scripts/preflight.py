"""Read-only probe of the selected project Python and its installation."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path


def _problem(code: str, message: str, next_step: str) -> dict[str, str]:
    return {"code": code, "message": message, "next_step": next_step}


def _next_step(status: str, problems: list[dict[str, str]]) -> str:
    if problems:
        return problems[0]["next_step"]
    if status == "ready":
        return "Run guarded pytest with the saved targets, for example wt-import -- -q."
    if status == "needs_selection":
        return (
            "Confirm import-name to package-directory mappings, then save settings with "
            "--setup or provide --expect for a one-off check."
        )
    return "Resolve the reported preparation conditions before running guarded pytest."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", type=Path, required=True)
    cwd = parser.parse_args().cwd
    raw_cwd = cwd.expanduser()
    out: dict[str, object] = {
        "status": "missing_conditions",
        "conditions": {"cwd_accessible": raw_cwd.is_dir()},
        "problems": [],
        "problem_details": [],
        "cwd": str(raw_cwd),
        "python": sys.executable,
        "python_resolved": str(Path(sys.executable).resolve()),
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "python_version": platform.python_version(),
        "config_path": None,
        "targets": [],
    }
    problems: list[dict[str, str]] = []
    if not raw_cwd.is_dir():
        problems.append(
            _problem(
                "PROJECT_NOT_ACCESSIBLE",
                "project directory is not accessible",
                "Choose an existing project directory that this interpreter can read.",
            )
        )
        out["problems"] = [item["message"] for item in problems]
        out["problem_details"] = problems
        out["next_step"] = _next_step("missing_conditions", problems)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    resolved_cwd = raw_cwd.resolve()
    out["cwd"] = str(resolved_cwd)
    out["conditions"] = {"cwd_accessible": True}

    try:
        from run_check import console_script

        from worktree_import_guard.compatibility import distribution_compatible
        from worktree_import_guard.onboarding import pytest_available
        from worktree_import_guard.project_config import find_config, load_config
    except ImportError:
        problems.append(
            _problem(
                "DETECTOR_MISSING",
                "worktree-import-guard is not importable in this environment",
                "Install the documented compatible preview or candidate "
                "into this pytest environment.",
            )
        )
        out["conditions"] = {
            "cwd_accessible": True,
            "pytest_compatible": False,
            "detector_compatible": False,
            "console_script_verified": False,
        }
        out["problems"] = [item["message"] for item in problems]
        out["problem_details"] = problems
        out["next_step"] = _next_step("missing_conditions", problems)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    conditions: dict[str, bool] = {"cwd_accessible": True}
    try:
        pytest_version = version("pytest")
        out["pytest_version"] = pytest_version
        conditions["pytest_compatible"] = pytest_available()
        if not conditions["pytest_compatible"]:
            problems.append(
                _problem(
                    "PYTEST_MISSING_OR_UNSUPPORTED",
                    f"pytest {pytest_version or 'missing'} is not in the supported >=8.2,<10 range",
                    "Select the project's existing pytest environment before checking source.",
                )
            )
    except PackageNotFoundError:
        out["pytest_version"] = None
        conditions["pytest_compatible"] = False
        problems.append(
            _problem(
                "PYTEST_MISSING_OR_UNSUPPORTED",
                "pytest is not installed in this environment",
                "Install pytest into the project's existing test environment, then retry.",
            )
        )

    try:
        dist = distribution("worktree-import-guard")
        out["detector_version"] = dist.version
        conditions["detector_compatible"] = distribution_compatible(dist)
        if not conditions["detector_compatible"]:
            raise ValueError("distribution revision is not a supported preview or candidate")
        out["console_script"] = str(console_script(dist))
        conditions["console_script_verified"] = True
    except PackageNotFoundError:
        out["detector_version"] = None
        conditions["detector_compatible"] = False
        conditions["console_script_verified"] = False
        problems.append(
            _problem(
                "DETECTOR_MISSING",
                "worktree-import-guard is not installed in this environment",
                "Install the documented compatible preview or candidate "
                "into this pytest environment.",
            )
        )
    except ValueError as error:
        out["detector_version"] = dist.version if "dist" in locals() else None
        conditions["detector_compatible"] = False
        conditions["console_script_verified"] = False
        problems.append(
            _problem(
                "DETECTOR_INCOMPATIBLE",
                str(error),
                "Install the README preview commit or the verified 0.1.1 candidate wheel.",
            )
        )
    except OSError as error:
        out["detector_version"] = dist.version if "dist" in locals() else None
        conditions["detector_compatible"] = bool(conditions.get("detector_compatible"))
        conditions["console_script_verified"] = False
        problems.append(
            _problem(
                "CONSOLE_SCRIPT_UNVERIFIED",
                f"installed console script could not be verified: {error}",
                "Reinstall the detector into this environment and confirm "
                "wt-import exists beside pytest.",
            )
        )

    config_invalid = False
    try:
        config = find_config(resolved_cwd)
        if config is not None:
            out["config_path"] = str(config)
            out["targets"] = [
                {"package": contract.package, "expected_root": str(contract.expected_root)}
                for contract in load_config(config)
            ]
    except Exception as exc:
        config_invalid = True
        out["config_invalid"] = True
        problems.append(
            _problem(
                "CONFIG_INVALID",
                f"saved settings cannot be used: {exc}",
                "Inspect the reported configuration file manually; "
                "the guard will not overwrite it.",
            )
        )

    out["conditions"] = conditions
    required = all(
        conditions.get(key, False)
        for key in (
            "cwd_accessible",
            "pytest_compatible",
            "detector_compatible",
            "console_script_verified",
        )
    )
    if config_invalid:
        out["status"] = "missing_conditions"
    elif required and out["targets"]:
        out["status"] = "ready"
    elif required:
        out["status"] = "needs_selection"
        problems.append(
            _problem(
                "TARGET_SELECTION_REQUIRED",
                "no confirmed package targets are saved for this project",
                "Run --setup once or provide explicit --expect mappings before guarded pytest.",
            )
        )
    else:
        out["status"] = "missing_conditions"

    out["problems"] = [item["message"] for item in problems]
    out["problem_details"] = problems
    out["next_step"] = _next_step(str(out["status"]), problems)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
