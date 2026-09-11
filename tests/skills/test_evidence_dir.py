"""Evidence directory boundary checks for run_check."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/verify-worktree-imports/scripts/run_check.py"
spec = importlib.util.spec_from_file_location("skill_runner_evidence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.mark.skipif(not hasattr(Path, "symlink_to"), reason="symlinks unavailable")
def test_evidence_dir_symlink_rejected_before_resolve(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        runner.run_check(tmp_path, ["missing=missing"], [], evidence_dir=link)
