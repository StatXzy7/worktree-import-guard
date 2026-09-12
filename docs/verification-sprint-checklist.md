# Verification Sprint 逐项验收工单（v0）

目标：把“本轮实现”从“设计收敛”推进到“可发布证据”。

执行前提：
- 保持 feature freeze，不再新增功能改动。
- 只在本清单条目内进行验证与修复（若有必要）。

---

## 0. 基础状态冻结与基线
- [ ] 记录当前 HEAD 与工作树：`git rev-parse --short HEAD` + `git status --short`
  - 预期：后续有明确 commit 变化；清单执行前先记住基线。

---

## 1. 第一层（高相关）验证
- [ ] 运行 runner 合约测试：`pytest tests/skills/test_runner_contract.py -q`
  - 预期：通过；若失败，优先修复 `run_check`/envelope 状态相关回归。
- [ ] 运行 doctor/onboarding 相关测试：`pytest tests/unit/test_doctor.py -q`
  - 预期：通过；重点看环境发现与候选绑定语义是否稳健。
- [ ] 运行 README artifact 命令测试：`pytest tests/artifact/test_readme_commands.py -q`
  - 预期：通过；重点看公开命令路径在文档-实现一致。
- [ ] 运行 evidence 目录边界测试：`pytest tests/skills/test_evidence_dir.py -q`
  - 预期：通过；确认证据目录与 envelope 分离。
- [ ] 运行 preflight 用例：`pytest tests/skills/test_preflight.py -q`
  - 预期：通过；确认 `missing_conditions / needs_selection / ready` 的边界。

---

## 2. 完整回归
- [ ] 运行全量测试：`pytest -q`
  - 预期：全部通过。
- [ ] 运行覆盖率验证：`pytest --cov=worktree_import_guard --cov-report=term-missing`
  - 预期：生成覆盖率报告且关键新增路径不出现空白盲区。

---

## 3. 代码质量与类型
- [ ] 运行 lint：`ruff check .`
  - 预期：无 lint 错误。
- [ ] 运行类型检查：`mypy src`
  - 预期：无新类型错误。

---

## 4. 打包与 artifact 验证
- [ ] 构建 wheel/sdist：`python -m build`
  - 预期：通过，产物可安装。
- [ ] 安装当前 artifact 并执行候选性检查：
  - `python -m pip install dist/*.whl --force-reinstall`
  - `wt-import --version`
  - `wt-import --help`
  - 预期：能在 clean 环境下调用入口与帮助，说明分发可用。

---

## 5. 关键场景（Host 证据）
- [ ] 场景集（本地可复现）：
  1. normal PASS
  2. wrong worktree FAIL
  3. target not observed → UNKNOWN
  4. pytest failure + source PASS
  5. install declined
  6. demo only
  7. explanation only
  8. pytest 已执行但 evidence save 失败
  9. pre-launch 失败（启动前失败）
  10. post-launch delivery 失败但不重跑
  - 预期：每个场景均输出稳定且一致的 envelope 事实；失败场景不得误判为未执行。

---

## 6. 状态机一致性护栏（建议长期保留）
- [ ] 为状态字段添加/确认不变式验证（测试中）
  - `subprocess_finished -> subprocess_launched`
  - `pytest_exit_code_known -> subprocess_finished`
  - `engine_report_exists -> subprocess_finished`
  - `report_validated -> engine_report_exists`
  - `result_delivered -> result`
- [ ] 运行不变式对应测试（若无则补齐）。

---

## 7. 发布态冻结条件
- [ ] 更新 `docs/...` 或 release notes，统一声明本次状态：
  - Feature Complete / Evidence Incomplete（执行前）
  - Release Candidate Ready（执行通过后）
- [ ] 形成最终验收摘要（含 exact HEAD 与 exact wheel hash）。

