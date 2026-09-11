"""README public-entry consistency checks without network installs."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYPI_INSTALL = "worktree-import-guard==0.1.2"


@pytest.mark.parametrize("name", ["README.md", "README.zh-CN.md"])
def test_public_readme_quickstart_uses_pypi_release(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    quickstart = text.split("## Install into your existing test environment", 1)[0]
    quickstart = quickstart.split("## 安装到已有测试环境", 1)[0]
    assert PYPI_INSTALL in quickstart
    assert "--setup" in quickstart
    assert "--doctor" in quickstart


@pytest.mark.parametrize("name", ["README.md", "README.zh-CN.md"])
def test_public_readme_avoids_bare_wt_import_in_quickstart(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    quickstart = text.split("## Install into your existing test environment", 1)[0]
    quickstart = quickstart.split("## 安装到已有测试环境", 1)[0]
    commands = re.findall(r"```(?:sh|powershell)\n(.*?)```", quickstart, flags=re.S)
    for block in commands:
        sanitized = block.replace(".venv/bin/wt-import", "").replace(
            ".venv\\Scripts\\wt-import.exe", ""
        )
        assert not re.search(r"(?<![/\w-])wt-import(?![/\w-])", sanitized)


@pytest.mark.parametrize("name", ["README.md", "README.zh-CN.md"])
def test_public_readme_documents_pypi_not_source_preview(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert PYPI_INSTALL in text
    assert "PyPI" in text or "pypi" in text.lower()
    assert "git+https://github.com/StatXzy7/worktree-import-guard.git@" not in text.split(
        "## Explicit checks", 1
    )[0]
