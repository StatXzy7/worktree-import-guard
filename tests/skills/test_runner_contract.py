"""Deterministic Skill-helper contract checks."""

from __future__ import annotations

import copy
import errno
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/verify-worktree-imports/scripts/run_check.py"
spec = importlib.util.spec_from_file_location("skill_runner", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def _report(tmp_path: Path, *, exit_code: int = 0, status: str = "pass") -> dict[str, object]:
    report = json.loads((ROOT / "tests/golden/schema-v2-pass.json").read_text(encoding="utf-8"))
    runtime = runner.identity()
    report["run"].update(
        {
            "python": runtime["python"],
            "python_resolved": runtime["python_resolved"],
            "sys_prefix": runtime["sys_prefix"],
            "sys_base_prefix": runtime["sys_base_prefix"],
            "python_version": runtime["python_version"],
            "cwd": str(tmp_path),
            "pytest_args": ["-q"],
        }
    )
    report["guard"]["status"] = status
    report["pytest"]["exit_code"] = exit_code
    report["targets"][0]["expected_root"] = str(tmp_path / "pkg")
    return report


def _contracts(tmp_path: Path):
    from worktree_import_guard.contracts import parse_contracts

    (tmp_path / "pkg").mkdir()
    return parse_contracts(["pkg=pkg"], tmp_path)


def envelope(report: dict[str, object]) -> dict[str, object]:
    return {
        "runtime": {
            k: v
            for k, v in report["run"].items()
            if k not in {"cwd", "pytest_args", "pytest_version"}
        },
        "cwd": report["run"]["cwd"],
        "pytest_args": report["run"]["pytest_args"],
        "tool": report["tool"],
        "targets": [
            {"package": t["package"], "expected_root": t["expected_root"]}
            for t in report["targets"]
        ],
        "process_exit_code": report["pytest"]["exit_code"]
        or {"pass": 0, "fail": 1, "unknown": 2}[report["guard"]["status"]],
    }


@pytest.mark.parametrize("path", sorted((ROOT / "tests/golden").glob("schema-v2-*.json")))
def test_engine_golden_reports_are_preserved(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    original = copy.deepcopy(report)
    assert runner.validate(report, envelope(report)) == original
    report["metrics"]["future_counter"] = 10
    assert runner.validate(report, envelope(report)) == report


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(schema_version=3),
        lambda r: r.update(schema_version=True),
        lambda r: r["guard"].update(status="green"),
        lambda r: r["guard"].update(complete=False),
        lambda r: r["guard"].update(observation_complete=False),
        lambda r: r["run"].update(sys_prefix="other venv"),
        lambda r: r["run"].update(python_resolved="other python"),
        lambda r: r["run"].update(cwd="other machine"),
        lambda r: r["run"].update(pytest_args=["different.py"]),
        lambda r: r["targets"][0].update(expected_root="other source"),
        lambda r: r["targets"][0].update(status="unknown"),
        lambda r: r["pytest"].update(exit_code=True),
        lambda r: r["tool"].update(version="999"),
    ],
)
def test_invalid_reports_rejected(change):
    report = json.loads((ROOT / "tests/golden/schema-v2-pass.json").read_text(encoding="utf-8"))
    bound = copy.deepcopy(envelope(report))
    change(report)
    with pytest.raises(ValueError):
        runner.validate(report, bound)


def test_native_exit_six_and_test_failure_source_pass():
    report = json.loads((ROOT / "tests/golden/schema-v2-pass.json").read_text(encoding="utf-8"))
    for code in (1, 6):
        report["pytest"]["exit_code"] = code
        bound = envelope(report)
        assert runner.validate(report, bound)["guard"]["status"] == "pass"
        bound["process_exit_code"] = 0
        with pytest.raises(ValueError, match="exit mismatch"):
            runner.validate(report, bound)


@pytest.mark.parametrize("code", [1, 2, 3, 4, 5, 6])
def test_unusable_report_preserves_native_nonzero_exit(code):
    assert runner.exit_status({"result": "unusable_report", "process_exit_code": code}) == code
    assert runner.exit_status({"result": "unusable_report", "process_exit_code": 0}) == 2


