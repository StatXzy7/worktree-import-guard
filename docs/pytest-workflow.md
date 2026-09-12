# Keep the check in an existing pytest workflow

Use the environment and project directory that already run your tests. Install using the
install command in [README](../README.md#install-into-your-existing-test-environment), then run
`wt-import --setup` once. Review `.wt-import.json` and commit it only if your team wants that contract.

Replace the one pytest command you choose to guard:

```sh
# Before, in the prepared project environment:
pytest -q
# After confirming the saved package directories:
wt-import -- -q
```

Use the full environment executable path from README if it is not on PATH. The same command works
in an already prepared CI environment; it does not prompt. Keep the existing test arguments after
`--`. Do not add a long test suite to every commit or change unrelated hooks.

For an incident, run the check before changing the target project's installation or syncing.
For routine development, prepare dependencies according to the project's existing workflow first.
Native pytest failures remain failures; if pytest passes but provenance fails, investigate the
reported directories. An unobserved package is UNKNOWN, not a reason to delete it from the contract.

This saved-config command is exercised for src and flat fixtures in the installed-artifact tests,
including a source PASS combined with failing tests. It is not a claim of external adoption.
