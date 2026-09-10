# JSON report schema v2

Schema v2 makes runtime identity and completeness explicit while keeping the existing status and
reason-code model.

## Completeness

- `guard.complete` is true only when every target is `pass` or `fail`. Any `unknown` target makes
  it false, including a mixed run whose overall status is `fail`. It is also false when a
  deterministic failure coexists with unresolved evidence for that target; the failure remains
  visible and authoritative, but the evidence set is not complete.
- `guard.observation_complete` reports whether the supported observation lifecycle completed. It
  is false for an unsupported runtime/scope. It does not claim that every target yielded usable
  evidence.
- `unknown` never becomes `pass`, regardless of either completeness field.

In schema v1, `guard.complete` represented what v2 calls `guard.observation_complete`. A v1
consumer that needs evidence completeness must inspect every target status. Consumers must branch
on `schema_version`; silently applying v1 meaning to v2 is unsupported.

## Migrating from v1

- Branch on the integer `schema_version` before interpreting fields; schema and package versions
  are independent.
- In v2, use `guard.complete` for determinate evidence and `guard.observation_complete` for the
  supported single-process observation lifecycle.
- Read the added `run.python_resolved`, `run.sys_prefix`, `run.sys_base_prefix`,
  `run.python_version`, and `run.pytest_version` fields without discarding raw `run.python`.
- Treat the added `metrics` object as diagnostic data, not a pass criterion.

## Runtime identity

`run.python` preserves the executable path used to start `wt-import`, including a virtual
environment or symlink identity. `run.python_resolved` records the canonical binary separately.
`run.sys_prefix`, `run.sys_base_prefix`, `run.python_version`, and `run.pytest_version` make the
selected environment auditable without guessing from a resolved executable.

## Metrics

`metrics` contains diagnostic counters and timings from the guarded process:

- `import_returns`: wrapped built-in/importlib/reload return boundaries;
- `incremental_captures`: boundaries that had target candidates to inspect;
- `full_snapshots`: lifecycle-wide `sys.modules` scans;
- `observations`: distinct retained target metadata records;
- `guarded_wall_seconds`: guarded in-process elapsed time;
- `pytest_collection_seconds`: pytest session start through collection finish.

The metrics are measurement aids, not a service-level guarantee. External process wall time is
intentionally measured by `benchmarks/pytest_overhead.py`.

## Exit priority

When pytest exits nonzero, its exit code is retained even if provenance fails, is unknown, or JSON
writing fails. With pytest exit 0, guard pass/fail/unknown map to 0/1/2. If JSON writing fails after
pytest exit 0, the command exits 2 and writes a diagnostic to stderr.

Exact pass/fail/unknown examples live in `tests/golden/schema-v2-*.json`.
# Observation failures (additive schema v2 fields)

`OBSERVATION_ERROR` means the observer failed to capture supported imports. Such a run is
UNKNOWN unless retained evidence already proves a mismatch (which remains FAIL).
Both completeness flags are false. When errors exist, `guard.observation_errors` contains
up to 20 capture-phase and exception-type strings. Ordinary import failures do not by
themselves set this field. Existing fields and successful-report shapes are unchanged.