@pytest.mark.parametrize("code", [1, 5, 6])
def test_process_nonzero_without_report_preserves_exit(tmp_path, monkeypatch, code):
    package = tmp_path / "pkg"
    package.mkdir()
    from worktree_import_guard.contracts import parse_contracts

    monkeypatch.setattr(
        runner,
        "prepare",
        lambda *_: (
            Path("wt-import"),
            parse_contracts(["pkg=pkg"], tmp_path),
            {"version": "0.1.2"},
        ),
    )

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, code)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert result["execution_started"] is True
    assert result["process_exit_code"] == code
    assert result["result"] == "unusable_report"
    assert runner.exit_status(result) == code


@pytest.mark.parametrize("code", [0, 1, 5, 6])
def test_run_check_exit_code_is_preserved(tmp_path, monkeypatch, code):
    report = _report(tmp_path, exit_code=code)
    contracts = _contracts(tmp_path)
    monkeypatch.setattr(
        runner, "prepare", lambda *_: (Path("wt-import"), contracts, {"version": "0.1.2"})
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        Path(command[2]).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, code)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert len(calls) == 1
    assert result["preparation_succeeded"] is True
    assert result["subprocess_launched"] is True
    assert result["subprocess_finished"] is True
    assert result["pytest_exit_code_known"] is True
    assert result["engine_report_exists"] is True
    assert result["report_validated"] is True
    assert result["evidence_persisted"] is True
    assert result["result"] == "usable_report"
    assert runner.exit_status(result) == code


