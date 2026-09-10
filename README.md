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

Install the command into the Python environment whose pytest run you want to inspect:

```console
python -m pip install worktree-import-guard
.venv/bin/wt-import --expect acme=src/acme -- -q
```

On Windows, the executable is normally `.venv\Scripts\wt-import.exe`. With `uv`, use:

```console
uv run wt-import --expect acme=src/acme -- -q
```

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
An ordinary pytest test failure remains exit 1. Native pytest exits 2, 3, 4, and 5 are preserved.

Use `--show-all` to include matching origins in human output. Use `--report-json PATH` for the
stable schema-versioned report:

```console
wt-import --expect acme=src/acme --report-json provenance.json -- -q
```

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
events with retained `sys.modules` snapshots at import returns and pytest lifecycle boundaries.
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

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). The real-worktree integration test constructs a temporary
main and feature worktree, deliberately resolves `demo_pkg` to main while running in feature, and
proves that ordinary pytest passes while the guard reports `CROSS_WORKTREE_IMPORT`.

