# worktree-import-guard

> Your tests passed. They may have tested another checkout.

You changed **feature**, but Python still loaded **main**. Catch that mismatch while pytest runs.
[简体中文](README.zh-CN.md)

A [real recorded example](docs/demo-output.txt), shortened to key lines; `<demo>` replaces its
temporary directory. This is an example, not a scan of your computer:

```text
1. Ordinary pytest:
1 passed in 0.04s

2. Check wrong source:
Tests passed.
WORKTREE IMPORT GUARD: FAIL
expected: <demo>\feature\src\demo_pkg
observed: <demo>\main\src\demo_pkg\__init__.py (demo_pkg)
reason:   CROSS_WORKTREE_IMPORT

3. Select correct source inside this example:
Tests passed.
WORKTREE IMPORT GUARD: PASS
```

## Install into your existing test environment

**Public source preview, not a PyPI release.** No need to contact the author or obtain a wheel.
You need Python with pip, Git, and network access to download source, build dependencies and pytest.
The commit below is fixed and verified; the project is still alpha.

Use the environment where your project's pytest already works. `.venv` below is an example of
that **existing environment**; replace it with your real path. If you do not have a Python test
project yet, the recorded example explains the tool without installing anything.

Linux / macOS:

```sh
".venv/bin/python" -m pip install "git+https://github.com/StatXzy7/worktree-import-guard.git@edae3e6fa9a0b065385a080c371c9c17728b4656"
```

Windows PowerShell (no activation or execution-policy changes):

```powershell
& ".venv\Scripts\python.exe" -m pip install "git+https://github.com/StatXzy7/worktree-import-guard.git@edae3e6fa9a0b065385a080c371c9c17728b4656"
```

Installation satisfies the tool's pytest requirement; already supported dependencies are retained.
**Upgrading an earlier 0.1.0 preview?** After this install, follow the
[guard-only refresh command](docs/troubleshooting.md#refresh-an-older-source-preview) to replace the
same-version tool without reinstalling pytest. If this exact preview is already installed, skip
installation. During an incident, do not sync or repair the target project first.

## Choose an entry

| First, see what it does | Check my project |
| --- | --- |
| `wt-import --demo` | `wt-import --setup` |
| Runs an offline, private example with the installed tool. | Confirms project/environment, package directories, then saving and running tests. |

Use the executable in the same environment as the Python above:

```sh
".venv/bin/wt-import" --demo
".venv/bin/wt-import" --setup
# After setup, repeat checks without re-entering directories:
".venv/bin/wt-import" -- -q
```

```powershell
& ".venv\Scripts\wt-import.exe" --demo
& ".venv\Scripts\wt-import.exe" --setup
# After setup:
& ".venv\Scripts\wt-import.exe" -- -q
```

Run setup from your project's root. Choose package number(s), review the settings, then confirm.
Setup creates `.wt-import.json`; you do not need to write it. Multiple candidates require a choice,
and existing files are never overwritten. It never installs, activates or repairs an environment.
[Settings and unusual layouts](docs/first-use.md).

The demo deliberately selects a wrong path in a disposable fixture, without inspecting your project.
With Git it creates real worktrees, otherwise it labels two ordinary directories. It needs no
downloads after installation. The [maintainer demo](examples/cross-worktree-demo/README.md)
separately verifies the complete editable-install chain.

## Read the two results

### Let a coding agent check

An [experimental local Codex Skill](docs/skill-quickstart.md) reuses your settings
and runs the detector in your project's existing pytest environment. Import the
Skill folder once, then ask: “Use $verify-worktree-imports to check this project;
do not repair the environment.” The host needs local project access; first use
may require an environment/install confirmation. [Validation status](docs/skill-validation.md).

| Source result | Meaning | Next step |
| --- | --- | --- |
| PASS | Observed sources for selected packages match your directories. | Check pytest's separate result too. |
| FAIL | Observed code came from outside a selected directory. | Compare expected/observed and inspect the chosen environment/install. |
| UNKNOWN | Source checking could not be completed. | Read reason/next: the target may be unobserved or its source unresolved. |

**Tests failed + source PASS still means the tests failed. UNKNOWN is never a pass.**
Native nonzero pytest exits are preserved. With pytest exit 0, source PASS / FAIL / UNKNOWN exit
0 / 1 / 2. No tests preserves pytest exit 5. JSON write failures do not hide pytest failures.

## Scope and requirements

Tested with CPython 3.10–3.13 and pytest >=8.2,<10 on Windows and POSIX CI. Only selected packages,
their observed submodules, and this supported pytest process are checked. Unexecuted code, coverage,
commit-content equality and child-process imports are not verified. Active xdist and multi-root
namespaces are unsupported. A worktree mismatch requires Git evidence. This is not a sandbox;
your tests still execute and may have side effects.

Use the project's actual environment. `pipx`, `uvx` and `uv tool install` create separate tool
environments and are not recommended here. [Troubleshooting, including uv](docs/troubleshooting.md).

## Explicit checks and details

For automation or a one-off check, no setup or config is needed:

```sh
wt-import --expect demo_pkg=src/demo_pkg -- -q
```

Flat layout: `--expect demo_pkg=demo_pkg`. Use the Python import name, not necessarily the pip name,
and the source **package directory**, not the repository root. Repeat `--expect` for multiple
packages. Explicit targets replace all saved targets for that run. Quote mappings with spaces.

`--cwd backend` changes the pytest directory and base for explicit relative expectations. Config
paths are relative to their config file. `--report-json provenance.json` saves UTF-8 evidence
relative to the original invocation directory; `--show-all` includes matching origins.
Without config or explicit targets, CI exits 2 immediately; setup needs an interactive terminal.

[Existing pytest workflow](docs/pytest-workflow.md) · [First-use details](docs/first-use.md) ·
[Runtime scope](docs/runtime-scope.md) · [JSON schema v2](docs/json-schema-v2.md) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md) ·
[Benchmarks](benchmarks/README.md) · [Publication step](docs/releasing/README.md)

The pinned source revision predates this homepage rewrite, so its packaged README still contains
the older installation text. Use this repository homepage for the current entry points, or the
[documentation at the preview revision](https://github.com/StatXzy7/worktree-import-guard/tree/edae3e6fa9a0b065385a080c371c9c17728b4656/docs).