@pytest.mark.parametrize("payload", [None, "{bad", '{"schema_version":99}'])
def test_run_check_missing_or_damaged_report_marks_unusable_and_no_rerun(
    tmp_path, monkeypatch, payload
):
    contracts = _contracts(tmp_path)
    calls = []
    monkeypatch.setattr(
        runner, "prepare", lambda *_: (Path("wt-import"), contracts, {"version": "0.1.2"})
    )

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if payload is not None:
            Path(command[2]).write_text(payload, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert len(calls) == 1
    assert result["result"] == "unusable_report"
    assert result["subprocess_finished"] is True
    assert result["engine_report_exists"] == (payload is not None)
    assert runner.exit_status(result) == 2


def test_run_check_identity_mismatch_never_reused_as_pass(tmp_path, monkeypatch):
    contracts = _contracts(tmp_path)
    report = _report(tmp_path, exit_code=0)
    report["run"]["python"] = "/usr/bin/python-other"
    monkeypatch.setattr(
        runner, "prepare", lambda *_: (Path("wt-import"), contracts, {"version": "0.1.2"})
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        Path(command[2]).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert len(calls) == 1
    assert result["result"] == "unusable_report"
    assert result["engine_report_exists"] is True
    assert result["report_validated"] is False
    assert runner.exit_status(result) == 2


@pytest.mark.parametrize("payload", [None, "{bad", '{"schema_version":99}'])
def test_fresh_report_missing_or_damaged_never_uses_old_pass(tmp_path, monkeypatch, payload):
    old = tmp_path / "report.json"
    old.write_text('{"guard":{"status":"pass"}}', encoding="utf-8")
    package = tmp_path / "pkg"
    package.mkdir()
    from worktree_import_guard.contracts import parse_contracts

    monkeypatch.setattr(
        runner,
        "prepare",
        lambda *_: (
            Path("wt-import"),
            parse_contracts(["pkg=pkg"], tmp_path),
            {"version": "0.1.2"},
        ),
    )
    calls = []

    def fake(command, **kwargs):
        calls.append((command, kwargs))
        path = Path(command[2])
        assert path != old and not path.exists()
        if payload is not None:
            path.write_text(payload, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner.subprocess, "run", fake)
    result = runner.run_check(tmp_path, [], ["-q", "test 空 格.py", "; echo do not execute"])
    assert len(calls) == 1
    assert result["result"] == "unusable_report"
    assert calls[0][0][-1] == "; echo do not execute"
    assert calls[0][1]["stdin"] == subprocess.DEVNULL
    assert "shell" not in calls[0][1]
    assert json.loads(old.read_text(encoding="utf-8"))["guard"]["status"] == "pass"
    assert runner.exit_status(result) == 2


def test_final_save_failure_keeps_running_exit_and_process_result(tmp_path, monkeypatch):
    package = tmp_path / "pkg"
    package.mkdir()
    from worktree_import_guard.contracts import parse_contracts

    contracts = parse_contracts(["pkg=pkg"], tmp_path)
    report = _report(tmp_path, exit_code=0)
    monkeypatch.setattr(
        runner, "prepare", lambda *_: (Path("wt-import"), contracts, {"version": "0.1.2"})
    )
    write_calls = {"count": 0}

    def fake_write(path, value):
        write_calls["count"] += 1
        if write_calls["count"] == 2:
            raise OSError(errno.EACCES, "denied", str(path))
        Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_run(command, **kwargs):
        Path(command[2]).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runner, "_write_json", fake_write)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert result["execution_started"] is True
    assert result["process_exit_code"] == 0
    assert result["result"] == "usable_report"
    assert result["evidence_persisted"] is False
    assert any(
        "Could not write envelope" in str(item) for item in result.get("evidence_errors", [])
    )
    assert runner.exit_status(result) == 2


@pytest.mark.parametrize("code", [1, 6])
def test_final_save_failure_keeps_native_nonzero_exit(tmp_path, monkeypatch, code):
    package = tmp_path / "pkg"
    package.mkdir()
    from worktree_import_guard.contracts import parse_contracts

    contracts = parse_contracts(["pkg=pkg"], tmp_path)
    report = _report(tmp_path, exit_code=code)
    monkeypatch.setattr(
        runner, "prepare", lambda *_: (Path("wt-import"), contracts, {"version": "0.1.2"})
    )
    write_calls = {"count": 0}

    def fake_write(path, value):
        write_calls["count"] += 1
        if write_calls["count"] == 2:
            raise OSError(errno.EACCES, "denied", str(path))
        Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def fake_run(command, **kwargs):
        Path(command[2]).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return subprocess.CompletedProcess(command, code)

    monkeypatch.setattr(runner, "_write_json", fake_write)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert result["process_exit_code"] == code
    assert result["result"] == "usable_report"
    assert result["evidence_persisted"] is False
    assert any(
        "Could not write envelope" in str(item) for item in result.get("evidence_errors", [])
    )
    assert runner.exit_status(result) == code


def test_interpreter_alias_same_environment_is_accepted():
    report = json.loads((ROOT / "tests/golden/schema-v2-pass.json").read_text(encoding="utf-8"))
    bound = copy.deepcopy(envelope(report))
    bound["runtime"]["python"] = "python3"
    assert runner.validate(report, bound) == report


def test_runner_main_reports_stdout_delivery_failure_and_preserves_exit(tmp_path, monkeypatch):
    envelope_payload = {
        "process_exit_code": 6,
        "result": "unusable_report",
        "result_delivered": False,
    }

    def fake_run(*_args, **_kwargs):
        return envelope_payload

    monkeypatch.setattr(runner, "run_check", fake_run)
    monkeypatch.setattr(
        runner, "print", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("stdout closed"))
    )
    code = runner.main(["--cwd", str(tmp_path)])
    assert code == 6
    assert envelope_payload["result_delivered"] is False
    assert any(
        str(item).startswith("Could not write result to stdout")
        for item in envelope_payload.get("evidence_errors", [])
    )


