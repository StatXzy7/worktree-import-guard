# Maintainer editable-install demo

This is optional. Checking your own project does not require this demo.

For the installed offline experience, use `wt-import --demo` after the [public preview installation](../../README.md).
This separate maintainer test requires a checkout of this repository and a wheel built with
`python -m build`; `run.py` is in this directory. It verifies the real PEP 660 chain.
With Python 3.10–3.13 including venv/pip and Git on PATH, run from the directory containing run.py:

```sh
python run.py --wheel "/path/to/worktree_import_guard-0.1.0-py3-none-any.whl"
```

PowerShell uses the same command with your quoted Windows wheel path. If you already have this
repository, the equivalent from its root is `python examples/cross-worktree-demo/run.py --wheel
"/path/to/worktree_import_guard-0.1.0-py3-none-any.whl"` (one line). No build or dev extras needed.

The driver creates a private temporary repository, two real worktrees and a shared venv. Setup
uses pip and may download pytest, setuptools and their dependencies. All editable installs and
changes happen in that demo environment, not your project's environment. It does not inspect your
repository. It prints its temporary directory, attempts normal cleanup, and reports the exact
residual path if cleanup is restricted. It does not elevate permissions or retry policy bypasses.

It verifies ordinary pytest succeeds, a wrong editable import is `CROSS_WORKTREE_IMPORT` with
pytest exit 0 / guard exit 1, then installs the feature fixture in its own venv and verifies
complete PASS / exit 0. Expected guard exit 1 is part of demo success. Any unexpected result fails
the driver. The fixture contains exactly one test. Output paths and timings depend on your machine.

For maintainers, `--wheel dist` accepts a directory with exactly one candidate wheel.
