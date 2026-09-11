"""Read-only environment preflight for the verify-worktree-imports skill."""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--cwd", type=Path, required=True)
    a = p.parse_args(); cwd = a.cwd.resolve()
    out = {"status": "ready" if cwd.is_dir() else "missing_conditions", "cwd": str(cwd),
           "python": sys.executable, "python_resolved": str(Path(sys.executable).resolve()),
           "sys_prefix": sys.prefix, "sys_base_prefix": sys.base_prefix,
           "detector_installed": False, "console_script": shutil.which("wt-import"),
           "config": str(cwd / ".wt-import.json") if (cwd / ".wt-import.json").is_file() else None,
           "next_step": "Run guarded pytest after confirming targets."}
    try:
        import pytest
        out["pytest_version"] = pytest.__version__
    except Exception as e:
        out["pytest_version"] = None; out["pytest_error"] = str(e)
    try:
        from importlib.metadata import version
        out["detector_version"] = version("worktree-import-guard"); out["detector_installed"] = True
    except Exception:
        out["detector_version"] = None
    if not out["detector_installed"]: out["status"] = "missing_conditions"
    print(json.dumps(out, ensure_ascii=False, indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