def test_interruption_before_launch_preserves_non_execution_flags(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "prepare", lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    invoked = {"run": 0}

    def forbidden_run(*_args, **_kwargs):
        invoked["run"] += 1
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr(runner.subprocess, "run", forbidden_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert invoked["run"] == 0
    assert result["failure_stage"] == "interruption_before_launch"
    assert result["result"] == "not_started"
    assert result["preparation_succeeded"] is False
    assert result["subprocess_launched"] is False
    assert result["execution_started"] is False
    assert result["subprocess_finished"] is False


def test_interruption_after_launch_keeps_executed_state_and_no_rerun(tmp_path, monkeypatch):
    contracts = _contracts(tmp_path)
    monkeypatch.setattr(
        runner, "prepare", lambda *_: (Path("wt-import"), contracts, {"version": "0.1.2"})
    )
    calls = {"run": 0}

    def fake_run(*_args, **_kwargs):
        calls["run"] += 1
        raise KeyboardInterrupt()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_check(tmp_path, [], ["-q"])
    assert calls["run"] == 1
    assert result["failure_stage"] == "interrupted_after_launch"
    assert result["result"] == "unusable_report"
    assert result["preparation_succeeded"] is True
    assert result["subprocess_launched"] is True
    assert result["execution_started"] is True
    assert result["subprocess_finished"] is False


def test_console_script_supports_windows_base_and_recorded_user_layout(tmp_path, monkeypatch):
    script = tmp_path / ("wt-import.exe" if sys.platform == "win32" else "wt-import")
    script.touch()

    class Dist:
        files = [script]

        def locate_file(self, path):
            return path

    monkeypatch.setattr(runner.sysconfig, "get_path", lambda _: str(tmp_path / "other"))
    assert runner.console_script(Dist()) == script


@pytest.mark.parametrize("failure", [ImportError("CLI missing"), ValueError("incompatible")])
def test_precheck_never_installs_or_runs_tests(tmp_path, monkeypatch, failure):
    def missing(*_):
        raise failure

    def forbidden(*args, **kwargs):
        pytest.fail("Precheck must not install or run anything")

    monkeypatch.setattr(runner, "prepare", missing)
    monkeypatch.setattr(runner.subprocess, "run", forbidden)
    with pytest.raises(type(failure)):
        runner.run_check(tmp_path, [], [])


def test_inaccessible_project_never_substituted(tmp_path):
    with pytest.raises(ValueError, match="not accessible"):
        runner.run_check(tmp_path / "remote-machine", [], [])


@pytest.mark.parametrize(
    "mode,code,status",
    [
        ("config", 0, "pass"),
        ("explicit", 0, "pass"),
        ("failure", 1, "pass"),
        ("unknown", 2, "unknown"),
        ("wrong", 1, "fail"),
    ],
)
def test_independent_skill_executes_real_console(tmp_path, mode, code, status):
    import shutil

    skill = tmp_path / "独立 skill"
    shutil.copytree(SCRIPT.parents[1], skill, ignore=shutil.ignore_patterns("__pycache__"))
    project = tmp_path / "项目 space"
    project.mkdir()
    (project / "pkg").mkdir()
    (project / "pkg/__init__.py").write_text("VALUE=42\n", encoding="utf-8")
    body = "def test_value():\n    import pkg\n    assert pkg.VALUE == 42\n"
    if mode == "failure":
        body = body.replace("== 42", "== 0")
    if mode == "unknown":
        body = "def test_no_import():\n    assert True\n"
    (project / "test_sample.py").write_text(body, encoding="utf-8")
    (project / "other").mkdir()
    (project / ".wt-import.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "expect": {"pkg": "other" if mode in {"explicit", "wrong"} else "pkg"},
            }
        ),
        encoding="utf-8",
    )
    alias = Path(sys.executable).parent / "python3"
    selected = str(alias) if sys.platform != "win32" and alias.exists() else sys.executable
    command = [selected, str(skill / "scripts/run_check.py"), "--cwd", str(project)]
    if mode == "explicit":
        command += ["--expect", "pkg=pkg"]
    result = subprocess.run(
        [*command, "--", "-q"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert result.returncode == code, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["result"] == "usable_report", data
    assert data["source_status"] == status
    report = json.loads(Path(data["report_path"]).read_text(encoding="utf-8"))
    assert report["guard"]["status"] == status
    if mode == "failure":
        assert report["pytest"]["exit_code"] == 1
