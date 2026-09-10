# Contributing

`worktree-import-guard` intentionally has a narrow V0.1 scope. Changes should preserve its role as
a diagnostic wrapper around a single-process pytest run, without environment repair or import-path
mutation.

## Setup

```console
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest
pytest --cov=worktree_import_guard --cov-report=term-missing
python -m build
```

Run the commands through their console scripts where shown. In particular, provenance integration
fixtures must not replace pytest console-script semantics with `python -m pytest`.

Add a focused regression test for every provenance bug. Tests making a cross-worktree claim must
use real Git worktrees, not only mocks. Keep public reason codes and JSON schema changes deliberate
and documented.

By contributing, you agree that your contribution is licensed under the MIT License.

## Explicit installation checks

These opt-in tests create disposable environments and can download dependencies.
On POSIX: `WTIG_RUN_ARTIFACT_TESTS=1 pytest tests/artifact -q -rA`.
On PowerShell: `$env:WTIG_RUN_ARTIFACT_TESTS="1"`, then `pytest tests/artifact -q -rA`.
Set `WTIG_ARTIFACT_WHEEL` to an absolute candidate wheel path to test that exact file;
otherwise tests build temporary wheels. Normal pytest intentionally skips these expensive checks.

See [releasing](docs/releasing/README.md) for candidate identity, sdist and demo checks.
No release upload is part of these checks.
