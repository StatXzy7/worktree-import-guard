import sys

import pytest

from worktree_import_guard import onboarding
from worktree_import_guard.contracts import ContractError
from worktree_import_guard.project_config import CONFIG_NAME


def package(path):
    path.mkdir(parents=True)
    (path / "__init__.py").write_text("raise AssertionError('do not import')", encoding="utf-8")


def answers(monkeypatch, values):
    iterator = iter(values)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: next(iterator))


@pytest.mark.parametrize("layout", ["src", "."])
def test_confirm_save_without_importing(monkeypatch, tmp_path, layout):
    package(tmp_path / layout / "pkg")
    package(tmp_path / "tests")
    package(tmp_path / ".venv")
    answers(monkeypatch, ["y", "1", "yes"])
    contracts = onboarding.setup(tmp_path)
    assert len(contracts) == 1 and contracts[0].package == "pkg"
    assert (tmp_path / CONFIG_NAME).is_file()


@pytest.mark.parametrize("inputs", [["n"], ["y", "1", "n"]])
def test_declining_does_not_write(monkeypatch, tmp_path, inputs):
    package(tmp_path / "pkg")
    answers(monkeypatch, inputs)
    assert onboarding.setup(tmp_path) is None
    assert not (tmp_path / CONFIG_NAME).exists()


@pytest.mark.parametrize("selection", ["", "0", "3", "one", "1,1"])
def test_invalid_or_duplicate_selection(monkeypatch, tmp_path, selection):
    package(tmp_path / "pkg")
    answers(monkeypatch, ["y", selection])
    with pytest.raises(ContractError):
        onboarding.setup(tmp_path)


def test_namespace_requires_explicit_mapping(monkeypatch, tmp_path):
    (tmp_path / "src/ns/pkg").mkdir(parents=True)
    assert not onboarding.candidates(tmp_path)
    answers(monkeypatch, ["y", "ns.pkg=src/ns/pkg", "y"])
    assert onboarding.setup(tmp_path)[0].package == "ns.pkg"


def test_no_tty_missing_pytest_existing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ContractError, match="interactive"):
        onboarding.setup(tmp_path)
    answers(monkeypatch, [])
    monkeypatch.setattr(onboarding, "pytest_available", lambda: False)
    with pytest.raises(ContractError, match="pytest"):
        onboarding.setup(tmp_path)
    monkeypatch.setattr(onboarding, "pytest_available", lambda: True)
    (tmp_path / CONFIG_NAME).write_text("{}", encoding="utf-8")
    with pytest.raises(ContractError, match="already exists"):
        onboarding.setup(tmp_path)


@pytest.mark.parametrize("version", ["8.2.0", "9.1.1", "7.4.0", "10.0.0", "bad"])
def test_pytest_version_check(monkeypatch, version):
    monkeypatch.setattr(onboarding, "version", lambda name: version)
    assert onboarding.pytest_available() == (version in {"8.2.0", "9.1.1"})


def test_interrupt_does_not_start_tests(monkeypatch, tmp_path):
    answers(monkeypatch, [])

    def interrupted(prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrupted)
    assert onboarding.setup(tmp_path) is None


def test_multiple_candidates_require_selection(monkeypatch, tmp_path):
    package(tmp_path / "one")
    package(tmp_path / "two")
    answers(monkeypatch, ["y", "2", "y"])
    assert [c.package for c in onboarding.setup(tmp_path)] == ["two"]


def test_alternate_environment_is_only_a_suggestion(monkeypatch, tmp_path, capsys):
    executable = tmp_path / ".venv" / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    executable.parent.mkdir(parents=True)
    executable.write_text("not executed", encoding="utf-8")
    answers(monkeypatch, ["n"])
    assert onboarding.setup(tmp_path) is None
    text = capsys.readouterr().out
    assert str(executable) in text and "show" in text and "README installation" in text


def test_external_link_is_not_a_candidate(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    package(outside / "pkg")
    try:
        (project / "src").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink unavailable")
    assert not onboarding.candidates(project)


def test_missing_directory_cannot_be_saved(monkeypatch, tmp_path):
    answers(monkeypatch, ["y", "pkg=missing"])
    with pytest.raises(ContractError, match="existing source"):
        onboarding.setup(tmp_path)
    assert not (tmp_path / CONFIG_NAME).exists()
