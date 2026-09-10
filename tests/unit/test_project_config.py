import json

import pytest

from worktree_import_guard.contracts import ContractError, parse_contracts
from worktree_import_guard.project_config import (
    CONFIG_NAME,
    config_data,
    find_config,
    load_config,
    save_config,
    validate_config,
)


def test_nearest_config_stops_at_worktree_and_non_git_project(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    (parent / CONFIG_NAME).write_text("{}", encoding="utf-8")
    project = parent / "worktree"
    project.mkdir()
    (project / ".git").write_text("gitdir: unused", encoding="utf-8")
    sub = project / "sub"
    sub.mkdir()
    assert find_config(sub) is None
    (project / CONFIG_NAME).write_text("{}", encoding="utf-8")
    assert find_config(sub) == project / CONFIG_NAME
    (sub / CONFIG_NAME).write_text("{}", encoding="utf-8")
    assert find_config(sub) == sub / CONFIG_NAME
    other = parent / "non_git"
    other.mkdir()
    assert find_config(other) is None


@pytest.mark.parametrize(
    "data",
    [
        {},
        [],
        {"schema_version": True, "expect": {"p": "p"}},
        {"schema_version": 2, "expect": {"p": "p"}},
        {"schema_version": 1, "expect": {}},
        {"schema_version": 1, "expect": []},
        {"schema_version": 1, "expect": {"p": None}},
        {"schema_version": 1, "expect": {"p": "../outside"}},
        {"schema_version": 1, "expect": {"p": "C:\\absolute"}},
        {"schema_version": 1, "expect": {"p": "/absolute"}},
        {"schema_version": 1, "expect": {"bad-name": "p"}},
        {"schema_version": 1, "expect": {"p": "p"}, "command": "oops"},
    ],
)
def test_invalid_configuration_is_an_error(tmp_path, data):
    with pytest.raises(ContractError):
        validate_config(data, tmp_path)


@pytest.mark.parametrize("text", ["{", '{"schema_version":1,"expect":{"p":"p","p":"q"}}'])
def test_broken_or_duplicate_json(tmp_path, text):
    path = tmp_path / CONFIG_NAME
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ContractError):
        load_config(path)


def test_utf8_save_roundtrip_and_no_overwrite(tmp_path):
    contracts = parse_contracts(["pkg=中文 目录/pkg"], tmp_path)
    data = config_data(contracts, tmp_path)
    path = save_config(tmp_path, data)
    assert "中文" in path.read_text(encoding="utf-8")
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert load_config(path) == contracts
    with pytest.raises(ContractError, match="never overwritten"):
        save_config(tmp_path, data)
    assert json.loads(path.read_text(encoding="utf-8")) == data


def test_symlink_config_and_external_target_are_refused(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    external = tmp_path / "outside.json"
    external.write_text("{}", encoding="utf-8")
    link = project / CONFIG_NAME
    try:
        link.symlink_to(external)
        (project / "pkg").symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("symlink unavailable")
    for action in (
        lambda: find_config(project),
        lambda: load_config(link),
        lambda: save_config(project, {"schema_version": 1, "expect": {"p": "p"}}),
        lambda: validate_config({"schema_version": 1, "expect": {"p": "pkg"}}, project),
    ):
        with pytest.raises(ContractError):
            action()
    assert external.read_text(encoding="utf-8") == "{}"


def test_relative_paths_use_config_directory(tmp_path):
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "tests"
    sub.mkdir()
    path = save_config(tmp_path, {"schema_version": 1, "expect": {"pkg": "src/pkg"}})
    assert load_config(find_config(sub))[0].expected_root == (tmp_path / "src/pkg").resolve()
    assert path.name == CONFIG_NAME
