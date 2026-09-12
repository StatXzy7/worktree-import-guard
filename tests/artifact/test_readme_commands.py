"""README public-entry consistency checks without network installs."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYPI_INSTALL = "worktree-import-guard==0.1.2"
CURRENT_DASH = "fixed-source preview"


@pytest.mark.parametrize("name", ["docs/skill-quickstart.md", "docs/pytest-workflow.md"])
def test_active_docs_do_not_describe_source_preview(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert "0.1.0 source preview" not in text
    assert CURRENT_DASH not in text


@pytest.mark.parametrize("name, has_release", [
    ("docs/skill-quickstart.md", True),
    ("docs/pytest-workflow.md", False),
])
def test_active_docs_show_pypi_release_and_reuse_saved_config(name: str, has_release: bool) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    if has_release:
        assert PYPI_INSTALL in text
    assert "wt-import --setup" in text
    if name == "docs/skill-quickstart.md":
        assert "wt-import --doctor" in text


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


@pytest.mark.parametrize("name", ["docs/first-use.md"])
def test_active_first_use_docs_references_current_release(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert "0.1.2" in text
    assert "--doctor" in text
