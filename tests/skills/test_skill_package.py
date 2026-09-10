"""Check distributable resources, without claiming that static checks test an agent."""

import shutil
import subprocess
import sys
import zipfile


def test_skill_only_archive_runs_outside_repository(tmp_path, project_root):
    source = project_root / "skills/verify-worktree-imports"
    archive = tmp_path / "skill.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for path in source.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                bundle.write(path, path.relative_to(source.parent))
    destination = tmp_path / "consumer"
    shutil.unpack_archive(archive, destination)
    skill = destination / source.name
    assert (skill / "LICENSE.txt").read_text(encoding="utf-8") == (
        project_root / "LICENSE"
    ).read_text(encoding="utf-8")
    assert (skill / "references/workflow.md").is_file()
    assert (skill / "references/report-v2.md").is_file()
    result = subprocess.run([sys.executable, str(skill / "scripts/run_check.py"), "--help"],
                            cwd=destination, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
