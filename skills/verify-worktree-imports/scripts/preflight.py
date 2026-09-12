"""Read-only probe of candidate interpreters for a single project."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from worktree_import_guard.environment_probe import choose_default_candidate, probe_candidates
from worktree_import_guard.project_config import find_config, load_config


def _problem(code: str, message: str, next_step: str) -> dict[str, str]:
    return {"code": code, "message": message, "next_step": next_step}


def _append_problem(
    problems: list[dict[str, str]], code: str, message: str, next_step: str
) -> None:
    problems.append(_problem(code, message, next_step))


def _next_step(status: str, problems: list[dict[str, str]]) -> str:
    if problems:
        return problems[0]["next_step"]
    if status == "ready":
        return "Run guarded pytest with the saved targets, for example bound command."
    if status == "needs_selection":
        return (
            "Confirm import-name to package-directory mappings, then save settings with "
            "--setup or provide explicit --expect for this run."
        )
    return "Resolve the reported preparation conditions before running guarded pytest."


def _candidate_summary(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "label": candidate["label"],
            "python": candidate["python"],
            "python_version": candidate["python_version"],
            "pytest_available": candidate["pytest_available"],
            "detector_installed": candidate["detector_installed"],
            "detector_compatible": candidate["detector_compatible"],
            "pytest_version": candidate.get("pytest_version"),
            "command_check": candidate.get("command_check"),
            "error": candidate.get("error"),
        }
        for candidate in candidates
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", type=Path, required=True)
    cwd = parser.parse_args().cwd
    raw_cwd = cwd.expanduser()
    resolved_cwd = raw_cwd.resolve()

    candidates = probe_candidates(resolved_cwd if resolved_cwd.is_dir() else raw_cwd)
    recommended, ambiguous = choose_default_candidate(candidates)
    problems: list[dict[str, str]] = []
    out: dict[str, object] = {
        "status": "missing_conditions",
        "conditions": {
            "cwd_accessible": raw_cwd.is_dir(),
            "candidate_ready": any(
                item["pytest_available"]
                and item["detector_installed"]
                and item["detector_compatible"]
                for item in candidates
            ),
            "detector_installed_any": any(item["detector_installed"] for item in candidates),
            "targets_found": False,
            "candidate_compatible": any(item["detector_compatible"] for item in candidates),
        },
        "problems": [],
        "problem_details": [],
        "cwd": str(resolved_cwd if raw_cwd.is_dir() else raw_cwd),
        "python": sys.executable,
        "python_resolved": str(Path(sys.executable).resolve()),
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "python_version": platform.python_version(),
        "config_path": None,
        "targets": [],
        "candidates": candidates,
        "recommended": recommended,
        "recommended_requires_confirmation": True,
    }

    if not raw_cwd.is_dir():
        _append_problem(
            problems,
            "PROJECT_NOT_ACCESSIBLE",
            "project directory is not accessible",
            "Choose an existing project directory that this interpreter can read.",
        )
        out["problems"] = [item["message"] for item in problems]
        out["problem_details"] = problems
        out["status"] = "missing_conditions"
        out["next_step"] = _next_step(out["status"], problems)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    out["cwd"] = str(resolved_cwd)

    if not candidates:
        _append_problem(
            problems,
            "NO_CANDIDATE_INTERPRETERS",
            "no local interpreter candidate with an executable path was found",
            "Run preflight from an environment that can run this project's pytest.",
        )
    if not out["conditions"]["candidate_ready"]:
        _append_problem(
            problems,
            "DETECTOR_OR_PYTEST_MISSING",
            "no detected interpreter combines supported pytest and installed detector",
            "Install worktree-import-guard and pytest in the project's existing environment.",
        )
    if recommended is not None and recommended.get("detector_installed"):
        out["recommended"] = recommended
        out["recommended_requires_confirmation"] = bool(
            ambiguous or not recommended.get("detector_compatible")
        )
    else:
        out["recommended"] = candidates[0] if candidates else None
    if not candidates:
        out["recommended"] = None

    config_invalid = False
    config = find_config(resolved_cwd)
    if config is not None:
        out["config_path"] = str(config)
        try:
            targets = load_config(config)
            out["targets"] = [
                {"package": contract.package, "expected_root": str(contract.expected_root)}
                for contract in targets
            ]
            out["conditions"]["targets_found"] = True
        except Exception as exc:
            config_invalid = True
            out["conditions"]["targets_found"] = False
            _append_problem(
                problems,
                "CONFIG_INVALID",
                f"saved settings cannot be used: {exc}",
                (
                    "Inspect the reported configuration file manually; "
                    "the guard will not overwrite it."
                ),
            )

    if config_invalid:
        out["status"] = "missing_conditions"
    else:
        if (
            out["conditions"]["cwd_accessible"]
            and out["conditions"]["candidate_ready"]
            and out["conditions"]["targets_found"]
        ):
            out["status"] = "ready"
        elif out["conditions"]["cwd_accessible"] and out["conditions"]["candidate_ready"]:
            out["status"] = "needs_selection"
            _append_problem(
                problems,
                "TARGET_SELECTION_REQUIRED",
                "no confirmed package targets are saved for this project",
                "Run --setup once or provide explicit --expect mappings before guarded pytest.",
            )

    if not out["conditions"]["candidate_ready"] and out["conditions"]["detector_installed_any"]:
        out["conditions"]["detector_compatible"] = False
    out["problems"] = [item["message"] for item in problems]
    out["problem_details"] = problems
    out["candidates"] = _candidate_summary(candidates)
    out["next_step"] = _next_step(out["status"], problems)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
