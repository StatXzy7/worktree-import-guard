import json
import sys

import pytest

from tests.unit.test_first_setup import answers, package
from worktree_import_guard.contracts import ContractError
from worktree_import_guard.onboarding import doctor, setup
from worktree_import_guard.project_config import CONFIG_NAME


def test_doctor_without_config_runs_setup_wizard(monkeypatch, tmp_path):
    package(tmp_path / "pkg")
    answers(monkeypatch, ["y", "1", "yes"])
    contracts = doctor(tmp_path)
    assert len(contracts) == 1
    assert (tmp_path / CONFIG_NAME).is_file()


def test_doctor_reuses_existing_config_without_rewrite(monkeypatch, tmp_path):
    package(tmp_path / "pkg")
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 1, "expect": {"pkg": "pkg"}}),
        encoding="utf-8",
    )
    answers(monkeypatch, ["y"])
    contracts = doctor(tmp_path)
    assert contracts[0].package == "pkg"
    assert json.loads((tmp_path / CONFIG_NAME).read_text(encoding="utf-8"))["expect"] == {
        "pkg": "pkg"
    }


def test_doctor_cancelled_does_not_run_tests(monkeypatch, tmp_path):
    package(tmp_path / "pkg")
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 1, "expect": {"pkg": "pkg"}}),
        encoding="utf-8",
    )
    answers(monkeypatch, ["n"])
    assert doctor(tmp_path) is None


def test_doctor_reports_broken_config(monkeypatch, tmp_path, capsys):
    (tmp_path / CONFIG_NAME).write_text("{", encoding="utf-8")
    answers(monkeypatch, [])
    with pytest.raises(ContractError, match="saved settings cannot be used"):
        doctor(tmp_path)
    assert str(tmp_path / CONFIG_NAME) in capsys.readouterr().out


def test_doctor_noninteractive_error(monkeypatch, tmp_path):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(ContractError, match="interactive"):
        doctor(tmp_path)


def test_setup_still_refuses_existing_config(monkeypatch, tmp_path):
    (tmp_path / CONFIG_NAME).write_text("{}", encoding="utf-8")
    answers(monkeypatch, [])
    with pytest.raises(ContractError, match="already exists"):
        setup(tmp_path)


def test_doctor_cancelled_on_eof(monkeypatch, tmp_path):
    package(tmp_path / "pkg")
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 1, "expect": {"pkg": "pkg"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: (_ for _ in ()).throw(EOFError))
    assert doctor(tmp_path) is None


def test_doctor_cancelled_on_keyboard_interrupt(monkeypatch, tmp_path):
    package(tmp_path / "pkg")
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 1, "expect": {"pkg": "pkg"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: (_ for _ in ()).throw(KeyboardInterrupt))
    assert doctor(tmp_path) is None


def test_doctor_shows_bound_next_check_command(monkeypatch, tmp_path, capsys):
    package(tmp_path / "pkg")
    (tmp_path / CONFIG_NAME).write_text(
        json.dumps({"schema_version": 1, "expect": {"pkg": "pkg"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    script = str(tmp_path / "My Project" / "wt-import.exe")
    monkeypatch.setattr("worktree_import_guard.onboarding.console_script", lambda *_: script)
    monkeypatch.setattr(
        "worktree_import_guard.onboarding.distribution",
        lambda name: None
    )
    monkeypatch.setattr(
        "worktree_import_guard.onboarding.command_for_path",
        lambda _script, _args: f"\"{script}\" -- -q",
    )
    answers(monkeypatch, ["y"])
    assert doctor(tmp_path) is not None
    assert f'Next time: "{script}" -- -q' in capsys.readouterr().out
