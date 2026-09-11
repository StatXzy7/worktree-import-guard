# 0.1.1 candidate quick start

Maintainer and early-tester documentation. **Not** the public README install target until a real
PyPI release is downloaded, hash-verified, and smoke-tested. [简体中文摘要](#简体中文摘要)

## What the candidate adds

- `--doctor` reuses saved `.wt-import.json` for repeat checks; `--setup` still refuses to overwrite.
- Skill `preflight.py` returns `ready`, `needs_selection`, or `missing_conditions` with actionable
  `problem_details` before any guarded pytest.
- `run_check.py` binds each invocation to a fresh report and validates runtime/cwd/target identity.

Report schema v2, reason codes, and pytest exit semantics remain compatible.

## Install the candidate

Use the project's existing pytest environment. Replace `.venv` with the real path.

From a verified maintainer wheel (after `python -m build` and candidate checks):

```sh
".venv/bin/python" -m pip install /absolute/path/to/worktree_import_guard-0.1.1-py3-none-any.whl
```

```powershell
& ".venv\Scripts\python.exe" -m pip install "D:\absolute\path\to\worktree_import_guard-0.1.1-py3-none-any.whl"
```

From an exact candidate commit (only after that commit passes maintainer verification):

```sh
".venv/bin/python" -m pip install "git+https://github.com/StatXzy7/worktree-import-guard.git@<candidate-sha>"
```

Always invoke the console script from the same environment:

```sh
".venv/bin/wt-import" --version
".venv/bin/wt-import" --demo
".venv/bin/wt-import" --doctor
".venv/bin/wt-import" -- -q
```

```powershell
& ".venv\Scripts\wt-import.exe" --version
& ".venv\Scripts\wt-import.exe" --demo
& ".venv\Scripts\wt-import.exe" --doctor
& ".venv\Scripts\wt-import.exe" -- -q
```

Do not substitute `python -m worktree_import_guard.cli`; console-script launch semantics differ.

## Repeat checks with `--doctor`

| Situation | Behavior |
| --- | --- |
| No `.wt-import.json` | Same three-step wizard as `--setup`. |
| Valid saved settings | Shows config path, targets, Python environment; one confirmation; no file rewrite. |
| Broken config | Reports the actual file and error; does not overwrite or guess targets. |
| Non-interactive | Clear usage error; no waiting for input; no pytest. |

Automation should continue using `wt-import -- -q` or `--expect PACKAGE=PATH -- -q`.

## Skill preflight before guarded pytest

```text
<project-python> <skill>/scripts/preflight.py --cwd <project>
```

Resolve `problem_details[].next_step` before calling `run_check.py`. Preflight never installs,
repairs, saves configuration, or runs project tests.

## 简体中文摘要

候选版尚未成为公开 README 安装入口。安装 wheel 或精确候选提交后，始终用同一环境中的
`wt-import` console script。`--doctor` 在有配置时复用 `.wt-import.json` 并只确认一次；
`--setup` 仍不覆盖已有文件。Skill 先运行 `preflight.py`，再运行 `run_check.py`。
