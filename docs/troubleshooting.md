# Troubleshooting

Use the same project directory and environment as the pytest run you want to inspect.
The checks below do not repair your environment. Installing/syncing dependencies does modify it.

| Symptom | What to do |
| --- | --- |
| Shell cannot find `wt-import` | Invoke the console script beside that environment's pytest: `.venv/bin/wt-import` or `& ".venv\Scripts\wt-import.exe"`. Replace `.venv` with the real path; do not fall back to another PATH entry. |
| Script does not exist there | Check installation with that environment's `python -m pip show worktree-import-guard`. If absent, install the documented route there using the README command; installation may adjust dependencies. If pip is missing, use your project's established installer against that same interpreter. |
| No saved settings, malformed `PACKAGE=PATH` | Run `--setup` once, or use the Python import name and expected package directory, e.g. `--expect demo_pkg=src/demo_pkg`. Quote the whole argument if its path contains spaces. |
| `--cwd` does not exist | Correct the directory or invoke from the project root without `--cwd`. Expected paths start there; report paths start at the original invocation directory. |
| `TARGET_NOT_OBSERVED` | Check the import spelling and test selection. Select tests that use that package in this process. A child-process import is outside scope. Do not remove the target just to get green. |
| `ORIGIN_UNRESOLVED`, metadata conflict, non-filesystem origin | An import may have happened but its source metadata was insufficient or inconsistent. Inspect `--show-all` / JSON and custom loaders or test code that replaces module metadata. This is not the same as no import. |
| Namespace UNKNOWN | See [supported namespace limits](runtime-scope.md#namespace-packages). Multiple search roots cannot be verified. |
| Active parallel execution | Run single-process pytest, with `-- -n 0 -q` if xdist is installed. Check project `addopts` and `PYTEST_ADDOPTS` too. Child-process imports remain outside scope. |
| Cannot write JSON | Choose a file in an existing writable directory. A directory itself is not a report filename. Pytest has already run; rerunning can repeat test side effects. Read the terminal report even if JSON saving failed. |
| FAIL | Compare expected and observed directories. Check the selected environment using its `python -m pip show YOUR_DISTRIBUTION_NAME` (the pip name can differ from the import name). After confirming the cause, repair the editable install according to your project rules; repair changes the environment and the guard never runs it. |

## uv projects

For an incident, invoke the existing environment's console script directly as in README.
After confirming uv selects that exact environment and the script exists there, the alternative is:

```sh
uv run --no-sync wt-import --expect demo_pkg=src/demo_pkg -- -q
```

`--no-sync` requires an already prepared environment with the tool installed. It does not install
anything missing. Avoid `--with`, which can select an overlay environment for the command.
`--locked` controls lockfile changes; it does not disable sync.

For routine development, declare the tool in the project's development dependencies before syncing.
With a supplied candidate wheel (replace the absolute path):

```sh
uv add --dev "/path/to/worktree_import_guard-0.1.0-py3-none-any.whl"
uv run wt-import --expect demo_pkg=src/demo_pkg -- -q
```

On Windows, use a quoted absolute Windows wheel path. `uv add` updates project metadata, lockfile
and environment, so use it during planned setup, not before collecting incident evidence. A local
wheel dependency remains machine-specific until deliberately replaced by the published dependency.

Ordinary `uv run` automatically locks/syncs (inexact by default); it can change the project install
even while preserving extra packages. `uv sync` is exact by default and removes manually installed
packages absent from the lockfile. Do not manually install the tool then assume it survives sync.
These distinctions follow [uv's sync documentation](https://docs.astral.sh/uv/concepts/projects/sync/)
and are exercised by the candidate onboarding checks.

## Sharing a report

Include the symptom, expected result, tool/Python/pytest versions and a small reproducer.
JSON is optional. Redact usernames, company directories, secrets, private source and sensitive
command arguments before sharing. Never post full environment variables or credentials.

## Refresh an older source preview

Preview commits share version 0.1.0. First run the normal README installation command to satisfy
runtime dependencies. If you already had an older preview, then replace only the guard (using the
same project interpreter); `--no-deps` preserves the dependencies just checked:

```sh
".venv/bin/python" -m pip install --force-reinstall --no-deps "git+https://github.com/StatXzy7/worktree-import-guard.git@edae3e6fa9a0b065385a080c371c9c17728b4656"
```

```powershell
& ".venv\Scripts\python.exe" -m pip install --force-reinstall --no-deps "git+https://github.com/StatXzy7/worktree-import-guard.git@edae3e6fa9a0b065385a080c371c9c17728b4656"
```

This is not an environment repair or a project reinstall. Source-preview artifact tests verify the
installed VCS commit and retain an existing supported pytest 8.2.0 across both commands.
