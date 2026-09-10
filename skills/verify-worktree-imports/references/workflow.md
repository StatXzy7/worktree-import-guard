# Compatibility and installation

Skill revision 1 accepts report schema 2 from CLI 0.1.1 or the verified 0.1.0 source
preview at `edae3e6fa9a0b065385a080c371c9c17728b4656`. CLI and Skill versions are
independent. A bare 0.1.0 version string cannot identify which preview was installed.
The helper checks distribution metadata and direct_url for the pinned preview.

The current public route is a source preview, not a released PyPI package. After
authorization, using the confirmed project Python and a subprocess argument array:

```text
<project-python> -m pip install git+https://github.com/StatXzy7/worktree-import-guard.git@edae3e6fa9a0b065385a080c371c9c17728b4656
```

If an older same-version preview remains installed, first verify pytest >=8.2,<10
is satisfied, then refresh only this tool with the same command plus
`--force-reinstall --no-deps`, only within installation authorization. Never force
reinstall all dependencies or use no-deps to conceal unmet requirements. No network
or no compatible installation means no run, not a fabricated engine UNKNOWN.

For the probe, inspect `sys.executable`, `sys.prefix`, `sys.base_prefix`, and
`importlib.metadata.distribution('worktree-import-guard')` version, location and
direct_url. Console scripts may be under sysconfig's scripts directory or the
distribution's recorded installation path; Windows base Python need not place
scripts beside python.exe. Do not import pytest early in the guarded process.

For saved settings or candidates, import only the installed engine's configuration
or onboarding functions in a separate probe. A helper precheck failure is not an
engine provenance report. Do not widen roots or overwrite config to bypass it.
