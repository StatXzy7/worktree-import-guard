"""Bind one existing wt-import invocation to a fresh report; never classify imports."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import sysconfig
import tempfile
from importlib.metadata import distribution
from pathlib import Path


def identity():
    return {
        "python": sys.executable,
        "python_resolved": str(Path(sys.executable).resolve()),
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "python_version": platform.python_version(),
    }


def console_script(dist):
    name = "wt-import.exe" if os.name == "nt" else "wt-import"
    recorded = {
        Path(dist.locate_file(f)).resolve()
        for f in (dist.files or []) if Path(f).name == name
    }
    preferred = Path(sysconfig.get_path("scripts")) / name
    if preferred.resolve() in recorded and preferred.is_file():
        return preferred
    existing = [p for p in recorded if p.is_file()]
    if len(existing) != 1:
        raise ValueError("Cannot identify one installed console script in this environment")
    return existing[0]


def prepare(cwd, expectations):
    # Reuse the installed engine's contracts; do not import candidate project packages.
    from worktree_import_guard import __version__
    from worktree_import_guard.contracts import parse_contracts
    from worktree_import_guard.onboarding import pytest_available
    from worktree_import_guard.project_config import find_config, load_config

    dist = distribution("worktree-import-guard")
    direct = json.loads(dist.read_text("direct_url.json") or "null")
    # Old previews all used 0.1.0. Only the verified preview revision is accepted.
    preview = "edae3e6fa9a0b065385a080c371c9c17728b4656"
    verified_preview = (
        isinstance(direct, dict) and direct.get("vcs_info", {}).get("commit_id") == preview
    )
    if dist.version != __version__ or not (
        dist.version == "0.1.1" or (dist.version == "0.1.0" and verified_preview)
    ):
        raise ValueError("Unverified CLI revision; use the documented compatible candidate/preview")
    if not pytest_available():
        raise ValueError("This environment needs supported pytest >=8.2,<10")
    script = console_script(dist)
    if expectations:
        contracts = parse_contracts(expectations, cwd)
    elif (config := find_config(cwd)) is not None:
        contracts = load_config(config)
    else:
        raise ValueError("No confirmed targets: reuse static candidates, then ask for a mapping")
    return script, contracts, {"version": dist.version, "direct_url": direct}


def validate(report, envelope):
    """Validate report structure and invocation identity, not provenance evidence."""
    if type(report.get("schema_version")) is not int or report["schema_version"] != 2:
        raise ValueError("Unsupported report schema")
    run, guard, targets = report["run"], report["guard"], report["targets"]
    if not isinstance(run["python"], str) or not run["python"]:
        raise ValueError("Missing raw interpreter identity")
    for key, value in envelope["runtime"].items():
        if key == "python":
            # python and python3 can be aliases in the same venv. Keep both raw
            # paths as evidence; resolved binary PLUS prefixes identify the env.
            continue
        if run[key] != value:
            raise ValueError(f"Report runtime mismatch: {key}")
    if run["cwd"] != envelope["cwd"] or run["pytest_args"] != envelope["pytest_args"]:
        raise ValueError("Report cwd/test selection mismatch")
    if report["tool"]["version"] != envelope["tool"]["version"]:
        raise ValueError("Report CLI version mismatch")
    if report["tool"]["name"] != "worktree-import-guard":
        raise ValueError("Report tool mismatch")
    if not isinstance(targets, list) or not targets:
        raise ValueError("Missing report targets")
    actual = [{"package": t["package"], "expected_root": t["expected_root"]} for t in targets]
    if actual != envelope["targets"]:
        raise ValueError("Report target mismatch")
    statuses = {"pass", "fail", "unknown"}
    if guard["status"] not in statuses or any(t["status"] not in statuses for t in targets):
        raise ValueError("Unsupported report status")
    for key in ("complete", "observation_complete"):
        if type(guard[key]) is not bool:
            raise ValueError(f"Invalid completeness: {key}")
    for target in targets:
        if not isinstance(target["reasons"], list) or not target["reasons"] or not all(
            isinstance(reason, str) for reason in target["reasons"]
        ) or not isinstance(target["observations"], list):
            raise ValueError("Invalid target evidence structure")
    if guard["status"] == "pass" and (
        not guard["complete"] or not guard["observation_complete"]
        or any(t["status"] != "pass" for t in targets)
    ):
        raise ValueError("Inconsistent PASS report")
    code = report["pytest"]["exit_code"]
    if type(code) is not int or code < 0:
        raise ValueError("Invalid pytest exit code")
    expected = code if code else {"pass": 0, "fail": 1, "unknown": 2}[guard["status"]]
    if envelope["process_exit_code"] != expected:
        raise ValueError("Report/process exit mismatch")
    return report


def run_check(cwd, expectations, pytest_args):
    if not cwd.is_dir():
        raise ValueError("Target project is not accessible here; verification was not started")
    script, contracts, tool = prepare(cwd, expectations)
    folder = Path(tempfile.mkdtemp(prefix="wt-import-check-"))
    report_path = folder / "report.json"  # New private directory, never a previous PASS.
    envelope = {
        "runtime": identity(), "console_script": str(script), "cwd": str(cwd),
        "expect": expectations, "pytest_args": pytest_args, "tool": tool,
        "targets": [{"package": c.package, "expected_root": str(c.expected_root)}
                    for c in contracts],
        "report_path": str(report_path), "process_exit_code": None,
        "result": "not_started",
    }
    command = [str(script), "--report-json", str(report_path)]
    for value in expectations:
        command.extend(["--expect", value])
    command.extend(["--", *pytest_args])
    envelope["command"] = command
    envelope_path = folder / "envelope.json"

    def save():
        envelope_path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")

    save()
    try:
        # Preserve the project environment and arguments. Logs are untrusted data.
        with (folder / "stdout.log").open("wb") as out, (folder / "stderr.log").open("wb") as err:
            result = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, check=False)
        envelope["process_exit_code"] = result.returncode
        envelope["result"] = "unusable_report"
        report = validate(json.loads(report_path.read_text(encoding="utf-8")), envelope)
        envelope["result"] = "usable_report"
        envelope["pytest_exit_code"] = report["pytest"]["exit_code"]
        envelope["source_status"] = report["guard"]["status"]
        return envelope
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        envelope["error"] = f"No usable verification result: {error}"
        return envelope
    finally:
        save()


def exit_status(result):
    code = result.get("process_exit_code")
    if code:
        return code  # Even a missing report must not hide a native nonzero exit.
    return 0 if result["result"] == "usable_report" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    pytest_args = args.pytest_args
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]
    try:
        result = run_check(args.cwd.resolve(), args.expect, pytest_args)
    except (OSError, ValueError, ImportError, KeyError, TypeError, AttributeError) as error:
        result = {"result": "not_started", "error": str(error)}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return exit_status(result)


if __name__ == "__main__":
    raise SystemExit(main())
