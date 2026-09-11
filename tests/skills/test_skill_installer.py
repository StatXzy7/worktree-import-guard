import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "skills/verify-worktree-imports/scripts/install_skill.py"


def test_installer_copies_resources_without_overwriting(tmp_path: Path) -> None:
    project = tmp_path / "project with spaces"
    project.mkdir()
    first = subprocess.run(
        [sys.executable, str(INSTALLER), str(project)], capture_output=True, text=True
    )
    assert first.returncode == 0, first.stderr
    installed = project / ".agents/skills/verify-worktree-imports"
    assert (installed / "SKILL.md").is_file()
    assert (installed / "scripts/run_check.py").is_file()

    second = subprocess.run(
        [sys.executable, str(INSTALLER), str(project)], capture_output=True, text=True
    )
    assert second.returncode != 0
    assert "refusing to overwrite" in second.stderr
