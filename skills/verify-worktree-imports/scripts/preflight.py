"""Read-only probe of the selected project Python and its installation."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", type=Path, required=True)
    cwd = parser.parse_args().cwd.resolve()
    out = {
        "status": "missing_conditions",
        "conditions": {"cwd_accessible": cwd.is_dir()},
        "problems": [],
        "cwd": str(cwd),
        "python": sys.executable,
        "python_resolved": str(Path(sys.executable).resolve()),
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "python_version": platform.python_version(),
        "config_path": None,
        "targets": [],
    }
    if not cwd.is_dir():
        out["problems"].append("project directory is not accessible")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    try:
        from run_check import console_script

        from worktree_import_guard import __version__
        from worktree_import_guard.onboarding import pytest_available
        from worktree_import_guard.project_config import find_config, load_config
    except ImportError:
        pytest_available = None
        find_config = load_config = None
        console_script = None
    try:
        out["pytest_version"] = version("pytest")
        out["conditions"]["pytest_compatible"] = bool(pytest_available and pytest_available())
    except PackageNotFoundError:
        out["pytest_version"] = None
        out["conditions"]["pytest_compatible"] = False
    try:
        dist = distribution("worktree-import-guard")
        out["detector_version"] = dist.version
        direct = json.loads(dist.read_text("direct_url.json") or "null")
        preview = "edae3e6fa9a0b065385a080c371c9c17728b4656"
        compatible = dist.version == __version__ and (dist.version == "0.1.1" or (
            dist.version == "0.1.0"
            and isinstance(direct, dict)
            and direct.get("vcs_info", {}).get("commit_id") == preview
        ))
        out["conditions"]["detector_compatible"] = compatible
        if not compatible:
            raise ValueError("module/distribution version mismatch or unverified CLI revision")
        out["console_script"] = str(console_script(dist))
        out["conditions"]["console_script_verified"] = True
    except (PackageNotFoundError, ValueError, OSError):
        out["detector_version"] = None
        out["conditions"]["detector_compatible"] = False
        out["conditions"]["console_script_verified"] = False
    if find_config:
        try:
            config = find_config(cwd)
            if config:
                out["config_path"] = str(config)
                out["targets"] = [
                    {"package": c.package, "expected_root": str(c.expected_root)}
                    for c in load_config(config)
                ]
        except Exception as exc:
            out["problems"].append(f"invalid_config: {exc}")
            out["config_invalid"] = True
    required = all(
        out["conditions"].get(k, False)
        for k in (
            "cwd_accessible",
            "pytest_compatible",
            "detector_compatible",
            "console_script_verified",
        )
    )
    if out.get("config_invalid"):
        out["status"] = "missing_conditions"
    else:
        out["status"] = (
            "ready"
            if required and out["targets"]
            else "needs_selection"
            if required
            else "missing_conditions"
        )
    if not required:
        out["problems"].append("one or more required conditions are missing")
    out["next_step"] = "Run guarded pytest after confirming targets."
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
