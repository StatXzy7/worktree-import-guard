# B0 release-candidate readiness

## Decision

**BLOCKED** for B0 completion because the candidate has not been pushed and no real GitHub Actions
workflow or job has run. Local release-preparation evidence is complete for the recorded Windows
environments and exact artifacts below. This decision does not mean the package was released or
authorize any upload.

## Source identities

- Alpha baseline: `dd4c5e468f3b029fab8d196eee36b8a1c9625b88`.
- Tested candidate source: `4ff2ed30652f70b4ee1e115e6626ad63ced7166a` on local branch
  `codex/b0-release-candidate`.
- The candidate was two commits ahead of `origin/main` and clean at test start. Ignored coverage
  and distribution files do not alter that Git identity.
- This readiness record and its copied logs are committed after the tested source. Resolve the
  report commit with `git log -1 --format=%H -- docs/release-readiness`; it is intentionally not
  embedded here, avoiding a self-referential SHA.

No observer redesign or V0.2 feature was added. B0 changes were limited to retaining a
deterministic wrong-origin failure when evidence or observation is incomplete, golden schema
coverage for those cases, small plugin/import-mode smokes, resolvable development dependencies,
CI evidence capture, artifact skip enforcement, and pre-release installation wording.

## Local checks

All commands below ran against the clean tested candidate on Windows 11, CPython 3.13.5,
pytest 9.1.1, pytest-cov 7.1.0, pytest-asyncio 1.3.0, and pytest-xdist 3.8.0 unless noted.

| Check | Result | Evidence |
| --- | --- | --- |
| `ruff check .` | pass | `01-ruff.txt` |
| `mypy src` | pass, 10 source files | `02-mypy.txt` |
| `pytest -q -rs` | 46 passed, 1 skipped | `03-pytest.txt` |
| pytest with coverage | 46 passed, 1 skipped; 92.42% | `04-coverage.txt` |
| `python -m build` | wheel and sdist built | `05-build.txt` |
| Explicit installed-artifact entry | 1 passed, 0 skipped | `07-artifact-test.txt` |
| sdist rebuild/install outside repository | pass | `08-sdist-chain.txt` |
| installed-wheel Hero Demo | pass | `09-hero-demo.txt` |
| plugin/import-mode smokes | 4 passed | `10-plugin-compat.txt` |
| Python 3.11.1 + pytest 8.2.0 boundary | 46 passed, 1 skipped | `11-py311-pytest820.txt` |

The regular-suite skip is exactly
`tests/artifact/test_installed_worktrees.py::test_wheel_console_scripts_pth_and_pep660_across_worktrees`:
`set WTIG_RUN_ARTIFACT_TESTS=1 to run installation smoke tests`. It is intentional because the
test has a separate installed-artifact entry. The explicit entry used the frozen wheel via
`WTIG_ARTIFACT_WHEEL`, and the actual result was `1 passed`; it was not an all-skip success.

The pytest 8.2.0 check was resolved in one pip transaction with the development extra. It selected
pytest-asyncio 1.3.0, which is compatible with the declared pytest floor. pytest-asyncio emitted a
deprecation warning about its future default fixture loop scope; the smoke uses no async fixture,
and this warning is recorded rather than suppressed.

## Frozen local artifacts

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `worktree_import_guard-0.1.0-py3-none-any.whl` | 20,761 | `48f8b457a84f4fcfaa01f66e757ee6da8fee2088e078b4b425cabdb98681f240` |
| `worktree_import_guard-0.1.0.tar.gz` | 36,344 | `997be746445603bbc726e801cf6afa9042aa42e8615be5639eb88abac2110629` |

They are stored under
`dist/b0-4ff2ed30652f70b4ee1e115e6626ad63ced7166a/`. The build used `build 1.6.0`
and isolated `hatchling 1.32.0`. Rebuilding the sdist outside the repository produced a wheel with
the same 20,761-byte size and complete SHA-256 as the frozen wheel; this is a result of this local
run, not a cross-environment reproducibility promise.

