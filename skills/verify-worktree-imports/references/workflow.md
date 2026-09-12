# Compatibility and installation

Skill revision 1 accepts report schema 2 from CLI 0.1.2 and compatible future
releases. CLI and Skill versions are independent; a bare `worktree-import-guard`
version string is used to select compatible behavior.

The current public route is the released package:

```text
<project-python> -m pip install "worktree-import-guard==0.1.2"
```

If an older candidate/preview remains installed in the target environment, remove
that environment’s legacy installation and install the released route.
Never force-reinstall dependencies to work around unmet requirements. No compatible
installation means no run, and no fabricated engine UNKNOWN.

For the probe, inspect `sys.executable`, `sys.prefix`, `sys.base_prefix`, and
`importlib.metadata.distribution('worktree-import-guard')` version, location and
direct_url. Console scripts may be under sysconfig's scripts directory or the
distribution's recorded installation path; Windows base Python need not place
scripts beside python.exe. Do not import pytest early in the guarded process.

For saved settings or candidates, import only the installed engine's configuration
or onboarding functions in a separate probe. A helper precheck failure is not an
engine provenance report. Do not widen roots or overwrite config to bypass it.
