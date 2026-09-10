"""Measure cached unrelated-import overhead without importing pytest."""

from __future__ import annotations

import argparse
import builtins
import json
import statistics
import sys
import time
from pathlib import Path
from types import ModuleType

from worktree_import_guard.models import PackageContract
from worktree_import_guard.observer import ImportObserver


def _populate_modules(count: int) -> list[str]:
    names = [f"_wtig_benchmark_dummy_{index}" for index in range(count)]
    for name in names:
        sys.modules[name] = ModuleType(name)
    return names


def _time_cached_imports(iterations: int) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        builtins.__import__("math")
    return time.perf_counter() - start


def measure(module_count: int, iterations: int, repeats: int) -> dict[str, object]:
    names = _populate_modules(module_count)
    contract = PackageContract(
        package="_wtig_benchmark_absent",
        declared_path="_wtig_benchmark_absent",
        expected_root=Path.cwd() / "_wtig_benchmark_absent",
    )
    observer = ImportObserver((contract,))
    observer_stats: dict[str, int]
    try:
        baseline = [_time_cached_imports(iterations) for _ in range(repeats)]
        observer.install()
        guarded = [_time_cached_imports(iterations) for _ in range(repeats)]
        observer_stats = {
            "import_returns": observer.import_returns,
            "incremental_captures": observer.incremental_captures,
            "full_snapshots": observer.full_snapshots,
            "observations": len(observer.observations_for(contract.package)),
        }
    finally:
        observer.stop()
        for name in names:
            sys.modules.pop(name, None)
    return {
        "module_count_requested": module_count,
        "module_count_observed": len(sys.modules) + module_count,
        "iterations": iterations,
        "repeats": repeats,
        "baseline_seconds": baseline,
        "baseline_median_seconds": statistics.median(baseline),
        "guarded_seconds": guarded,
        "guarded_median_seconds": statistics.median(guarded),
        "observer": observer_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module-count", type=int, action="append", dest="module_counts")
    parser.add_argument("--iterations", type=int, default=1_000)
    parser.add_argument("--repeats", type=int, default=7)
    options = parser.parse_args()
    counts = options.module_counts or [1_000, 2_000, 4_000]
    results = [measure(count, options.iterations, options.repeats) for count in counts]
    print(json.dumps({"results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
