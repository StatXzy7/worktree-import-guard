"""Bind one existing wt-import invocation to a fresh report; never classify imports."""

from __future__ import annotations

import argparse
import builtins
import json
import os
import platform
import subprocess
import sys
import tempfile
import uuid
from importlib.metadata import distribution
from pathlib import Path

from worktree_import_guard import launcher
from worktree_import_guard.compatibility import distribution_compatible
from worktree_import_guard.launcher import command_for_path

sysconfig = launcher.sysconfig
print = builtins.print


def _canonical_path(value: object) -> str:
    try:
        return str(Path(value).resolve())
    except TypeError:
        return str(value)


def identity() -> dict[str, object]:
    return {
        "python": sys.executable,
        "python_resolved": str(Path(sys.executable).resolve()),
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "python_version": platform.python_version(),
    }


def console_script(dist):
    return launcher.console_script(dist)


def _append_evidence_error(envelope: dict[str, object], message: str) -> None:
    if "evidence_errors" not in envelope:
        envelope["evidence_errors"] = []
    errors = envelope["evidence_errors"]
    if isinstance(errors, list):
        errors.append(message)
    else:
        envelope["evidence_errors"] = [str(message)]


def _write_json(path: str | Path, value: object) -> None:
    destination = Path(path)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(destination)


def _save_envelope(envelope_path: Path, envelope: dict[str, object], *, prefix: str) -> None:
    try:
        _write_json(envelope_path, envelope)
        envelope["evidence_persisted"] = True
    except OSError as error:
        envelope["evidence_persisted"] = False
        _append_evidence_error(envelope, f"{prefix}: {error}")


def _build_envelope(
    script: Path,
    cwd: Path,
    expectations: list[str],
    pytest_args: list[str],
    command: list[str],
    report_path: Path,
    tool: dict[str, object],
    contracts,
) -> dict[str, object]:
    return {
        "runtime": identity(),
        "console_script": str(script),
        "cwd": str(cwd),
        "expect": expectations,
        "pytest_args": pytest_args,
        "tool": tool,
        "targets": [
            {"package": contract.package, "expected_root": str(contract.expected_root)}
            for contract in contracts
        ],
        "report_path": str(report_path),
        "process_exit_code": None,
        "pytest_exit_code_known": False,
        "command": command,
        "command_text": command_for_path(Path(command[0]), command[1:]),
        "result": "not_started",
        "result_description": "No usable verification result was produced yet",
        "preparation_succeeded": False,
        "execution_started": False,
        "subprocess_launched": False,
        "subprocess_finished": False,
        "engine_report_exists": False,
        "report_validated": False,
        "failure_stage": "prepare",
        "finalized": False,
        "evidence_persisted": False,
        "result_delivered": False,
        "run_id": report_path.parent.name,
    }


def _compatible_python_run(
    runtime_python: object,
    runtime_python_resolved: object,
    run_python: object,
    run_python_resolved: object,
) -> bool:
    if run_python == runtime_python:
        return True
    if runtime_python in {"python", "python3"}:
        return str(Path(run_python).name) in {"python", "python3"} and _canonical_path(
            run_python_resolved
        ) == _canonical_path(runtime_python_resolved)
    return _canonical_path(run_python) == _canonical_path(runtime_python)


def _interrupted_before_launch(
    cwd: Path, expectations: list[str], pytest_args: list[str]
) -> dict[str, object]:
    return {
        "runtime": identity(),
        "console_script": None,
        "cwd": str(cwd),
        "expect": expectations,
        "pytest_args": pytest_args,
        "tool": {},
        "targets": [],
        "report_path": None,
        "process_exit_code": None,
        "pytest_exit_code_known": False,
        "command": [],
        "command_text": None,
        "result": "not_started",
        "result_description": "Execution was interrupted before the subprocess launch",
        "preparation_succeeded": False,
        "execution_started": False,
        "subprocess_launched": False,
        "subprocess_finished": False,
        "engine_report_exists": False,
        "report_validated": False,
        "failure_stage": "interruption_before_launch",
        "finalized": False,
        "evidence_persisted": False,
        "result_delivered": False,
        "run_id": None,
    }


