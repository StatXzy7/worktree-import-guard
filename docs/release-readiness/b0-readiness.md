# B0 release-candidate readiness

## Decision

GO_FOR_RELEASE_PREPARATION. The authorized branch was pushed and
[PR #1](https://github.com/StatXzy7/worktree-import-guard/pull/1) was opened.
Both acceptance runs completed successfully, each with eight jobs. This authorizes entering
controlled release preparation only; no merge or publication has occurred.

## Source and report identities

- Original baseline: `dd4c5e468f3b029fab8d196eee36b8a1c9625b88`.
- Frozen candidate source / accepted PR head: `40b70c678d6d52bcfd1af4b39f6bef701e9e84e7`.
- The source working tree was clean when the candidate was tested locally and pushed.
- PR synthetic merge checkout: `ab650e1eec375fcc523d3dd9c8e60e0dc8fafbbd`.
- GitHub API confirmed that both commits have tree `dfd0723cd81439553af78feed3491dc570bb38a0`.
  They are distinct commit identities despite containing identical files.
- No final merged commit exists. The later report commit changes only acceptance documentation;
  resolve its identity with `git log -1 --format=%H -- docs/release-readiness`.
  It is not the source of the frozen files.

The old Windows-only candidate manifest is preserved in
[history/4ff2ed30-local-manifest.json](history/4ff2ed30-local-manifest.json).
Its artifacts and earlier blocked remote snapshot are historical evidence, not the accepted files.

## Changes made during remote acceptance

The first push run failed on Windows because test fixtures looked for console scripts beside the
base `python.exe`, although Windows base installations use a `Scripts` subdirectory.
`tests/conftest.py` and `benchmarks/pytest_overhead.py` now use the active interpreter's
`sysconfig.get_path("scripts")`. Missing scripts still fail explicitly; no PATH fallback or
inline Python replacement was introduced. The previously failing base-interpreter CI now passes.

`tests/integration/test_cli_provenance.py` now checks the installed pytest version's actual
warning-limit exit 6, including a simultaneous report-write failure, on versions defining
`MAX_WARNINGS_ERROR`. Pytest 8.2.0 never receives the newer option. README now describes
preservation of all nonzero native pytest states.

The artifact workflow now runs the Hero Demo using the downloaded wheel and records sdist-derived
wheel hashes and installed dependencies. No guard runtime architecture was rewritten.

## Real CI evidence

Repository: `StatXzy7/worktree-import-guard`; workflow: `.github/workflows/ci.yml`.

| Event | Run / attempt | Checkout and workflow SHA | Result |
| --- | --- | --- | --- |
| push | [34485447492 / 1](https://github.com/StatXzy7/worktree-import-guard/actions/runs/34485447492) | `40b70c678d6d52bcfd1af4b39f6bef701e9e84e7` | 8/8 success |
| pull_request | [34485453330 / 1](https://github.com/StatXzy7/worktree-import-guard/actions/runs/34485453330) | `ab650e1eec375fcc523d3dd9c8e60e0dc8fafbbd` | 8/8 success |

The following are six actual combinations, not a 3-by-4 Cartesian matrix. Every combination
returned 46 passed and one intentional artifact skip in both runs.

| Platform | Python | pytest | Push job | PR job |
| --- | --- | --- | --- | --- |
| ubuntu-latest | 3.10.21 | 8.2.0 | 102898478200 | 102898637791 |
| ubuntu-latest | 3.11.16 | 9.1.1 | 102898478219 | 102898637570 |
| ubuntu-latest | 3.12.14 | 9.1.1 | 102898477984 | 102898637607 |
| ubuntu-latest | 3.13.15 | 9.1.1 | 102898477800 | 102898637497 |
| windows-latest | 3.13.15 | 9.1.1 | 102898478305 | 102898637536 |
| macos-latest | 3.13.15 | 9.1.1 | 102898478006 | 102898637912 |

Quality/build jobs: 102898477931 and 102898637256. Both ran Ruff, mypy and coverage successfully;
coverage was 92.42%. Artifact jobs: 102898712382 and 102898874161. Each explicitly ran the
installed-wheel test (1 passed, 0 skipped), sdist rebuild/install and Hero Demo.

All job URLs, Python/pytest/plugin versions, checkout/workflow SHAs, artifact IDs and log paths
are recorded in [b0-manifest.json](b0-manifest.json).
[evidence/b0-ci-evidence.zip](evidence/b0-ci-evidence.zip) preserves GitHub API responses,
individual unabridged job logs, file identities and the Windows artifact-test JUnit report.
Within it, logs are named `ci-RUN_ID/job-JOB_ID.log`.

The first failed Windows run remains inspectable at
[34485171515](https://github.com/StatXzy7/worktree-import-guard/actions/runs/34485171515).
Superseded intermediate runs are not used as acceptance evidence.

## Frozen files and installation chain

These exact files were downloaded from the successful push run's `distributions` artifact.
The corresponding PR-run files were independently downloaded and have identical hashes.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `worktree_import_guard-0.1.0-py3-none-any.whl` | 20,777 | `b718e8d6804f1d8292cf84066a5f6cdb280689ddc014178ed91a24ff2a49fe28` |
| `worktree_import_guard-0.1.0.tar.gz` | 46,221 | `01708839e3feb0bbbdb39f5f3d3c70b6f6105546c99477cf12b7edf73bcdb06b` |

Local files: `dist/ci-34485447492/distributions/`. Candidate package version: 0.1.0;
schema version: 2. Builder: Ubuntu, Python 3.13.15, pytest 9.1.1, build 1.6.1,
isolated hatchling 1.32.0.

The artifact job installs the wheel in a new virtual environment outside the repository, runs
real pytest / wt-import console scripts, and proves native success plus guarded failure for
both an ordinary stale .pth and a real PEP 660 wrong-worktree editable. Reinstalling the fixture
from the correct worktree yields guard success. These setup actions belong to the fixture;
the guard does not fix the environment.

The sdist is independently rebuilt to a wheel and installed into another virtual environment.
Its derived wheel SHA-256 is `b718e8d6804f1d8292cf84066a5f6cdb280689ddc014178ed91a24ff2a49fe28`.
The installed console script runs from the runner temporary directory.

The downloaded CI wheel was additionally tested on local Windows / Python 3.13.5 using
`WTIG_RUN_ARTIFACT_TESTS=1`, its absolute `WTIG_ARTIFACT_WHEEL` path and
`pytest tests/artifact -q -rA --junitxml=dist/ci-34485447492/windows-artifact.xml`:
1 passed, 0 skipped, 83.22 seconds.

Later documentation commits can change an sdist rebuilt from HEAD because docs are packaged.
Such later files are not silently substituted for this frozen set. Cross-environment bitwise
reproducibility is not promised.

## Hero Demo output

The push artifact job used the frozen wheel and produced these actual paths and outcomes
(the complete output is in job 102898712382's archived log):

```text
ORDINARY PYTEST (stale main editable, expected exit 0)
1 passed in 0.01s

WORKTREE IMPORT GUARD: FAIL
expected: /tmp/wtig-demo-k368q5xk/feature worktree/src/demo_pkg
observed: /tmp/wtig-demo-k368q5xk/main repository/src/demo_pkg/__init__.py (demo_pkg)
observed: /tmp/wtig-demo-k368q5xk/main repository/src/demo_pkg/core.py (demo_pkg.core)
reason:   CROSS_WORKTREE_IMPORT
pytest exit: 0
guard:      FAIL

GUARD (feature editable, expected exit 0)
1 passed in 0.01s
WORKTREE IMPORT GUARD: PASS
pytest exit: 0
guard:      PASS
```

## Local quality, skip and compatibility scope

Against clean source 40b70c6, local Ruff and mypy passed, 18 integration/compatibility cases passed,
and the full coverage run returned 46 passed, 1 skipped in 85.95 seconds with coverage 92.42%.

The exact regular skip is
`tests/artifact/test_installed_worktrees.py::test_wheel_console_scripts_pth_and_pep660_across_worktrees`.
Reason: `set WTIG_RUN_ARTIFACT_TESTS=1 to run installation smoke tests`.
The CI artifact job asserts at least one genuinely passed test from JUnit, so all-skip success
cannot satisfy it. The explicit test passed on Linux and on the downloaded wheel on Windows.

All six CI combinations used pytest-cov 7.1.0, pytest-asyncio 1.3.0 and pytest-xdist 3.8.0.
Smokes cover native and guarded coverage, a small asynchronous test, correct/wrong importlib-mode
origins, xdist installed but inactive, -n 0, and rejection of active -n 2.

Schema-v2 golden/integration cases and runtime identity checks pass. Determinate wrong origins
remain FAIL even with unresolved evidence or incomplete observation. Evidence completeness and
observation completeness remain distinct. Coverage does not imply provenance or all-path coverage.

The previous Windows/Python 3.13 benchmark record was retained as historical measured samples;
no benchmark rerun or new performance claim was needed for fixture/CI-only changes.
Negative deltas remain measurement noise. This record does not imply a performance guarantee.

## Remaining boundaries and next stage

No B0 acceptance blocker remains for the frozen candidate. PR remains open; no merge was done.
Unverified combinations include Windows/macOS on Python 3.10-3.12, Python 3.14, unrelated plugins,
and any eventual merged commit or public distribution channel.

The guard observes only the current pytest process. Child-process imports and active xdist
aggregation remain unsupported. Namespace/malformed-origin restrictions remain unchanged.

Only authorized push and PR operations occurred. No release/tag, PyPI/TestPyPI upload, permissions,
rulesets, environment/secrets or Trusted Publisher changes occurred. No OIDC publish permission
was added. The legacy `D:\temp\wtig-sdist-smoke-b9b003e6c18649cda4e0f239e27a8727`
was left untouched.

B1 may now prepare release notes and controlled approval. B2 requires separate maintainer
authorization; approve the exact frozen files before any upload. A later merge/build must be
identified and validated rather than reusing a different artifact's acceptance.
