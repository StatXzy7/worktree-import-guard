# Changelog

All notable changes to this project are documented here.

## 0.1.0 — Unreleased candidate

### Changed

- Reworked onboarding around the existing pytest environment, with src/flat layouts and Chinese.
- Separated test outcomes from source checks and added actionable help and error explanations.
- Human output retains WORKTREE IMPORT GUARD, expected, observed, reason, pytest exit and guard
  markers; per-target status and next steps are new. JSON v2, reasons and exit policy are unchanged.
- Demo validates actual wrong-worktree evidence and reports cleanup leftovers honestly.
- Added runtime-only onboarding checks and a disabled Trusted Publishing workflow template.

- Replaced full module-table scans at every import return with incremental target capture and
  lifecycle fallback snapshots.
- Frozen filesystem origin evidence at observation time and avoided dynamic module attribute
  access during metadata capture.
- Added JSON schema v2 with unambiguous evidence/observation completeness, preserved virtualenv
  identity, runtime versions, and observation metrics.
- Preserved an existing pytest failure when JSON report writing also fails.

### Added

- Installed-wheel tests for ordinary `.pth` and PEP 660 editable cross-worktree failures, with a
  correct-worktree control.
- Pinned public CI, wheel/sdist smoke checks, golden reports, independent benchmarks, and a
  disposable executable demo.

### Initial capabilities

- Explicit repeatable `PACKAGE=PATH` runtime provenance contracts.
- Early CPython import observation and pytest lifecycle snapshots.
- Canonical origin matching, conservative unknown results, and fixed reason codes.
- Best-effort NUL-delimited Git worktree context.
- Human and schema-versioned JSON reports with documented exit semantics.
- Unit tests and a real cross-worktree integration fixture.
