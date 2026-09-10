# Repository guidance

## Purpose

Catch Python tests that pass after importing explicitly selected packages from the wrong Git
worktree. This is current-process runtime provenance checking, not environment management or a
sandbox.

## Architecture

- `cli.py` coordinates the run without importing pytest early.
- `observer.py` captures target imports and lifecycle snapshots.
- `origins.py` resolves metadata; `matcher.py` performs component-wise containment.
- `git_worktrees.py` adds best-effort Git classification.
- `report.py` classifies and renders both human and JSON output from one model.
- `pytest_plugin.py` supplies the explicit, non-auto-loaded pytest hooks.

## Checks

```console
ruff check .
mypy src
pytest
pytest --cov=worktree_import_guard --cov-report=term-missing
python -m build
```

## Invariants

- Never mutate `PYTHONPATH`, insert expected roots into `sys.path`, or auto-fix an environment.
- Install observation before importing pytest; do not add a `pytest11` entry point.
- UNKNOWN must never become PASS.
- Public reason codes and JSON schema are compatibility surfaces.
- Use canonical path components, not string-prefix containment.
- Preserve native pytest exit codes 2 through 5.
- Add a regression test for every provenance bug.

