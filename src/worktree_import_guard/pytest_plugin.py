"""Explicit pytest plugin object used only by the ``wt-import`` command."""

from __future__ import annotations

import time
from typing import Any

from .models import ReasonCode
from .observer import ImportObserver


class GuardPytestPlugin:
    """Take snapshots at stable pytest lifecycle boundaries."""

    def __init__(self, observer: ImportObserver) -> None:
        self._observer = observer
        self._collection_started: float | None = None
        self.collection_seconds: float | None = None

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
                "worktree-import-guard 0.1 does not support distributed pytest-xdist execution; "
                "run a single process with -n 0 (also check pytest addopts and PYTEST_ADDOPTS)"
            )

    def pytest_sessionstart(self, session: Any) -> None:
        del session
        self._collection_started = time.perf_counter()
        self._observer.snapshot("pytest-session-start")

    def pytest_collection_finish(self, session: Any) -> None:
        del session
        if self._collection_started is not None:
            self.collection_seconds = time.perf_counter() - self._collection_started
        self._observer.snapshot("pytest-collection-finish")

    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:
        del session, exitstatus
        self._observer.snapshot("pytest-session-finish")
