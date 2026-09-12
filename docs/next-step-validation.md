# Next-step validation summary (2026-09-11)

This note records what was verified in the working tree after the A/B/C increment and the
authorized 0.1.2 publication. Raw logs belong in CI artifacts or a disposable output directory,
not in the repository.

## Baseline at verification time

| Item | Value |
| --- | --- |
| HEAD | `8c17d5a` on `main` |
| Package version | `0.1.2` published |
| Local Python | CPython 3.13.9 |
| Local pytest | 8.4.2 |
| PyPI package page | **PUBLISHED_AND_SMOKED** — latest `0.1.2` (2026-09-11) |
| GitHub Release | `v0.1.2` at `8c17d5a` with wheel/sdist assets |
| Skill host evidence | `STATIC_AND_HELPERS_VERIFIED; HOST_UNVERIFIED` |

## Reference findings — current status

| # | Finding | Status after this increment |
| --- | --- | --- |
| 1 | README pinned `edae3e6` but recommended `--doctor` | Fixed: public README uses `pip install worktree-import-guard==0.1.2` and `--setup` first |
| 2 | Install used explicit Python but examples used bare `wt-import` | Fixed: Quick Start keeps one environment throughout |
| 3 | `--doctor` was alias of `--setup`; unusable with existing config | Fixed: `--doctor` reuses valid config with one confirmation; verified on PyPI 0.1.2 |
| 4 | Release docs said workflow disabled while `release.yml` exists | Fixed: release workflow published 0.1.2; docs distinguish workflow from index state |
| 5 | Skill host still `HOST_UNVERIFIED` | Unchanged: helper tests expanded; no fabricated Codex session pass |
| 6 | Duplicate helper implementations | Not introduced; existing scripts extended |
| 7 | Version compatibility scattered | Fixed: shared `compatibility.py`; Skill scripts import it |

## Work package scope delivered

- **A:** Public README/quickstart consistency, README command tests, release doc alignment.
- **B:** Reusable `--doctor`, actionable `preflight.py` with `problem_details`, regression tests.
- **C:** Evidence-dir symlink ordering fix, validation doc refresh, no false host pass claim.

## Publication evidence

| Check | Result |
| --- | --- |
| Release workflow | [run 34612206280](https://github.com/StatXzy7/worktree-import-guard/actions/runs/34612206280) — success |
| PyPI index | `0.1.2` latest; releases `0.1.1`, `0.1.2` |
| Wheel SHA256 | `1eabbc2873b2da9415ad2dd0bb5d7360009d48076dc0ecc655baad02f445682c` |
| sdist SHA256 | `ca770eeb7094497bcc949b94aedf2ebde53851d2a8273bbde94f9232065d3b6d` |
| GitHub Release | [v0.1.2](https://github.com/StatXzy7/worktree-import-guard/releases/tag/v0.1.2) |
| Post-index smoke (Windows, fresh venv) | `wt-import 0.1.2`; `--help` shows `--doctor`; `--demo` runs Hero Demo |

Artifact checks with `WTIG_RUN_ARTIFACT_TESTS=1` on Windows (CPython 3.13.9): **11 passed**
(candidate wheel via `WTIG_ARTIFACT_WHEEL`).

## External actions still required

1. Retest Codex host sessions with authorized evidence directory when host policy allows
   (`HOST_UNVERIFIED` → host-verified evidence).
2. External user trial per [user-validation.md](user-validation.md) — still `NOT_STARTED`.

## Not in scope

Plugin marketplace, MCP, telemetry, environment repair, xdist/multi-root support, observer rewrite,
remote publication beyond the authorized 0.1.2 release, or claiming user-adoption statistics.
