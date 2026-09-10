# Skill validation evidence

The Skill is experimental. Static packaging, deterministic runner behavior, actual
Codex sessions, and external user adoption are distinct evidence layers.

Implementation host: Windows, Codex CLI 0.146.0. The CLI reports a ChatGPT login.
The target test interpreter is explicitly selected for each disposable fixture.
Local session attempts and final results are recorded below before final delivery.

Ordinary CI exercises golden schema v2 pass/fail/unknown/incomplete/observation-error
reports, native nonzero pytest exits, runtime/cwd/target/argument mismatches, missing
or damaged fresh reports, stale PASS files, literal malicious-looking arguments,
missing CLI, standalone resource copying, and real console-script checks from
independent Skill folders with non-ASCII/space paths. These tests do not measure
whether a language model will choose the correct environment or ask for permission.

Artifact checks install the exact candidate wheel outside the repository and run
the standalone helper, including upgrading the actual old source preview.

Manual session cases: configured project, wrong source, UNKNOWN, test failure with
source PASS, installation refusal, explanation-only and demo-only. Logs must show
the user prompt, actual tools and result; a hand-run helper is not a Skill session.
No implicit trigger success rate is claimed. External pilot status: NOT_STARTED.
