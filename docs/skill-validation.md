# Skill validation evidence

The Skill is experimental. Static packaging, deterministic runner behavior, actual
Codex sessions, and external user adoption are distinct evidence layers.

Implementation host: Windows, Codex CLI 0.146.0. The CLI reports a ChatGPT login.
The target test interpreter is explicitly selected for each disposable fixture.
The session fixtures imported only the Skill folder into `.agents/skills` inside
independent disposable Git projects. They did not depend on `../../src`. Codex
discovered/read that installed Skill when explicitly invoked with `$verify-worktree-imports`.

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

## Actual local host attempts, 2026-09-11 (Asia/Shanghai)

Session Skill source: `dbadf809e397d61a1f98af2d254bbb261f0abc00`, before the
subsequent interpreter-alias/native-exit fixes. CLI: 0.1.1 from this repository's
development editable installation, CPython 3.13.9, pytest 9.1.1. It was not a PyPI
installation. These sessions used Codex's existing ChatGPT login and inherited
host policy; no paid external API fallback or permission bypass was attempted.
The CLI warned about missing cached model metadata and shortened Skill descriptions.

The check prompt explicitly named the installed Skill, confirmed interpreter and
`-q`, authorized that selection, and prohibited installation/repair/config writes.
Refusal selected a separate empty venv and prohibited any substitute environment.
Demo/explanation prompts explicitly prohibited project tests.

| Session | Observed behavior | What was established |
| --- | --- | --- |
| Existing config | Read Skill/config; invoked helper once; command exited 1 without an envelope; temporary evidence read denied | Honest unverified response; no complete source result |
| Wrong source fixture | Reused config and invoked helper once; command exited 1 without an envelope | Did not infer source FAIL or PASS from the process exit |
| Unobserved target fixture | Invoked helper once; host command timed out at 120 seconds; evidence reads denied | Correctly distinguished tool timeout from a pytest exit; UNKNOWN interpretation from an actual report remains unverified |
| Test failure / correct-source fixture | Invoked helper once; exited 1 without envelope/output; evidence read denied | Kept both outcomes unverified instead of treating the process exit as an engine report |
| Installation refusal | Inspected the selected empty environment; Python probes failed; stopped | No pip, repair, project test or substitute environment used |
| Demo only | Attempted private demo in selected environment; exited 1 without output | Reported unavailable demo; did not check the user's project |
| Explanation only | Read local report reference, then explained scoped PASS and independent test outcome | No tests/demo/install/config writes |

One real session excerpt (not a successful check story): “No usable verification
result was obtained.” It explained that the invocation returned no bound envelope,
kept both test/source outcomes unconfirmed, and did not rerun tests or fix the
environment. This is useful boundary evidence, not an AGENT_FLOW_VERIFIED result.

**Status: STATIC_AND_HELPERS_VERIFIED; HOST_UNVERIFIED.** Real execution and
PASS/FAIL/UNKNOWN explanation end-to-end have not been established in this host.
The 2026-09-11 increment added reusable `--doctor`, structured Skill preflight
`problem_details`, README/public-entry consistency tests, and evidence-directory
symlink rejection before path resolution. Retest the seven manual session cases
after host policy allows reading the exact per-invocation evidence path.

The [sanitized session record](skill-session-evidence.json) preserves user prompts,
actual command summaries, final replies and transcript hashes. Full local logs are
not distributed with the Skill. There were seven explicit sessions, not seven
successful checks or a measurement of implicit triggering.
