# worktree-import-guard

> Catch Python tests that pass against the wrong Git worktree.

```text
$ pytest -q
47 passed

$ wt-import --expect acme=src/acme -- -q
expected: /repo/feature/src/acme
observed: /repo/main/src/acme/core.py
reason:   CROSS_WORKTREE_IMPORT
```

`worktree-import-guard` checks runtime provenance for explicitly selected Python packages during
one pytest process. It is aimed at the subtle case where tests pass, but imports came from an
editable install, stale environment entry, or another checkout instead of the worktree under test.

## Install and use

Until the first package release, install from an authorized checkout into the Python environment
whose pytest run you want to inspect:

```console
python -m pip install -e .
.venv/bin/wt-import --expect acme=src/acme -- -q
```

You can also install a locally built candidate with
`python -m pip install dist/worktree_import_guard-0.1.0-py3-none-any.whl`. After the package is
actually published, `python -m pip install worktree-import-guard` will be the PyPI installation
form; it is not presented here as an already available release.

On Windows, the executable is normally `.venv\Scripts\wt-import.exe`.

For a routine `uv` project run, prepare/sync the project environment first and then invoke the
command:

```console
uv sync
uv run wt-import --expect acme=src/acme -- -q
```

`uv run` normally checks and syncs the project environment. For incident diagnosis of an existing
possibly stale environment, invoke its already-installed console script directly:

```console
.venv/bin/wt-import --expect acme=src/acme -- -q
```

On Windows use `.venv\Scripts\wt-import.exe`. After confirming that `uv` selects that exact
environment and that the command is already installed, `uv run --no-sync wt-import ...` is an
alternative. `--locked` controls lockfile changes; it does not disable environment syncing.

The command deliberately has no `--python` option. The environment is selected by the
`wt-import` executable you invoke. It calls `pytest.main(...)` in that process and neither changes
`PYTHONPATH` nor inserts an expected source directory into `sys.path`.

Declare more than one package by repeating the option. Dotted packages are supported:

```console
wt-import \
  --expect acme=src/acme \
  --expect shared.api=packages/shared/src/shared/api \
  -- tests/unit -q

wt-import -C backend --expect service=src/service -- -q
```

Relative expected paths are resolved from the pytest working directory (`--cwd`, or the current
directory by default).

## Results

Each target is `pass`, `fail`, or `unknown`:

- `pass`: every concrete observed origin is within the canonical expected package directory.
- `fail`: at least one concrete observed origin is outside it.
- `unknown`: the target was not observed, or its origin could not be resolved safely.

Unknown never means pass. If pytest succeeds, guard pass/fail/unknown produce process exits 0/1/2.
An ordinary pytest test failure remains exit 1. All native nonzero pytest exits are preserved,
including exit 6 for warning limits on pytest versions that provide it.
If JSON writing also fails, the existing nonzero pytest exit remains authoritative and the report
error is printed to stderr; with pytest exit 0, a report-write failure exits 2.

Use `--show-all` to include matching origins in human output. Use `--report-json PATH` for the
stable schema-versioned report:

```console
wt-import --expect acme=src/acme --report-json provenance.json -- -q
```

Schema v2 records the invoked virtual-environment identity (`python`, `sys_prefix`) separately
from the resolved interpreter binary, plus Python/pytest versions and observation metrics.
`guard.complete` means every target has determinate evidence; `guard.observation_complete` means
the supported observation lifecycle ran to completion. See
[`docs/json-schema-v2.md`](docs/json-schema-v2.md) and the golden reports under `tests/golden`.

Git context is best effort. When the expected and wrong origins belong to different worktrees in
the same `git worktree list --porcelain -z` result, the reason is `CROSS_WORKTREE_IMPORT`.
Otherwise it is `OUTSIDE_EXPECTED_ROOT`. Use `--no-git-context` to skip Git discovery entirely.

Public V0.1 reason codes are:

```text
MATCH
CROSS_WORKTREE_IMPORT
OUTSIDE_EXPECTED_ROOT
MIXED_ORIGINS
TARGET_NOT_OBSERVED
ORIGIN_UNRESOLVED
ORIGIN_METADATA_CONFLICT
NON_FILESYSTEM_ORIGIN
UNSUPPORTED_NAMESPACE_LAYOUT
UNSUPPORTED_RUNTIME
```

## What is observed

The command installs observation before lazily importing pytest. It combines CPython audit import
events with incremental target capture at import returns and full `sys.modules` snapshots at
observer/pytest lifecycle boundaries. Cached unrelated imports do not scan the full module table.
For each selected package and loaded submodule, it evaluates `__spec__.origin`, `__file__`, and
namespace search locations. Canonical path operations handle dot segments, symlinks, Windows case
normalization, separators, spaces, and component boundaries; string-prefix containment is never
used.

For a one-off incident, manually checking `package.__file__` is a valid solution. The value of
this tool is making the check repeatable, covering selected submodules, producing deterministic
exit codes and JSON, and allowing it to be retained in a test, CI, or coding-agent workflow.

## Scope and trust

V0.1 observes only the current, single pytest process.

- Complete pytest-xdist tracing is not supported. An active distributed run is rejected rather
  than reported as a trustworthy pass.
- Imports that occur only in child processes are not covered.
- Namespace packages with more than one search root are reported unknown.
- This is runtime diagnostic instrumentation, not environment prediction or repair.
- It does not create environments, repair editable installs, or mutate import paths.
- It is not a sandbox, and audit hooks are not tamper-proof security evidence.

Pytest executes arbitrary repository code. Use this tool only for trusted or authorized test
execution; hostile code in the same process can interfere with diagnostics.

## Reproducible demo and performance probes

The installed-wheel demo creates and removes its own temporary Git repository, two worktrees, and
shared virtual environment:

```console
python -m build
python examples/cross-worktree-demo/run.py --wheel dist
```

Independent observer and end-to-end pytest benchmark scripts retain all samples and report medians
plus ranges:

```console
python benchmarks/observer_imports.py --repeats 7
python benchmarks/pytest_overhead.py --repeats 7
```

These synthetic probes are regression evidence, not a universal performance claim. See
[`benchmarks/README.md`](benchmarks/README.md) for their measured fields and limitations.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). The real-worktree integration test constructs a temporary
main and feature worktree, deliberately resolves `demo_pkg` to main while running in feature, and
proves that ordinary pytest passes while the guard reports `CROSS_WORKTREE_IMPORT`.
