# B1 — User-first onboarding and release preparation for 0.1.0

Status: **PREPARED_WITH_VERIFICATION_GAPS**. Local preparation and acceptance passed; this
session did not authorize push/PR, so the required new Windows/POSIX CI runs remain outstanding.
This is not approval to publish. No external human usability study was performed.

## Frozen source and files

Accepted local source: `fb1033a09207cf5367e97cca0cf83a4235a78eed`, with a clean working tree at
`D:\worktree-import-guard`, branch `codex/b1-user-first-release`. This summary is a later
documentation commit and does not replace those frozen files or identify itself as their source.

PR #1 was open at inspection, head `b4e3afe66981bc3d1744c61593d5cc20772b1c93`; B1 branches from
that B0 head. The latest B0 runs were successful, but their results are not B1 platform evidence.
No B1 PR exists yet. A local proposed PR body is in the external candidate directory below.

External evidence root: `D:\temp\wtig-b1-20260910\final-candidate`.
The authoritative manifest is `verification/manifest.json`; it includes complete hashes,
installation results, source identity, log hashes, platform scope and explicit null CI identifiers.

| File in dist/ | Bytes | SHA-256 |
| --- | ---: | --- |
| worktree_import_guard-0.1.0-py3-none-any.whl | 22,080 | 28e2544f0d79d3315249c130f8c58e591d67558fb105451bce3e993ef6dc07a3 |
| worktree_import_guard-0.1.0.tar.gz | 197,471 | ec7ad4884694be1e3d8eacb9add393a9929d20a07ee0599e452001df2612a9c6 |

Builder: Windows 11, CPython 3.13.9, build 1.6.1, isolated hatchling 1.32.0. Package 0.1.0 and
JSON schema 2 remain independent. The sdist-derived wheel matched the wheel hash above in this
run; cross-environment byte reproducibility is not promised. B0 records were not modified.

## User outcome and validation

The homepage now explains the wrong-source problem before internals, binds installation and the
console script to the existing pytest environment, teaches src/flat mappings and quotes spaces.
The Chinese entry, troubleshooting and help follow the same contract. Human output separates
pytest failure from source PASS, gives per-package status, and explains UNKNOWN without hiding it.

Actual wrong-editable Demo excerpt (paths redacted, some module details omitted):

```text
Tests passed.
WORKTREE IMPORT GUARD: FAIL
Observed code sources do not match your directory requirements.
demo_pkg: FAIL
reason:   CROSS_WORKTREE_IMPORT
next:     Code was loaded from another worktree. Check the Python environment and the editable install used by this test run.
pytest exit: 0
guard:      FAIL
```

Recorded local combination: Windows 11 / CPython 3.13.9 / pytest 9.1.1. Checks at the frozen source:

- Ruff and mypy passed (10 source files).
- Regular pytest: 59 passed, 3 intentional artifact skips. Coverage: 93.10%, threshold still 90%.
- Explicit artifact suite: 3 passed, 0 skipped, using the exact supplied wheel. Includes real
  `.pth` and editable wrong-worktree cases plus src/flat README commands through PowerShell,
  spaces, cwd/report bases, missing install diagnosis, UNKNOWN, test failure and JSON-write errors.
- Existing schema v2 goldens, native pytest nonzero exits (including actual exit 6), plugin smokes
  and provenance regressions passed. Observer, classification and JSON semantics were unchanged.
- Demo verified one passing native test, wrong-source guard exit 1 with CROSS_WORKTREE_IMPORT,
  then complete correct-source PASS. Its temporary files were removed successfully.
- Wheel/sdist build, strict twine metadata checks, sdist-derived installation and console scripts
  passed. Runtime-only onboarding installed no dev tools. Wheel code and README matched checkout.
- README rendered using readme_renderer 44.0; package links are absolute and their source targets
  exist locally. Public main links await the approved merge. This was not a live PyPI preview.
- uv 0.11.28: no-sync used the installed command; normal run synced a missing dependency; exact
  sync removed the undeclared tool; declaring it as a dev dependency retained it after sync.
- Disabled workflow YAML/structure checked; action SHAs verified through official repository APIs.
  Standards review found two issues, both fixed and re-reviewed with no new findings. Spec review
  found one missing maintainer prerequisite, now documented.

## What still needs authorization or external completion

Authorize push/PR to run the prepared Windows and Ubuntu artifact jobs and remaining CI matrix.
Linux/macOS and other Python versions have not been exercised for B1. Resolve PR #1 and approve
merging separately; a later merged source needs new acceptance.

The package was not available at its PyPI JSON endpoint (HTTP 404 on 2026-09-10); releases and tags
were absent. Recheck before publication; this does not reserve the name. No B1 public distribution
or PyPI download acceptance is claimed.

Before enabling the disabled template, verify a private security-reporting channel, protected
`pypi` GitHub Environment and PyPI Trusted Publisher fields in the [checklist](../releasing/README.md).
Then obtain explicit authorization for final source/workflow activation and exact-file publication.
No push, PR creation, merge, tag, GitHub Release, package upload, secrets or permission changes
were performed in B1. The final manifest/logs remain outside the repository to avoid self-reference.
