# worktree-import-guard

发现“pytest 通过了，却测试了另一份源码”的问题。
你修改当前 checkout 的代码后，Python 仍可能从另一份源码导入包；本工具在 pytest
实际运行时检查你指定的包来自哪里。[English](README.md)

## 快速开始

0.1.0 仍为候选版本，尚未作为正式 PyPI 版本发布。先向维护者取得
`worktree_import_guard-0.1.0-py3-none-any.whl`；目前没有公开的 B1 下载地址。
普通使用不需要克隆工具仓库、安装开发依赖或自行构建。

在**你项目的根目录**执行，使用**平时能运行该项目 pytest 的现有环境**。
`.venv` 只是示例，请替换为真实环境路径；wheel 路径也要替换。不要为诊断先重装待测项目。

Windows PowerShell（无需激活环境或修改执行策略）：

```powershell
& ".venv\Scripts\python.exe" -m pip install "C:\path to\worktree_import_guard-0.1.0-py3-none-any.whl"
& ".venv\Scripts\wt-import.exe" --expect demo_pkg=src/demo_pkg -- -q
```

Linux / macOS：

```sh
".venv/bin/python" -m pip install "/path/to/worktree_import_guard-0.1.0-py3-none-any.whl"
".venv/bin/wt-import" --expect demo_pkg=src/demo_pkg -- -q
```

安装可能安装或调整 pytest 等依赖。现场诊断时若工具已安装，先只运行检查命令，不先 sync。
Python 与 wt-import 必须属于同一环境。带空格的可执行文件路径、wheel 路径和整个映射参数
均需引号，例如 `--expect "demo_pkg=source tree/demo_pkg"`。

`--expect` 左边是 `import` 使用的包名，可能与 pip 安装名不同；右边是希望加载的源码包目录。
`src/demo_pkg/__init__.py` 对应 `demo_pkg=src/demo_pkg`；
`demo_pkg/__init__.py` 对应 `demo_pkg=demo_pkg`。不要只填仓库根目录，也不要填另一个 worktree。
多个包重复写 `--expect`。英文首页有两种完整目录树。

从父目录使用 `--cwd backend --expect demo_pkg=src/demo_pkg`，测试在 backend 中运行，
预期目录是 backend/src/demo_pkg；可执行文件路径仍从当前 shell 目录计算。
`--report-json` 相对路径从原始调用目录计算。没有 `__init__.py` 的布局请看
[namespace 限制](docs/runtime-scope.md#namespace-packages)。

## 结果与下一步

- **PASS**：本次观察到的指定包来源符合目录要求。还要单独看 pytest 是否通过。
- **FAIL**：观察到的代码来源不符合要求。比较 expected 与 observed，检查当前环境及 editable 安装。
- **UNKNOWN**：这次无法完成来源验证。可能未观察到目标、元数据无法可靠解析，或执行方式不受支持；
  查看 reason 和 next，不能当成通过。

pytest 失败但 guard PASS 表示“测试失败，来源符合要求”，不是整体成功。
保留 pytest 的全部非零退出码；pytest 成功时，PASS / FAIL / UNKNOWN 分别退出 0 / 1 / 2。
JSON 写入失败时，pytest 成功则退出 2，否则保留 pytest 非零退出码。
`--show-all` 展开匹配模块；`--report-json provenance.json` 保存详细证据，共享前请脱敏。

## 范围

只检查显式指定包及本次受支持 pytest 进程中观察到的来源，不证明测试覆盖率或代码等于某个 commit。
不自动修环境，不完整追踪 xdist 或子进程；启用 xdist 时需单进程 `-n 0`。
多根 namespace 不受支持。只有 Git 证据确定时才称为另一个 worktree。
工具不是沙箱，pytest 仍执行代码并可能产生副作用。

[排障（含 uv）](docs/troubleshooting.md) · [独立临时 Demo](examples/cross-worktree-demo/README.md) ·
[发布说明草稿](docs/releasing/0.1.0-notes.md) · [贡献](CONTRIBUTING.md)
