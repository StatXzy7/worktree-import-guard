# Cross-worktree demo

Build the distributions, then run the disposable demo from the repository root:

```console
python -m build
python examples/cross-worktree-demo/run.py --wheel dist
```

It creates a temporary Git repository with `main` and `feature` worktrees. Both contain
`src/demo_pkg`, and both implementations return `42`. A deliberately stale test configuration in
the feature worktree resolves `demo_pkg` from main. Ordinary pytest therefore passes, while:

```console
wt-import --expect demo_pkg=src/demo_pkg -- -q
```

reports `CROSS_WORKTREE_IMPORT` and exits 1 even though the retained pytest exit is 0. The script
then switches the same environment's editable install to the feature worktree and proves that the
guard passes. It uses a temporary repository and environment, removes both on completion, clears
`PYTHONPATH`, and runs only the installed wheel's console scripts.

The automated equivalents are
`tests/integration/test_cross_worktree.py::test_real_cross_worktree_import_is_caught` and the
opt-in artifact test under `tests/artifact`.
