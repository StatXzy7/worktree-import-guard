# Benchmarks

The benchmark scripts are executable evidence, not claimed results for every project.

`observer_imports.py` populates `sys.modules`, performs cached imports unrelated to an absent
target, and emits every timing sample. This isolates the hot import-return path and also reports
import-return, incremental-capture, full-snapshot, and retained-observation counts.

`pytest_overhead.py` creates disposable small, medium, and large synthetic suites. It runs ordinary
and guarded pytest seven times each through sibling console scripts with `PYTHONPATH` removed,
user site disabled, and plugin auto-loading disabled. It reports external end-to-end wall time,
collection time from a common fixture hook, all raw samples, median, and range. Guard samples also
include the schema-v2 process metrics.

Run them from an environment where this checkout and its development dependencies are installed:

```console
python benchmarks/observer_imports.py --repeats 7
python benchmarks/pytest_overhead.py --repeats 7
```

The default suites use 10, 100, and 500 test files. Use repeated `--suite NAME=COUNT` arguments to
model other sizes. Do not describe seven samples as a reliable P95, and do not extrapolate cached
synthetic-import results to a complete real pytest suite.
