"""Deterministic runner checks are not claims about model instruction following."""

import copy
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


def envelope(report):
    return {
        "runtime": {k: v for k, v in report["run"].items()
                    if k not in {"cwd", "pytest_args", "pytest_version"}},
        "cwd": report["run"]["cwd"], "pytest_args": report["run"]["pytest_args"],
        "tool": report["tool"],
        "targets": [{"package": t["package"], "expected_root": t["expected_root"]}
                    for t in report["targets"]],
        "process_exit_code": report["pytest"]["exit_code"] or
        {"pass": 0, "fail": 1, "unknown": 2}[report["guard"]["status"]],
    }


@pytest.mark.parametrize("path", sorted((ROOT / "tests/golden").glob("schema-v2-*.json")))
def test_engine_golden_reports_are_preserved(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    original = copy.deepcopy(report)
    assert runner.validate(report, envelope(report)) == original
    report["metrics"]["future_counter"] = 10
    assert runner.validate(report, envelope(report)) == report


@pytest.mark.parametrize("change", [
    lambda r: r.update(schema_version=3),
    lambda r: r.update(schema_version=True),
    lambda r: r["guard"].update(status="green"),
    lambda r: r["guard"].update(complete=False),
    lambda r: r["guard"].update(observation_complete=False),
    lambda r: r["run"].update(sys_prefix="other venv"),
    lambda r: r["run"].update(python="other python"),
    lambda r: r["run"].update(cwd="other machine"),
    lambda r: r["run"].update(pytest_args=["different.py"]),
    lambda r: r["targets"][0].update(expected_root="other source"),
    lambda r: r["targets"][0].update(status="unknown"),
    lambda r: r["pytest"].update(exit_code=True),
    lambda r: r["tool"].update(version="999"),
])
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


@pytest.mark.parametrize("payload", [None, "{bad", '{"schema_version":99}'])
def test_fresh_report_missing_or_damaged_never_uses_old_pass(tmp_path, monkeypatch, payload):
    old = tmp_path / "report.json"
    old.write_text('{"guard":{"status":"pass"}}', encoding="utf-8")
    package = tmp_path / "pkg"
    package.mkdir()
    from worktree_import_guard.contracts import parse_contracts
    monkeypatch.setattr(runner, "prepare", lambda *_: (
        Path("wt-import"), parse_contracts(["pkg=pkg"], tmp_path), {"version": "0.1.1"}
    ))
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
    assert result["result"] == "unusable_report"
    assert calls[0][0][-1] == "; echo do not execute"
    assert calls[0][1]["stdin"] == subprocess.DEVNULL
    assert "shell" not in calls[0][1]
    assert json.loads(old.read_text(encoding="utf-8"))["guard"]["status"] == "pass"


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


@pytest.mark.parametrize("mode,code,status", [
    ("config", 0, "pass"), ("explicit", 0, "pass"), ("failure", 1, "pass"),
    ("unknown", 2, "unknown"), ("wrong", 1, "fail"),
])
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
    (project / ".wt-import.json").write_text(json.dumps({
        "schema_version": 1, "expect": {"pkg": "other" if mode in {"explicit", "wrong"}
                                       else "pkg"},
    }), encoding="utf-8")
    command = [sys.executable, str(skill / "scripts/run_check.py"), "--cwd", str(project)]
    if mode == "explicit":
        command += ["--expect", "pkg=pkg"]
    result = subprocess.run([*command, "--", "-q"], capture_output=True, text=True,
                            encoding="utf-8", timeout=120, check=False)
    assert result.returncode == code, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["result"] == "usable_report", data
    assert data["source_status"] == status
    report = json.loads(Path(data["report_path"]).read_text(encoding="utf-8"))
    assert report["guard"]["status"] == status
    if mode == "failure":
        assert report["pytest"]["exit_code"] == 1
