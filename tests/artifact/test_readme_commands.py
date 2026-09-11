"""README public-entry consistency checks without network installs."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PREVIEW_COMMIT = "edae3e6fa9a0b065385a080c371c9c17728b4656"
INSTALL_PATTERN = re.compile(
    r"git\+https://github\.com/StatXzy7/worktree-import-guard\.git@([a-f0-9]{40})"
)


@pytest.mark.parametrize("name", ["README.md", "README.zh-CN.md"])
def test_public_readme_pins_one_verified_preview(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    commits = set(INSTALL_PATTERN.findall(text))
    assert commits == {PREVIEW_COMMIT}


@pytest.mark.parametrize("name", ["README.md", "README.zh-CN.md"])
def test_public_readme_quickstart_uses_setup_not_doctor(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    quickstart = text.split("## Install into your existing test environment", 1)[0]
    quickstart = quickstart.split("## 安装到已有测试环境", 1)[0]
    assert "--setup" in quickstart
    assert "--doctor" not in quickstart


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
def test_public_readme_documents_candidate_doctor_separately(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert "0.1.1" in text and "--doctor" in text
    assert "candidate-quickstart" in text
