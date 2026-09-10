# Repository guidance

## Purpose

Catch Python tests that pass after importing explicitly selected packages from the wrong Git
worktree. This is current-process runtime provenance checking, not environment management or a
sandbox.

## Product principles

- Help ordinary Python developers find which source their tests actually loaded.
- Recommend one installation and check path in the project's existing pytest environment.
- Explain what happened before technical evidence, and give an actionable next step.
- Keep PASS scoped to observed selected packages; never hide UNKNOWN or guess a safe origin.
- Diagnose without repairing the environment or expanding into environment management.
- Keep onboarding short; put schemas, benchmarks, and release evidence in maintainer docs.
- Prefer small, reliable changes that reduce a concrete installation or diagnosis problem.

## Text encoding

- Read and write text as UTF-8, preferably without BOM; use explicit UTF-8 for PowerShell I/O.
- Preserve existing content and verify Chinese text after editing.

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
- Preserve every native nonzero pytest exit, including exit 6 on versions that provide it.
- Add a regression test for every provenance bug.

