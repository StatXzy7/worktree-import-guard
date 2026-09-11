"""Copy this Skill into a project's local .agents/skills directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the local verify-worktree-imports Skill")
    parser.add_argument("project", type=Path, help="project directory receiving .agents/skills")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    destination = args.project.resolve() / ".agents" / "skills" / source.name
    if destination.exists():
        parser.error(f"refusing to overwrite existing Skill: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
    print(f"Installed Skill at {destination}")
    print("This copied files only; it did not install Python packages or change the environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