def _finalize(envelope: dict[str, object], path: Path, *, prefix: str) -> dict[str, object]:
    if envelope.get("failure_stage") is None:
        envelope["failure_stage"] = "finalizing"
    envelope.setdefault("preparation_succeeded", True)
    _save_envelope(path, envelope, prefix=prefix)
    envelope["finalized"] = envelope["evidence_persisted"]
    return envelope


def prepare(cwd: Path, expectations: list[str]) -> tuple[Path, object, dict[str, object]]:
    from worktree_import_guard.contracts import parse_contracts
    from worktree_import_guard.onboarding import pytest_available
    from worktree_import_guard.project_config import find_config, load_config

    dist = distribution("worktree-import-guard")
    if not distribution_compatible(dist):
        raise ValueError("Unverified CLI revision; use the documented compatible candidate/preview")
    if not pytest_available():
        raise ValueError("This environment needs supported pytest >=8.2,<10")
    script = console_script(dist)
    try:
        direct_url = dist.read_text("direct_url.json")
    except OSError:
        direct_url = None
    if expectations:
        contracts = parse_contracts(expectations, cwd)
    elif (config := find_config(cwd)) is not None:
        contracts = load_config(config)
    else:
        raise ValueError("No confirmed targets: reuse static candidates, then ask for a mapping")
    return script, contracts, {"version": dist.version, "direct_url": direct_url}


def validate(report: dict[str, object], envelope: dict[str, object]) -> dict[str, object]:
    if type(report.get("schema_version")) is not int or report["schema_version"] != 2:
        raise ValueError("Unsupported report schema")

    run = report["run"]
    guard = report["guard"]
    targets = report["targets"]
    if type(run) is not dict or type(guard) is not dict or type(targets) is not list:
        raise ValueError("Invalid report structure")

    runtime = envelope["runtime"]
    if not _compatible_python_run(
        runtime["python"], runtime["python_resolved"], run["python"], run["python_resolved"]
    ):
        raise ValueError("Report runtime mismatch: python")
    if _canonical_path(run["python_resolved"]) != _canonical_path(runtime["python_resolved"]):
        raise ValueError("Report runtime mismatch: python_resolved")
    if _canonical_path(run["sys_prefix"]) != _canonical_path(runtime["sys_prefix"]):
        raise ValueError("Report runtime mismatch: sys_prefix")
    if _canonical_path(run["sys_base_prefix"]) != _canonical_path(runtime["sys_base_prefix"]):
        raise ValueError("Report runtime mismatch: sys_base_prefix")
    if run["cwd"] != envelope["cwd"]:
        raise ValueError("Report runtime mismatch: cwd")
    if run["pytest_args"] != envelope["pytest_args"]:
        raise ValueError("Report run mismatch: pytest args")

    if not isinstance(guard["status"], str) or guard["status"] not in {"pass", "fail", "unknown"}:
        raise ValueError("Unsupported report status")
    for key in ("complete", "observation_complete"):
        if key not in guard or type(guard[key]) is not bool:
            raise ValueError(f"Invalid completeness: {key}")
    for target in targets:
        status = target.get("status")
        if (
            not isinstance(target["reasons"], list)
            or not target["reasons"]
            or not all(isinstance(reason, str) for reason in target["reasons"])
            or not isinstance(target["observations"], list)
        ):
            raise ValueError("Invalid target evidence structure")
        if status not in {"pass", "fail", "unknown"}:
            raise ValueError("Unsupported report status")
    if guard["status"] == "pass" and (
        not guard["complete"]
        or not guard["observation_complete"]
        or any(t["status"] != "pass" for t in targets)
    ):
        raise ValueError("Inconsistent PASS report")

    expected = [
        {"package": target["package"], "expected_root": _canonical_path(target["expected_root"])}
        for target in envelope["targets"]
    ]
    observed = [
        {"package": target["package"], "expected_root": _canonical_path(target["expected_root"])}
        for target in targets
    ]
    if expected != observed:
        raise ValueError("Report target mismatch")

    tool = report["tool"]
    if not isinstance(tool, dict):
        raise ValueError("Invalid report tool")
    if tool["name"] != "worktree-import-guard":
        raise ValueError("Report tool mismatch")
    if tool["version"] != envelope["tool"]["version"]:
        raise ValueError("Report runtime mismatch: tool version")

    command = envelope.get("command")
    if command is not None and command != [] and envelope.get("console_script") is not None:
        if type(command) is not list or not command:
            raise ValueError("Invalid command binding")
        if _canonical_path(command[0]) != _canonical_path(envelope["console_script"]):
            raise ValueError("Report command mismatch")
    code = report["pytest"]["exit_code"]
    if type(code) is not int or code < 0:
        raise ValueError("Invalid pytest exit code")
    expected = code if code else {"pass": 0, "fail": 1, "unknown": 2}[guard["status"]]
    if envelope["process_exit_code"] != expected:
        raise ValueError("Report/process exit mismatch")

    return report


