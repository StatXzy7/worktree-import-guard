# worktree-import-guard

> 测试通过了，却可能测的是另一份源码。

你改的是 **feature**，Python 加载的却是 **main**。本工具在 pytest 实际运行时发现这个来源差异。
[English](README.md)

下面来自[真实运行记录](docs/demo-output.txt)，只保留关键行；`<demo>` 替换临时目录。
这是示例展示，不是在扫描你的电脑：

```text
1. Ordinary pytest:
1 passed in 0.04s

2. Check wrong source:
Tests passed.
WORKTREE IMPORT GUARD: FAIL
expected: <demo>\feature\src\demo_pkg
observed: <demo>\main\src\demo_pkg\__init__.py (demo_pkg)
reason:   CROSS_WORKTREE_IMPORT

3. Select correct source inside this example:
Tests passed.
WORKTREE IMPORT GUARD: PASS
```

## 安装到已有测试环境

**目前是公开源码预览，不是正式 PyPI 发行版。** 无须联系作者索取 wheel。
需要 Python、pip、Git，以及下载源码、构建依赖和 pytest 的网络连接。以下固定提交已验证，
项目仍处于 alpha 阶段。

检查自己的项目时，使用平时能运行该项目 pytest 的环境。`.venv` 只是这个**现有环境**的示例，
请替换为实际路径。若还没有 Python 测试项目，先看上面的真实示例即可，不必安装。

Windows PowerShell（无须激活环境或修改执行策略）：

```powershell
& ".venv\Scripts\python.exe" -m pip install "git+https://github.com/StatXzy7/worktree-import-guard.git@edae3e6fa9a0b065385a080c371c9c17728b4656"
```

Linux / macOS：

```sh
".venv/bin/python" -m pip install "git+https://github.com/StatXzy7/worktree-import-guard.git@edae3e6fa9a0b065385a080c371c9c17728b4656"
```

安装会满足工具的 pytest 依赖要求，保留已符合版本范围的依赖。**从旧的 0.1.0 预览升级时**，
完成上述安装后，再按[只更新工具的命令](docs/troubleshooting.md#refresh-an-older-source-preview)替换
同版本旧代码，不重装 pytest。若已安装这个确切预览，直接检查即可。排查现场时不要先 sync 或修复待测项目。

## 选择一个入口

| 先体验 | 检查我的项目 |
| --- | --- |
| `wt-import --demo` | `wt-import --setup` |
| 用已安装工具运行离线临时示例。 | 确认项目与环境、选择包目录、确认保存并运行测试。 |

使用与上述 Python 属于同一环境的程序：

```powershell
& ".venv\Scripts\wt-import.exe" --demo
& ".venv\Scripts\wt-import.exe" --setup
# 首次设置后，每次只需：
& ".venv\Scripts\wt-import.exe" -- -q
```

```sh
".venv/bin/wt-import" --demo
".venv/bin/wt-import" --setup
# 首次设置后：
".venv/bin/wt-import" -- -q
```

在项目根目录运行设置，输入候选包编号，最后检查即将保存的内容。向导生成 `.wt-import.json`，
你不必手写。多个候选必须明确选择，已有配置不会被覆盖；向导不安装、激活或修复环境。
[配置与特殊布局](docs/first-use.md)。

Demo 只在私有临时目录中故意选择错误来源，不检查你的项目。有 Git 时创建真实 worktree，
没有 Git 时标注为两份普通目录。安装后不再下载依赖。
[维护者 Demo](examples/cross-worktree-demo/README.md) 另行验证完整 editable 安装链。

## 分别看测试结果和来源结果

| 来源结果 | 含义 | 下一步 |
| --- | --- | --- |
| PASS | 本次观察到的指定包来源符合目录要求。 | 还要看 pytest 是否通过。 |
| FAIL | 观察到的代码来自指定目录之外。 | 比较 expected/observed，检查选中的环境与安装来源。 |
| UNKNOWN | 这次无法完成来源检查。 | 看 reason/next；可能未观察到包，或来源无法解析。 |

**测试失败、来源 PASS，仍然表示测试失败。UNKNOWN 不能当作通过。**
保留 pytest 原生非零退出码；pytest 成功时，PASS / FAIL / UNKNOWN 分别退出 0 / 1 / 2。
没有测试保留 pytest 退出码 5。JSON 写入失败也不会掩盖 pytest 失败。

## 前提与边界

已在 Windows 与 POSIX CI 中测试 CPython 3.10–3.13、pytest >=8.2,<10。
只检查选定包、其已观察子模块和本次受支持 pytest 进程，不证明覆盖率、未执行代码正确性、
源码等于某个 commit，也不追踪子进程。启用 xdist 或多根 namespace 的布局不受支持。
只有 Git 证据确定时才称为跨 worktree。工具不是沙箱，pytest 仍会执行代码并产生副作用。

请使用项目的真实环境。`pipx`、`uvx`、`uv tool install` 使用独立工具环境，不作为推荐入口。
[排障与 uv 用法](docs/troubleshooting.md)。

## 显式检查与更多信息

自动化或单次检查可以不设置配置，直接运行：

```sh
wt-import --expect demo_pkg=src/demo_pkg -- -q
```

flat 布局使用 `demo_pkg=demo_pkg`。左边是 Python 的 import 名称，未必等于 pip 安装名；
右边是源码包目录，不是仓库根目录。多个包重复写 `--expect`，本次显式目标完全替代保存的目标。
路径有空格时给整个映射参数加引号。

`--cwd backend` 改变 pytest 目录及显式相对路径基准；配置路径相对配置文件。
`--report-json provenance.json` 相对最初调用目录保存 UTF-8 证据，`--show-all` 展开匹配来源。
CI 缺少配置和显式目标时立即退出 2，不等待输入；设置向导需要交互终端。

[保留在现有 pytest 流程中](docs/pytest-workflow.md) · [首次设置详情](docs/first-use.md) ·
[运行范围](docs/runtime-scope.md) · [JSON schema v2](docs/json-schema-v2.md) ·
[贡献](CONTRIBUTING.md) · [安全](SECURITY.md) · [变更记录](CHANGELOG.md) ·
[基准](benchmarks/README.md) · [正式发布步骤](docs/releasing/README.md)

固定源码提交早于本次首页重写，因此该安装包内的 README 仍含旧安装说明。当前入口请以本仓库首页为准，或访问
[该预览提交的文档](https://github.com/StatXzy7/worktree-import-guard/tree/edae3e6fa9a0b065385a080c371c9c17728b4656/docs)。