The wheel was installed into the artifact test's clean environment and produced:

- native pytest success with a stale `.pth`, followed by guard exit 1 and
  `CROSS_WORKTREE_IMPORT`;
- native pytest success with a real PEP 660 editable install from the wrong worktree, followed by
  guard exit 1 and `CROSS_WORKTREE_IMPORT`;
- guard exit 0 after reinstalling the same editable project from the correct worktree.

The Hero Demo used that same frozen wheel. Ordinary pytest returned 0 against the stale main
editable; the guard retained pytest exit 0 but returned process exit 1 with both actual main
worktree module paths; the correct feature editable returned guard exit 0.

## Schema v2 and compatibility

Schema v2 remains independent of package version 0.1.0. Golden reports cover pass, fail, unknown,
incomplete evidence with a retained fail, incomplete observation, pytest interruption, pytest
usage error, and no-tests exit. Integration coverage also confirms report-write failure cannot
mask an existing nonzero pytest exit. Raw `sys.executable`, resolved binary, `sys.prefix`,
`sys.base_prefix`, Python version, and pytest version remain separate report fields.

The compatibility smokes passed for pytest-cov native and guarded execution, pytest-asyncio,
correct and wrong origins under `--import-mode=importlib`, xdist installed but inactive, and
`-n 0`. Active `-n 2` remains deliberately unsupported and returns native pytest usage exit 4
with `observation_complete=false`. Coverage data and import provenance are separate claims.

## Performance record

`benchmarks/results/2026-09-10-windows-python313.md` was inspected and retained rather than rerun.
It includes all seven raw samples, medians/ranges, requested module counts, suite file counts,
Python/pytest versions, plugin auto-load setting, execution order, and correctness metrics. Its
negative large-suite deltas remain explicitly treated as noise, and the cached-import improvement
is not described as a universal pytest speedup.

## Remote state and block

At `2026-09-10T11:30:35.7939143Z`, read-only GitHub API queries confirmed repository
`StatXzy7/worktree-import-guard`, `main` at
`dd4c5e468f3b029fab8d196eee36b8a1c9625b88`, only the `main` branch, zero workflows, and zero
workflow runs. All four action commit pins in the proposed workflow resolve in their official
repositories. No candidate CI run ID, run attempt, job, checkout SHA, or uploaded artifact exists.

The remote candidate branch name does not currently collide. With maintainer authorization, the
checked commands are:

```console
git push --set-upstream origin codex/b0-release-candidate
gh pr create --repo StatXzy7/worktree-import-guard --base main --head codex/b0-release-candidate --title "Harden provenance checks and freeze B0 candidate"
```

After that, record the actual workflow run and every required job, including event, run attempt,
PR head SHA, workflow SHA, checkout HEAD, platform, Python/pytest versions, and uploaded artifact
hashes. A PR synthetic merge commit must not be relabeled as the PR head or final merge commit.

## Remaining scope and release boundary

Linux, macOS, the remote Python 3.10–3.13 matrix, a PR merge SHA, and a final merged candidate are
unverified. Current-process only, no child-process provenance, and no active xdist aggregation are
product limits. No broader plugin support is claimed.

The legacy `D:\temp\wtig-sdist-smoke-b9b003e6c18649cda4e0f239e27a8727` directory still exists
and contains a `venv` directory. It was not deleted, modified, elevated, or used as a release
blocker.

Future order is: authorized branch/PR sync; real CI inspection and fixes if needed; candidate
approval; B1 release notes and controlled procedure; then a separate B2 maintainer authorization
for tag, GitHub Release, or PyPI/TestPyPI upload of the approved files. No push, PR, release, tag,
upload, permission/ruleset/environment/secret/Trusted Publisher change, or publishing permission
was performed in B0.
