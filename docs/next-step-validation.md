# Next-step validation summary (2026-09-11)

This note records what was verified in the working tree after the A/B/C increment. Raw logs belong
in CI artifacts or a disposable output directory, not in the repository.

## Baseline at verification time

| Item | Value |
| --- | --- |
| HEAD | `fdb86af60ec54cd3022208243f04d7aed7473d18` (reference commit; incremental changes applied locally) |
| Package version | `0.1.1` candidate |
| Local Python | CPython 3.13.9 |
| Local pytest | 8.4.2 |
| PyPI package page | Not verified in this session (treat as unpublished) |
| Skill host evidence | `STATIC_AND_HELPERS_VERIFIED; HOST_UNVERIFIED` |

## Reference findings — current status

| # | Finding | Status after this increment |
| --- | --- | --- |
| 1 | README pinned `edae3e6` but recommended `--doctor` | Fixed: public README uses `--setup`; `--doctor` documented only for 0.1.1 candidate |
| 2 | Install used explicit Python but examples used bare `wt-import` | Fixed: Quick Start keeps one environment throughout |
| 3 | `--doctor` was alias of `--setup`; unusable with existing config | Fixed: `--doctor` reuses valid config with one confirmation |
| 4 | Release docs said workflow disabled while `release.yml` exists | Fixed: docs distinguish enabled workflow from unpublished PyPI state |
| 5 | Skill host still `HOST_UNVERIFIED` | Unchanged: helper tests expanded; no fabricated Codex session pass |
| 6 | Duplicate helper implementations | Not introduced; existing scripts extended |
| 7 | Version compatibility scattered | Fixed: shared `compatibility.py`; Skill scripts import it |

## Work package scope delivered

- **A:** Public README/quickstart consistency, README command tests, release doc alignment.
- **B:** Reusable `--doctor`, actionable `preflight.py` with `problem_details`, regression tests.
- **C:** Evidence-dir symlink ordering fix, validation doc refresh, no false host pass claim.

## External actions still required

1. Configure PyPI Trusted Publisher and protected `pypi` environment (not done here).
2. Dispatch `.github/workflows/release.yml` with explicit authorization.
3. Download published files from PyPI, verify hashes, smoke-test install/help/demo/check.
4. Only then switch public README to `pip install worktree-import-guard==0.1.1`.
5. Retest Codex host sessions with authorized evidence directory when host policy allows.

## Not in scope

Plugin marketplace, MCP, telemetry, environment repair, xdist/multi-root support, observer rewrite,
remote publication, or claiming user-adoption statistics.
