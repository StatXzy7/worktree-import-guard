"""Explicit pytest plugin object used only by the ``wt-import`` command."""

from __future__ import annotations

from typing import Any

from .models import ReasonCode
from .observer import ImportObserver


class GuardPytestPlugin:
    """Take snapshots at stable pytest lifecycle boundaries."""

    def __init__(self, observer: ImportObserver) -> None:
        self._observer = observer

    @staticmethod
    def _xdist_requested(config: Any) -> bool:
        if hasattr(config, "workerinput"):
            return True
        try:
            num_processes = config.getoption("numprocesses", default=None)
        except (AttributeError, ValueError):
            return False
        return num_processes not in (None, 0, "0")

    def pytest_configure(self, config: Any) -> None:
        self._observer.snapshot("pytest-configure")
        if self._xdist_requested(config):
            self._observer.mark_unsupported(ReasonCode.UNSUPPORTED_RUNTIME, xdist=True)
            import pytest

            raise pytest.UsageError(
                "worktree-import-guard 0.1 does not support distributed pytest-xdist execution"
            )

    def pytest_collection_finish(self, session: Any) -> None:
        del session
        self._observer.snapshot("pytest-collection-finish")

    def pytest_runtest_setup(self, item: Any) -> None:
        del item
        self._observer.snapshot("pytest-test-setup")

    def pytest_runtest_call(self, item: Any) -> None:
        del item
        self._observer.snapshot("pytest-test-call")

    def pytest_runtest_teardown(self, item: Any, nextitem: Any) -> None:
        del item, nextitem
        self._observer.snapshot("pytest-test-teardown")

    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:
        del session, exitstatus
        self._observer.snapshot("pytest-session-finish")
