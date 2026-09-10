# Reading the engine's v2 report

The authoritative schema is maintained in the engine's
[JSON contract](https://github.com/StatXzy7/worktree-import-guard/blob/main/docs/json-schema-v2.md).
This note only explains the consumer boundary; do not derive origins yourself.

`pytest.exit_code` is independent of `guard.status` (pass/fail/unknown).
`guard.complete` describes determinate target evidence; `observation_complete`
describes the supported observation lifecycle. FAIL can coexist with false flags.
UNKNOWN never becomes PASS, irrespective of completeness flags.

Native nonzero pytest exits, including 6 on versions providing it, win over guard
status. With pytest exit zero, pass/fail/unknown map to process exits 0/1/2.
A JSON write failure may exit 2 after successful tests and leaves no usable report.

Targets contain package, expected_root, status, reasons and observations. Show the
most relevant observed canonical_origin and expected_root. CROSS_WORKTREE_IMPORT
supports another-worktree wording. OUTSIDE_EXPECTED_ROOT alone does not.
TARGET_NOT_OBSERVED calls for checking spelling and the authorized test selection;
ORIGIN_UNRESOLVED calls for inspecting metadata. OBSERVATION_ERROR signals an
incomplete capture lifecycle; preserve any separate proven FAIL.

Use the helper's fresh envelope/report pair. Missing, malformed, unsupported or
identity-inconsistent JSON cannot be replaced by a cached report or terminal text.
These checks prevent accidental misassociation, not malicious report forgery.
