# worktree-import-guard

> Catch Python tests that pass against the wrong Git worktree.

You changed code in one checkout, but Python may still import your package from another.
This tool checks where selected packages were actually loaded from during pytest.

[简体中文](https://github.com/StatXzy7/worktree-import-guard/blob/main/README.zh-CN.md)

This real [demo](https://github.com/StatXzy7/worktree-import-guard/blob/main/examples/cross-worktree-demo/README.md) has **one test**: ordinary pytest
passes even when the editable install points to the wrong worktree. Excerpt from the B1 Windows demo;
temporary path prefix replaced by `<demo>` (additional module details omitted):

```text
1 passed in 0.03s

Tests passed.
WORKTREE IMPORT GUARD: FAIL
expected: <demo>\feature worktree\src\demo_pkg
observed: <demo>\main repository\src\demo_pkg\core.py (demo_pkg.core)
reason:   CROSS_WORKTREE_IMPORT
next:     Code was loaded from another worktree. Check the Python environment and the editable install used by this test run.

pytest exit: 0
guard:      FAIL
```

## Install once, then check your project

**0.1.0 is a release candidate, not a published PyPI release.** For early access, obtain the
candidate `worktree_import_guard-0.1.0-py3-none-any.whl` from the maintainer. There is no public
B1 download yet. You do not need to clone this tool, install dev extras, or build it yourself.

Run from **your project's root directory**, in the environment where its pytest already works.
Below, `.venv` is an example of that **existing** environment, not a directory the tool creates.
Replace it with your actual environment path and replace the wheel path with the file you received.
Do not create a new environment or reinstall your project just to diagnose it.

Linux / macOS:

```sh
".venv/bin/python" -m pip install "/path/to/worktree_import_guard-0.1.0-py3-none-any.whl"
".venv/bin/wt-import" --expect demo_pkg=src/demo_pkg -- -q
```

Windows PowerShell (no activation or execution-policy change needed):

```powershell
& ".venv\Scripts\python.exe" -m pip install "C:\path to\worktree_import_guard-0.1.0-py3-none-any.whl"
& ".venv\Scripts\wt-import.exe" --expect demo_pkg=src/demo_pkg -- -q
```

Use your package's import name and directory in place of `demo_pkg=src/demo_pkg`.
The Python and `wt-import` paths must belong to the **same environment**. Quote executable paths
and whole arguments containing spaces, e.g. `--expect "demo_pkg=source tree/demo_pkg"`.
Installation can install or adjust dependencies (including pytest). The check itself does not
repair installs or change import paths; your tests still execute and may have side effects.

For an incident, if the tool is already installed, run **only the check command** first. Do not
sync or reinstall the target project before inspecting it. For routine development, follow your
project's dependency setup first. [uv and missing-command help](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/troubleshooting.md).
`pipx`, `uvx` and `uv tool install` use separate tool environments and are not the recommended
way to inspect your existing pytest environment.

The [release notes draft](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/releasing/0.1.0-notes.md) contains the shorter PyPI install command
for activation **after publication**. Candidate installation is not a PyPI download test.

## What goes in --expect?

For a **src layout**:

```text
project/
  src/
    demo_pkg/
      __init__.py
  tests/
```

Use `--expect demo_pkg=src/demo_pkg`.

For a **flat layout**:

```text
project/
  demo_pkg/
    __init__.py
  tests/
```

Use `--expect demo_pkg=demo_pkg`.

The left side is the name in `import demo_pkg`; it may differ from the name used by pip.
The right side is the source **package directory** you want these tests to load. Do not use just
the repository root or point it at another worktree. Repeat `--expect` for multiple packages,
e.g. `--expect demo_pkg=src/demo_pkg --expect shared.api=lib/shared/api`.

Relative expected paths start in the pytest working directory. From a parent directory,
`--cwd backend --expect demo_pkg=src/demo_pkg` expects `backend/src/demo_pkg` and runs pytest in
`backend`. If the executable is also inside backend, invoke `"backend/.venv/bin/wt-import"` (or
`& "backend\.venv\Scripts\wt-import.exe"` in PowerShell). Executable paths are still relative
to the shell's current directory. Relative `--report-json` paths start in the original invocation
directory, even with `--cwd`.

No `__init__.py`? Read the [namespace limits](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/runtime-scope.md#namespace-packages).

## Read the result

| Result | Meaning | Next step |
| --- | --- | --- |
| PASS | Observed sources for your selected packages match the requested directories. | Check pytest's separate result; this does not prove test coverage. |
| FAIL | Observed code came from outside a requested directory. | Compare `expected` and `observed`; inspect the selected environment and editable install. |
| UNKNOWN | This source check could not be completed. | Read `reason` and `next`: the target may be unobserved, metadata unresolved, or execution unsupported. |

UNKNOWN is never a pass. The report shows each selected package and its expected directory.
`--show-all` also shows matching modules. `--report-json provenance.json` saves detailed evidence;
use an existing writable directory and redact paths before sharing it.

If pytest fails but the guard says PASS, **the tests failed and the observed sources matched**.
All native nonzero pytest exits are preserved, including exit 6 where pytest supports it.
When pytest exits 0, guard PASS / FAIL / UNKNOWN exit 0 / 1 / 2. A JSON write failure exits 2
when pytest succeeded, otherwise preserving pytest's nonzero exit.

## Common questions and limits

- Only explicitly selected packages, their observed submodules, and this supported pytest process
  are checked. Unexecuted code and child-process-only imports are not verified.
- Active pytest-xdist is unsupported; run one process (`-n 0` when xdist is installed).
- A mismatch is called “another worktree” only when Git confirms the relationship.
- This does not prove coverage, code equality to a commit, or complete environment isolation.
- It does not fix your environment and is not a sandbox. Run tests you trust or are authorized to run.

See [troubleshooting](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/troubleshooting.md) for missing commands, arguments, UNKNOWN and JSON errors.
Want to see it before checking your own code? The [disposable demo](https://github.com/StatXzy7/worktree-import-guard/blob/main/examples/cross-worktree-demo/README.md)
creates its own two worktrees and environment and checks all three expected outcomes.

## Details and contributing

[Runtime scope](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/runtime-scope.md) · [JSON schema v2](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/json-schema-v2.md) ·
[Contributing](https://github.com/StatXzy7/worktree-import-guard/blob/main/CONTRIBUTING.md) · [Security](https://github.com/StatXzy7/worktree-import-guard/blob/main/SECURITY.md) · [Changelog](https://github.com/StatXzy7/worktree-import-guard/blob/main/CHANGELOG.md) ·
[Release checklist](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/releasing/README.md) · [Historical B0 evidence](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/release-readiness/b0-readiness.md) ·
[Benchmarks](https://github.com/StatXzy7/worktree-import-guard/blob/main/benchmarks/README.md)
