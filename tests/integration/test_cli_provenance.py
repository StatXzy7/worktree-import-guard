from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import write_package, write_test
from worktree_import_guard.origins import canonicalize_path

pytestmark = pytest.mark.integration


def target(report: dict) -> dict:
    return report["targets"][0]


def test_correct_origin_passes_and_json_is_stable(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "demo_pkg")
    write_test(tmp_path, "import demo_pkg\n\ndef test_value():\n    assert demo_pkg.VALUE == 42\n")
    result = run_guard(tmp_path, "--expect", "demo_pkg=demo_pkg", "--", "-q")
    assert result.completed.returncode == 0, result.completed.stdout + result.completed.stderr
    assert result.report["pytest"]["exit_code"] == 0
    assert result.report["guard"] == {
        "complete": True,
        "observation_complete": True,
        "status": "pass",
    }
    assert target(result.report)["reasons"] == ["MATCH"]
    assert result.report["scope"]["child_process_imports"] is False
    assert result.report["run"]["python"] == sys.executable
    assert result.report["run"]["sys_prefix"] == sys.prefix
    assert result.report["run"]["sys_base_prefix"] == sys.base_prefix
    assert result.report["run"]["python_version"]
    assert result.report["run"]["pytest_version"]


def test_unobserved_target_is_unknown(tmp_path: Path, run_guard) -> None:
    write_test(tmp_path, "def test_value():\n    assert 42 == 42\n")
    result = run_guard(tmp_path, "--expect", "missing_pkg=missing_pkg", "--", "-q")
    assert result.completed.returncode == 2
    assert result.report["pytest"]["exit_code"] == 0
    assert target(result.report)["status"] == "unknown"
    assert target(result.report)["reasons"] == ["TARGET_NOT_OBSERVED"]


def test_external_origin_and_similar_prefix_fail(tmp_path: Path, run_guard) -> None:
    actual = write_package(tmp_path, "acme_other")
    write_test(
        tmp_path,
        """\
import importlib.util
import sys
from pathlib import Path

path = Path(__file__).parent / "acme_other" / "__init__.py"
spec = importlib.util.spec_from_file_location("acme", path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules["acme"] = module
spec.loader.exec_module(module)

def test_value():
    assert module.VALUE == 42
""",
    )
    result = run_guard(tmp_path, "--expect", "acme=acme", "--", "-q")
    assert result.completed.returncode == 1
    assert target(result.report)["reasons"] == ["OUTSIDE_EXPECTED_ROOT"]
    origin = target(result.report)["observations"][0]["canonical_origin"]
    assert str(canonicalize_path(actual)) in origin


def test_transient_import_removed_from_sys_modules_is_retained(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "transient_pkg")
    write_test(
        tmp_path,
        """\
import sys
import transient_pkg

VALUE = transient_pkg.VALUE
sys.modules.pop("transient_pkg")

def test_value():
    assert VALUE == 42
""",
    )
    result = run_guard(tmp_path, "--expect", "transient_pkg=transient_pkg", "--", "-q")
    assert result.completed.returncode == 0, result.completed.stdout + result.completed.stderr
    assert target(result.report)["status"] == "pass"
    assert target(result.report)["observations"]


def test_transient_import_inside_test_call_is_retained(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "call_pkg")
    write_test(
        tmp_path,
        """\
def test_value():
    import sys
    import call_pkg

    assert call_pkg.VALUE == 42
    sys.modules.pop("call_pkg")
""",
    )
    result = run_guard(tmp_path, "--expect", "call_pkg=call_pkg", "--", "-q")
    assert result.completed.returncode == 0, result.completed.stdout + result.completed.stderr
    assert target(result.report)["status"] == "pass"
    assert target(result.report)["observations"]


def test_mixed_package_and_submodule_origins_fail(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "mixed_pkg")
    external = tmp_path / "external"
    external.mkdir()
    (external / "foreign.py").write_text("FOREIGN = True\n", encoding="utf-8")
    write_test(
        tmp_path,
        """\
import importlib.util
import sys
from pathlib import Path
import mixed_pkg

path = Path(__file__).parent / "external" / "foreign.py"
spec = importlib.util.spec_from_file_location("mixed_pkg.foreign", path)
assert spec is not None and spec.loader is not None
foreign = importlib.util.module_from_spec(spec)
sys.modules["mixed_pkg.foreign"] = foreign
spec.loader.exec_module(foreign)

def test_value():
    assert mixed_pkg.VALUE == 42 and foreign.FOREIGN
""",
    )
    result = run_guard(tmp_path, "--expect", "mixed_pkg=mixed_pkg", "--", "-q")
    assert result.completed.returncode == 1
    assert target(result.report)["reasons"] == ["MIXED_ORIGINS"]
    origins = target(result.report)["observations"]
    assert any(
        item["canonical_origin"] and "external" in item["canonical_origin"] for item in origins
    )
    assert any(
        item["canonical_origin"] and "mixed_pkg" in item["canonical_origin"] for item in origins
    )


