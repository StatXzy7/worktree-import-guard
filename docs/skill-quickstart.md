# Let a local coding agent check the source

**Experimental local Codex Skill.** Ask your coding agent to check where pytest
loaded your package from. Deterministic helper tests and real agent sessions are
reported separately in [validation evidence](skill-validation.md).

From a checkout of this repository, copy **only** `skills/verify-worktree-imports`
into your test project's `.agents/skills/verify-worktree-imports` directory. Preserve
its `SKILL.md`, scripts, references, agents metadata and license. Do not overwrite
an existing installation without reviewing it. The source `skills/` folder is not
itself a Codex discovery directory. This is a local experimental import, not a
plugin marketplace installation.

Open that project in local Codex and ask:

> Use $verify-worktree-imports to check whether pytest loaded another checkout's
> source. Do not repair my environment.

中文：

> 使用 $verify-worktree-imports 检查这次 pytest 是否加载了别的 worktree 的源码，先别改环境。

The host must be able to run commands on the machine containing the project and
its existing pytest environment. Installing the Skill, installing the Python
detector, and selecting that environment are three separate steps. First use may
need one environment/installation confirmation. Already configured, authorized
projects reuse their settings without another setup. Tests still execute normally.

CLI compatibility: pinned 0.1.0 source preview from README or the 0.1.1 candidate;
report schema v2. The 0.1.1 candidate is not yet a PyPI release. No model API key,
MCP server or separate backend is introduced; the Codex host has its own account
and usage requirements.

Codex documents `.agents/skills` discovery and `$` invocation; if the Skill does
not appear, restart Codex. The local installation smoke checks resource independence;
it does not establish every desktop/IDE version or implicit-trigger reliability.
Other hosts are unverified. Plugin packaging is deferred until its installation
can be tested in a real host; there is one canonical Skill source.

## Existing pytest workflow recipe

After switching worktrees, ask for the same test selection you normally use, with
your already confirmed Python environment. The agent reuses `.wt-import.json`,
runs guarded pytest once, then reports tests and source separately. It does not
sync the environment before diagnosis. If source FAIL points elsewhere, inspect
the reported environment's installation metadata before deciding on a repair.

Official references checked for this implementation:
[Skills](https://learn.chatgpt.com/docs/build-skills),
[plugins](https://learn.chatgpt.com/docs/build-plugins),
[Agent Skills format](https://agentskills.io/specification).
