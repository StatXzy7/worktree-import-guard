from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

import pytest


def test_demo_subprocess_handles_non_ascii_with_legacy_encoding(tmp_path: Path) -> None:
    demo = runpy.run_path(str(Path(__file__).parents[2] / "examples/cross-worktree-demo/run.py"))
    env = {**os.environ, "PYTHONIOENCODING": "gbk", "PYTHONUTF8": "0"}
    result = demo["run"]([sys.executable, "-c", "print(chr(0x4e2d))"], cwd=tmp_path, env=env)
    assert result.stdout.strip() == "中"
    assert env["PYTHONIOENCODING"] == "gbk"
    with pytest.raises(RuntimeError, match="expected exit 0, got 1"):
        demo["run"]([sys.executable, "-c", "raise SystemExit(1)"], cwd=tmp_path)
