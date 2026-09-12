# Let a local coding agent check the source

**Experimental local Codex Skill.** Ask your coding agent to check where pytest
loaded your package from. Deterministic helper tests and real user observations are
reported separately in [validation evidence](skill-validation.md).

From a checkout of this repository, run the bundled installer to copy **only**
`skills/verify-worktree-imports` into your test project's `.agents/skills/verify-worktree-imports`
directory. Preserve its `SKILL.md`, scripts, references, agents metadata and license.
Do not overwrite an existing installation.

From this repository root, run:

```console
python skills/verify-worktree-imports/scripts/install_skill.py /absolute/project
```

Open that project in local Codex and ask:

> Use $verify-worktree-imports to check where pytest loaded this project.
> Do not repair my environment.

中文：

> 使用 $verify-worktree-imports 检查这次 pytest 是否加载了别的 worktree 的源码，先别修环境。

The host must be able to run commands on the machine containing the project and
its existing pytest environment. Installing the Skill, installing the Python
detector, and selecting that environment are three separate steps. First use may
need one environment/installation confirmation. Already configured, authorized
projects reuse their settings without another setup. Tests still execute normally.

CLI compatibility for this Skill is the released route:

- `worktree-import-guard==0.1.2` (alpha release)
- `wt-import --setup` then `wt-import --doctor`
- same environment, same interpreter, same workflow command

## Existing pytest workflow recipe

After switching worktrees, ask for the same test selection you normally use, with
your already confirmed Python environment. The agent reuses `.wt-import.json`,
runs guarded pytest once, then reports tests and source separately. It does not
sync the environment before diagnosis. If source FAIL points elsewhere, inspect
the reported installation metadata before deciding on a repair.

The repository docs describing the workflow use the public install route and the
same `wt-import -- -q` runtime command after setup.