def test_pytest_failure_and_native_exit_codes_are_preserved(
    tmp_path: Path, run_guard, test_runner_command: list[str], guard_command: list[str]
) -> None:
    write_package(tmp_path, "failure_pkg")
    write_test(tmp_path, "import failure_pkg\n\ndef test_failure():\n    assert False\n")
    failed = run_guard(tmp_path, "--expect", "failure_pkg=failure_pkg", "--", "-q")
    assert failed.completed.returncode == 1
    assert failed.report["pytest"]["exit_code"] == 1
    assert failed.report["guard"]["status"] == "pass"

    empty = tmp_path / "empty"
    empty.mkdir()
    no_tests = run_guard(empty, "--expect", "missing_pkg=missing_pkg", "--", "-q")
    assert no_tests.completed.returncode == 5
    assert no_tests.report["pytest"]["exit_code"] == 5

    usage = run_guard(tmp_path, "--expect", "failure_pkg=failure_pkg", "--", "--bad-option")
    assert usage.completed.returncode == 4
    assert usage.report["pytest"]["exit_code"] == 4

    # Exercise newer native states only on versions that actually define them.
    if hasattr(pytest.ExitCode, "MAX_WARNINGS_ERROR"):
        write_test(
            tmp_path,
            "import failure_pkg\nimport warnings\n\ndef test_warning():\n"
            "    warnings.warn('native warning threshold', UserWarning)\n",
        )
        args = ["--max-warnings=0", "-q"]
        native = subprocess.run(
            [*test_runner_command, *args], cwd=tmp_path, capture_output=True, text=True
        )
        assert native.returncode == int(pytest.ExitCode.MAX_WARNINGS_ERROR)
        guarded = run_guard(tmp_path, "--expect", "failure_pkg=failure_pkg", "--", *args)
        assert guarded.completed.returncode == native.returncode
        assert guarded.report["pytest"]["exit_code"] == native.returncode
        assert guarded.report["guard"]["status"] == "pass"
        report_failure = subprocess.run(
            [*guard_command, "--expect", "failure_pkg=failure_pkg",
             "--report-json", str(tmp_path), "--", *args],
            cwd=tmp_path, capture_output=True, text=True,
        )
        assert report_failure.returncode == native.returncode
        assert "could not write JSON report" in report_failure.stderr


def test_pytest_keyboard_interrupt_exit_is_preserved(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "interrupt_pkg")
    write_test(
        tmp_path,
        "import interrupt_pkg\n\ndef test_interrupt():\n    raise KeyboardInterrupt\n",
    )
    interrupted = run_guard(tmp_path, "--expect", "interrupt_pkg=interrupt_pkg", "--", "-q")
    assert interrupted.completed.returncode == 2
    assert interrupted.report["pytest"]["exit_code"] == 2
    assert interrupted.report["guard"] == {
        "complete": True,
        "observation_complete": True,
        "status": "pass",
    }


def test_spaces_and_no_git_context(tmp_path: Path, run_guard) -> None:
    project = tmp_path / "project with spaces"
    project.mkdir()
    write_package(project, "space_pkg")
    write_test(project, "import space_pkg\n\ndef test_value():\n    assert space_pkg.VALUE == 42\n")
    passed = run_guard(
        project,
        "--no-git-context",
        "--expect",
        "space_pkg=space_pkg",
        "--",
        "-q",
    )
    assert passed.completed.returncode == 0
    assert passed.report["git"]["available"] is False

    failed = run_guard(
        project,
        "--no-git-context",
        "--expect",
        "space_pkg=some other/space_pkg",
        "--",
        "-q",
    )
    assert failed.completed.returncode == 1
    assert target(failed.report)["reasons"] == ["OUTSIDE_EXPECTED_ROOT"]


def test_namespace_ambiguity_is_unknown(tmp_path: Path, run_guard) -> None:
    one = tmp_path / "namespace one"
    two = tmp_path / "namespace two"
    (one / "ns_pkg").mkdir(parents=True)
    (two / "ns_pkg").mkdir(parents=True)
    (one / "ns_pkg/one.py").write_text("VALUE = 1\n", encoding="utf-8")
    (two / "ns_pkg/two.py").write_text("VALUE = 2\n", encoding="utf-8")
    (tmp_path / "conftest.py").write_text(
        f"import sys\nsys.path[:0] = [{str(one)!r}, {str(two)!r}]\n",
        encoding="utf-8",
    )
    write_test(tmp_path, "import ns_pkg\n\ndef test_namespace():\n    assert ns_pkg is not None\n")
    result = run_guard(tmp_path, "--expect", f"ns_pkg={one / 'ns_pkg'}", "--", "-q")
    assert result.completed.returncode == 2
    assert target(result.report)["reasons"] == ["UNSUPPORTED_NAMESPACE_LAYOUT"]


def test_metadata_conflict_is_unknown(tmp_path: Path, run_guard) -> None:
    write_package(tmp_path, "conflict_pkg")
    write_test(
        tmp_path,
        """\
from pathlib import Path
import conflict_pkg

conflict_pkg.__file__ = str(Path(__file__).parent / "other" / "__init__.py")

def test_value():
    assert conflict_pkg.VALUE == 42
""",
    )
    result = run_guard(tmp_path, "--expect", "conflict_pkg=conflict_pkg", "--", "-q")
    assert result.completed.returncode == 2
    assert target(result.report)["reasons"] == ["ORIGIN_METADATA_CONFLICT"]


def test_malformed_and_duplicate_contracts_are_cli_errors(tmp_path: Path, run_guard) -> None:
    malformed = run_guard(tmp_path, "--expect", "not-a-contract", "--", "-q", report=False)
    assert malformed.completed.returncode == 2
    assert "expected PACKAGE=PATH" in malformed.completed.stderr

    duplicate = run_guard(
        tmp_path,
        "--expect",
        "pkg=one",
        "--expect",
        "pkg=two",
        "--",
        "-q",
        report=False,
    )
    assert duplicate.completed.returncode == 2
    assert "duplicate expectation" in duplicate.completed.stderr


def test_json_write_failure_does_not_mask_native_pytest_exit(
    tmp_path: Path, guard_command: list[str]
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    completed = subprocess.run(
        [
            *guard_command,
            "--report-json",
            str(empty),
            "--expect",
            "missing_pkg=missing_pkg",
            "--",
            "-q",
        ],
        cwd=empty,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 5
    assert "could not write JSON report" in completed.stderr
