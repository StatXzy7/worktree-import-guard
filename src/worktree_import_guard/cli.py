"""Command-line entry point for one-process pytest provenance checking."""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .contracts import ContractError, parse_contracts
from .git_worktrees import discover_git_context
from .models import ReasonCode, RunReport, Status
from .observer import ImportObserver
from .pytest_plugin import GuardPytestPlugin
from .report import classify, render_human, write_json_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wt-import",
        description="Catch Python tests that pass against the wrong Git worktree.",
        usage="wt-import [OPTIONS] -- [PYTEST_ARGS...]",
        epilog=(
            "Run in your project directory using its pytest environment. "
            "Example (src layout): wt-import --expect demo_pkg=src/demo_pkg -- -q. "
            "Flat layout: --expect demo_pkg=demo_pkg. "
            "Use the import name and source package directory, not the repository root. "
            "The guard checks imports; it does not fix your environment."
        ),
    )
    parser.add_argument(
        "-e",
        "--expect",
        action="append",
        dest="expectations",
        metavar="PACKAGE=PATH",
        help="package import name=expected source package directory; required, repeatable",
    )
    parser.add_argument(
        "-C",
        "--cwd",
        default=".",
        metavar="PATH",
        help="pytest working directory; relative expected paths start here",
    )
    parser.add_argument(
        "--report-json",
        metavar="PATH",
        help="write JSON; relative path starts in the directory where you invoked wt-import",
    )
    parser.add_argument(
        "--no-git-context",
        action="store_true",
        help="disable Git worktree discovery",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="show matching module origins as well as failures and unknowns",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parser


def composite_exit_code(pytest_exit_code: int, guard_status: Status) -> int:
    """Combine results without disguising native pytest conditions."""

    if pytest_exit_code in {1, 2, 3, 4, 5}:
        return pytest_exit_code
    if pytest_exit_code != 0:
        return pytest_exit_code
    return {Status.PASS: 0, Status.FAIL: 1, Status.UNKNOWN: 2}[guard_status]


def report_write_failure_exit_code(pytest_exit_code: int) -> int:
    """Surface report failure without overwriting an existing pytest failure."""

    return pytest_exit_code if pytest_exit_code != 0 else 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run pytest in this executable's interpreter and evaluate provenance."""

    parser = _parser()
    options = parser.parse_args(argv)
    if not options.expectations:
        parser.error(
            "at least one --expect PACKAGE=PATH is required; "
            "try --expect demo_pkg=src/demo_pkg -- -q (use your package name and directory)"
        )

    invocation_cwd = Path.cwd()
    pytest_cwd = Path(options.cwd).expanduser()
    if not pytest_cwd.is_absolute():
        pytest_cwd = invocation_cwd / pytest_cwd
    pytest_cwd = pytest_cwd.resolve(strict=False)
    if not pytest_cwd.is_dir():
        parser.error(
            f"pytest working directory does not exist or is not a directory: {pytest_cwd}; "
            "check --cwd, or run from your project directory without --cwd"
        )
    try:
        contracts = parse_contracts(options.expectations, pytest_cwd)
    except ContractError as error:
        parser.error(
            f"{error}; use an import name and source directory, e.g. demo_pkg=src/demo_pkg"
        )

    report_path = Path(options.report_json).expanduser() if options.report_json else None
    if report_path is not None and not report_path.is_absolute():
        report_path = invocation_cwd / report_path
    pytest_args = tuple(options.pytest_args)
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    observer = ImportObserver(contracts)
    if platform.python_implementation() != "CPython":
        observer.mark_unsupported(ReasonCode.UNSUPPORTED_RUNTIME)

    run_started = time.perf_counter()
    os.chdir(pytest_cwd)
    observer.install()
    try:
        # Deliberately lazy: installing the observer must precede importing pytest.
        pytest = importlib.import_module("pytest")
        plugin = GuardPytestPlugin(observer)
        pytest_exit_code = int(pytest.main(list(pytest_args), plugins=[plugin]))
        observer.snapshot("pytest-returned")
        observer.stop()
        git = discover_git_context(pytest_cwd, enabled=not options.no_git_context)
        guard = classify(contracts, observer, git)
        metrics: dict[str, int | float] = {}
        metrics.update(observer.metrics())
        metrics["guarded_wall_seconds"] = time.perf_counter() - run_started
        if plugin.collection_seconds is not None:
            metrics["pytest_collection_seconds"] = plugin.collection_seconds
        report = RunReport(
            cwd=pytest_cwd,
            python=Path(sys.executable),
            pytest_args=pytest_args,
            pytest_exit_code=pytest_exit_code,
            guard=guard,
            git=git,
            xdist=observer.xdist,
            python_resolved=Path(sys.executable).resolve(strict=False),
            sys_prefix=sys.prefix,
            sys_base_prefix=sys.base_prefix,
            python_version=platform.python_version(),
            pytest_version=str(pytest.__version__),
            metrics=metrics,
        )
    finally:
        observer.stop()
        os.chdir(invocation_cwd)

    sys.stdout.write(render_human(report, show_all=options.show_all))
    if report_path is not None:
        try:
            write_json_report(report_path, report)
        except OSError as error:
            sys.stderr.write(f"wt-import: could not write JSON report {report_path}: {error}\n")
            sys.stderr.write(
                "Choose a writable file path in an existing directory; "
                "relative report paths start in the invocation directory. "
                "Pytest has already run; the JSON report was not saved successfully.\n"
            )
            return report_write_failure_exit_code(pytest_exit_code)
    return composite_exit_code(pytest_exit_code, guard.status)


if __name__ == "__main__":
    raise SystemExit(main())
