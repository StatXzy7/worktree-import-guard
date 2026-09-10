# Runtime scope and evidence

## What is observed

The command installs observation before lazily importing pytest. It combines CPython audit import
events with incremental target capture at import returns and full `sys.modules` snapshots at
observer/pytest lifecycle boundaries. Cached unrelated imports do not scan the full module table.
For each selected package and loaded submodule, it evaluates `__spec__.origin`, `__file__`, and
namespace search locations. Canonical path operations handle dot segments, symlinks, Windows case
normalization, separators, spaces, and component boundaries; string-prefix containment is never
used.

For a one-off incident, manually checking `package.__file__` is a valid solution. The value of
this tool is making the check repeatable, covering selected submodules, producing deterministic
exit codes and JSON, and allowing it to be retained in a test, CI, or coding-agent workflow.


## Namespace packages

Packages without `__init__.py` may be namespaces. More than one search root is UNKNOWN
(`UNSUPPORTED_NAMESPACE_LAYOUT`). The guard does not choose one root to manufacture PASS.

See [schema v2](json-schema-v2.md) for machine fields, reason semantics and exit priorities.
