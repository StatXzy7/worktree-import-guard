# First use and saved settings

Install into the Python environment that already runs your project's tests. Run `wt-import --demo`
to see a disposable example, then `wt-import --doctor` in your own project to configure a check.
`--setup` is retained as an equivalent spelling for scripts and existing users.
The demo uses the installed runtime, without downloads or dev extras. Its fixture deliberately
selects paths in a private temporary directory. With Git it creates real worktrees; without Git
it labels its two ordinary directories. The separate maintainer demo still verifies PEP 660.

Setup asks three questions: confirm the project/Python environment, choose package directories,
then confirm saving and running pytest. It never imports candidate packages or installs anything.
Src and flat packages are suggested; namespace and unusual layouts require explicit mappings.
Multiple candidates are never silently selected. Suggested `.venv` paths are not automatically
trusted or activated. If its guard is missing, install it using that Python and restart setup.

Setup creates `.wt-import.json` as UTF-8, without overwriting any existing file or link:

```json
{"schema_version": 1, "expect": {"demo_pkg": "src/demo_pkg"}}
```

Paths are portable relative paths based on the config's directory. They cannot leave this
worktree/project. No interpreter paths, executable commands, secrets or telemetry settings are
stored. Config schema v1 is independent of report schema v2.

Repeat the check using `wt-import -- -q`. The nearest config is found from `--cwd` (or the current
directory) up to this worktree's root. Without a Git boundary, only the chosen directory is checked.
Symlink configs, unknown/duplicate keys and malformed JSON produce an error. Any explicit
`--expect` replaces the entire configured target set for that run, even if the config is broken.

No targets/config in a noninteractive environment exits 2 immediately; `--setup` also requires a
terminal. Cancellation exits 2 without starting tests. A successful demo exits 0; unexpected demo
results or cleanup failures exit 1 and identify any leftover directory. `--demo` cannot be combined
with check options; `--setup` and `--expect` are mutually exclusive. Names after `--`, including
tests named `demo` or `setup`, remain pytest arguments.

Tests still execute with their usual side effects. Source PASS does not override failing tests;
no tests preserves pytest exit 5, and an unobserved package is UNKNOWN. Setup automation tests
exercise scripted terminal input; they are not evidence from real novice users.

If a redirected terminal cannot encode a path character, human output escapes that character
(for example `\u4e2d`) instead of crashing. UTF-8 configuration and JSON reports retain the exact path.
