"""Compare ordinary pytest and guarded pytest with raw repeated samples."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def console_script(name: str) -> Path:
    suffix = ".exe" if sys.platform == "win32" else ""
    path = Path(sys.executable).with_name(f"{name}{suffix}")
    if not path.is_file():
        raise SystemExit(f"required console script is missing: {path}")
    return path


def parse_suite(value: str) -> tuple[str, int]:
    try:
        name, raw_count = value.split("=", 1)
        count = int(raw_count)
    except ValueError as error:
        raise argparse.ArgumentTypeError("suite must be NAME=TEST_FILE_COUNT") from error
    if not name or count < 1:
        raise argparse.ArgumentTypeError("suite name must be nonempty and count must be positive")
    return name, count


def prepare_suite(root: Path, count: int) -> None:
    package = root / "bench_pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("VALUE = 42\n", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    for index in range(count):
        (tests / f"test_{index:05d}.py").write_text(
            "from bench_pkg import VALUE\n\ndef test_value():\n    assert VALUE == 42\n",
            encoding="utf-8",
        )
    (root / "conftest.py").write_text(
        """\
import json
import os
import time
from pathlib import Path

started = None

def pytest_sessionstart(session):
    global started
    started = time.perf_counter()

def pytest_collection_finish(session):
    elapsed = time.perf_counter() - started
    Path(os.environ["WTIG_BENCH_TIMING_FILE"]).write_text(
        json.dumps({"collection_seconds": elapsed}), encoding="utf-8"
    )
""",
        encoding="utf-8",
    )


def execute(
    command: list[str],
    *,
    cwd: Path,
    timing_path: Path,
    report_path: Path | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["WTIG_BENCH_TIMING_FILE"] = str(timing_path)
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    wall = time.perf_counter() - start
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout + completed.stderr)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    sample: dict[str, Any] = {
        "wall_seconds": wall,
        "collection_seconds": timing["collection_seconds"],
    }
    if report_path is not None:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        sample["guard_metrics"] = report["metrics"]
    return sample


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    walls = [sample["wall_seconds"] for sample in samples]
    collections = [sample["collection_seconds"] for sample in samples]
    return {
        "wall_median_seconds": statistics.median(walls),
        "wall_range_seconds": [min(walls), max(walls)],
        "collection_median_seconds": statistics.median(collections),
        "collection_range_seconds": [min(collections), max(collections)],
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", action="append", type=parse_suite, dest="suites")
    parser.add_argument("--repeats", type=int, default=7)
    options = parser.parse_args()
    suites = options.suites or [("small", 10), ("medium", 100), ("large", 500)]
    if options.repeats < 1:
        parser.error("--repeats must be positive")

    pytest_script = console_script("pytest")
    guard_script = console_script("wt-import")
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="wtig-pytest-benchmark-") as raw_temp:
        temp = Path(raw_temp)
        for suite_name, count in suites:
            suite_root = temp / suite_name
            prepare_suite(suite_root, count)
            standard_samples: list[dict[str, Any]] = []
            guarded_samples: list[dict[str, Any]] = []
            for repeat in range(options.repeats):
                timing = suite_root / f"standard-{repeat}.json"
                standard_samples.append(
                    execute([str(pytest_script), "-q"], cwd=suite_root, timing_path=timing)
                )
                timing = suite_root / f"guarded-{repeat}.json"
                report = suite_root / f"guarded-report-{repeat}.json"
                guarded_samples.append(
                    execute(
                        [
                            str(guard_script),
                            "--no-git-context",
                            "--report-json",
                            str(report),
                            "--expect",
                            "bench_pkg=bench_pkg",
                            "--",
                            "-q",
                        ],
                        cwd=suite_root,
                        timing_path=timing,
                        report_path=report,
                    )
                )
            standard = summarize(standard_samples)
            guarded = summarize(guarded_samples)
            standard_wall = standard["wall_median_seconds"]
            guarded_wall = guarded["wall_median_seconds"]
            results.append(
                {
                    "suite": suite_name,
                    "test_files": count,
                    "repeats": options.repeats,
                    "standard": standard,
                    "guarded": guarded,
                    "wall_overhead_seconds": guarded_wall - standard_wall,
                    "wall_overhead_ratio": guarded_wall / standard_wall - 1,
                }
            )
    print(json.dumps({"results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
