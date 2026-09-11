"""Deterministic preflight helper checks."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = ROOT / "skills/verify-worktree-imports/scripts/preflight.py"


def run_preflight(cwd: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--cwd", str(cwd)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_preflight_needs_selection_without_config(tmp_path):
    data = run_preflight(tmp_path)
    assert data["status"] == "needs_selection"
    assert any(item["code"] == "TARGET_SELECTION_REQUIRED" for item in data["problem_details"])


def test_preflight_ready_with_saved_config(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/__init__.py").write_text("X=1\n", encoding="utf-8")
    (tmp_path / ".wt-import.json").write_text(
        json.dumps({"schema_version": 1, "expect": {"pkg": "pkg"}}),
        encoding="utf-8",
    )
    data = run_preflight(tmp_path)
    assert data["status"] == "ready"
    assert data["targets"]


def test_preflight_config_invalid(tmp_path):
    (tmp_path / ".wt-import.json").write_text("{", encoding="utf-8")
    data = run_preflight(tmp_path)
    assert data["status"] == "missing_conditions"
    assert any(item["code"] == "CONFIG_INVALID" for item in data["problem_details"])


def test_preflight_project_not_accessible(tmp_path):
    data = run_preflight(tmp_path / "missing")
    assert data["status"] == "missing_conditions"
    assert data["problem_details"][0]["code"] == "PROJECT_NOT_ACCESSIBLE"
