# Cross-worktree demo

The reproducible demo is executable as
`tests/integration/test_cross_worktree.py::test_real_cross_worktree_import_is_caught`.

It creates a temporary Git repository with `main` and `feature` worktrees. Both contain
`src/demo_pkg`, and both implementations return `42`. A deliberately stale test configuration in
the feature worktree resolves `demo_pkg` from main. Ordinary pytest therefore passes, while:

```console
wt-import --expect demo_pkg=src/demo_pkg -- -q
```

reports `CROSS_WORKTREE_IMPORT` and exits 1 even though the retained pytest exit is 0. No
`PYTHONPATH` environment variable is used, and the guard itself never alters import paths.