def _summary(
    report: dict[str, object], limit: int = 10, observations_limit: int = 3
) -> dict[str, object]:
    targets = report["targets"]
    counts = {"total": len(targets), "pass": 0, "fail": 0, "unknown": 0}
    visible = []
    for target in sorted(targets, key=lambda item: (item["status"] == "pass", item["package"])):
        status = target["status"]
        counts[status] += 1
        if len(visible) < limit:
            visible.append(
                {
                    "package": target["package"],
                    "status": status,
                    "reasons": target["reasons"],
                    "expected_root": target["expected_root"],
                    "representative_observations": target["observations"][:observations_limit],
                }
            )
    return {
        "pytest_exit_code": report["pytest"]["exit_code"],
        "source_status": report["guard"]["status"],
        "complete": report["guard"]["complete"],
        "observation_complete": report["guard"]["observation_complete"],
        "target_counts": counts,
        "targets": visible,
        "truncated": len(targets) > limit,
    }


def run_check(cwd, expectations, pytest_args, evidence_dir=None):
    if not cwd.is_dir():
        raise ValueError("Target project is not accessible here; verification was not started")
    try:
        script, contracts, tool = prepare(cwd, expectations)
    except KeyboardInterrupt:
        return _interrupted_before_launch(cwd, expectations, pytest_args)

    if evidence_dir is not None:
        root = Path(evidence_dir).expanduser()
        if root.is_symlink():
            raise ValueError("Evidence directory must be a real directory, not a symlink")
        root = root.resolve()
        if not root.exists():
            raise ValueError("Evidence directory must already exist")
        if not root.is_dir():
            raise ValueError("Evidence directory must be a real directory")
        folder = root / ("run-" + uuid.uuid4().hex)
        folder.mkdir()
    else:
        folder = Path(tempfile.mkdtemp(prefix="wt-import-check-"))

    report_path = folder / "report.json"
    command = [str(script), "--report-json", str(report_path)]
    for value in expectations:
        command.extend(["--expect", value])
    command.extend(["--", *pytest_args])

    envelope = _build_envelope(
        script, cwd, expectations, pytest_args, command, report_path, tool, contracts
    )
    envelope["preparation_succeeded"] = True
    envelope_path = folder / "envelope.json"

    try:
        envelope["failure_stage"] = "launch"
        _save_envelope(envelope_path, envelope, prefix="Could not write envelope before start")

        with (
            (folder / "stdout.log").open("wb") as out,
            (folder / "stderr.log").open("wb") as err,
        ):
            envelope["execution_started"] = True
            envelope["subprocess_launched"] = True
            process = subprocess.run(
                command,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                check=False,
            )
            envelope["process_exit_code"] = process.returncode
            envelope["pytest_exit_code_known"] = True
            envelope["subprocess_finished"] = True

        envelope["failure_stage"] = "report_read"
        envelope["engine_report_exists"] = report_path.is_file()
        if not envelope["engine_report_exists"]:
            envelope["result"] = "unusable_report"
            envelope["result_description"] = "No usable verification result: report missing"
            envelope["error"] = "No usable verification result: report missing"
            return _finalize(envelope, envelope_path, prefix="Could not write envelope")

        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            envelope["result"] = "unusable_report"
            envelope["result_description"] = f"No usable verification result: {error}"
            envelope["error"] = f"No usable verification result: {error}"
            return _finalize(envelope, envelope_path, prefix="Could not write envelope")

        try:
            validated = validate(report, envelope)
        except (KeyError, TypeError, ValueError) as error:
            envelope["result"] = "unusable_report"
            envelope["result_description"] = f"No usable verification result: {error}"
            envelope["error"] = f"No usable verification result: {error}"
            return _finalize(envelope, envelope_path, prefix="Could not write envelope")

        envelope["report_validated"] = True
        envelope["source_status"] = validated["guard"]["status"]
        envelope["result"] = "usable_report"
        envelope["result_description"] = "Usable report bound to execution envelope"
        envelope["summary"] = _summary(validated)
        envelope["summary"]["cwd"] = validated["run"]["cwd"]
        envelope["summary"]["report_path"] = str(report_path)
        return _finalize(envelope, envelope_path, prefix="Could not write envelope")
    except KeyboardInterrupt:
        if envelope.get("subprocess_launched"):
            envelope["subprocess_finished"] = envelope["process_exit_code"] is not None
            envelope["failure_stage"] = "interrupted_after_launch"
            envelope["result"] = "unusable_report"
            envelope["result_description"] = "Execution was interrupted after launch"
            envelope["error"] = "No usable verification result: interrupted"
        else:
            envelope["failure_stage"] = "interruption_before_launch"
            envelope["result"] = "not_started"
            envelope["result_description"] = "Execution was interrupted before launch"
            envelope["error"] = "No usable verification result: interrupted"
        return _finalize(
            envelope, envelope_path, prefix="Could not write envelope after interruption"
        )
    except OSError as error:
        envelope["failure_stage"] = "launch_or_wait"
        envelope["error"] = f"No usable verification result: {error}"
        if envelope.get("subprocess_launched") or envelope.get("execution_started"):
            envelope["result"] = "unusable_report"
        elif envelope["result"] == "not_started":
            envelope["result"] = "not_started"
        return _finalize(envelope, envelope_path, prefix="Could not write envelope")


def exit_status(result) -> int:
    code = result.get("process_exit_code")
    if isinstance(code, int) and code not in (0, None):
        return code
    if result.get("result") == "usable_report":
        if not result.get("finalized", False):
            return 2
        return {"pass": 0, "fail": 1, "unknown": 2}.get(result.get("source_status"), 2)
    return 2


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    args.pytest_args = args.pytest_args[1:] if args.pytest_args[:1] == ["--"] else args.pytest_args
    result: dict[str, object]
    try:
        result = run_check(args.cwd.resolve(), args.expect, args.pytest_args, args.evidence_dir)
    except (OSError, ValueError, ImportError, KeyError, TypeError, AttributeError) as error:
        result = {"result": "not_started", "error": str(error)}
    try:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except OSError as error:
        if isinstance(result, dict):
            result["result_delivered"] = False
            _append_evidence_error(result, f"Could not write result to stdout: {error}")
            result.setdefault("error", f"Could not write result to stdout: {error}")
            return exit_status(result)
        return 2
    if isinstance(result, dict):
        result["result_delivered"] = True
    return exit_status(result)


if __name__ == "__main__":
    raise SystemExit(main())
