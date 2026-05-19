# 任务列表

- [x] Task 1: Agent 重构 — 提取 `generate_chunk` 方法
  - [x] 修改 `agents/plot_expander.py`：提取 `generate_chunk(ctx, feedback)`，添加 `prepare_generation` 方法
  - [x] 修改 `agents/screenplay_writer.py`：同理提取 `generate_chunk(ctx, feedback)` 和 `prepare_generation`
  - [x] 返回的 `_chunks`属性改为由 `run_stream` 在循环中逐个收集

- [x] Task 2: 新增 `_run_chunked_generation` 方法（替换 `_run_chunked_phase`）
  - [x] 真实逐集生成：每集在后台线程中调用 `agent.generate_chunk()`，流式输出到前端
  - [x] 每集生成完后保存文件 + `wait_for_episode_approval`
  - [x] 处理"通过并生成下一集"：继续下一集生成
  - [x] 处理"完成"：break 循环，返回 confirmed
  - [x] 处理"修改"：重新用 feedback 调用 `generate_chunk`，替换文件，重新审核
  - [x] 替换 `run()` 和 `continue_run()` 和 `redo_phase()` 中的所有分块阶段调用点
  - [x] 添加 `ChunkIter.get_chunk_context(index)` 方法支持获取特定 chunk 的上下文

- [x] Task 3: 移除原有的 `_save_chunked_output` 和 `_run_chunked_phase` 方法
  - [x] 确认所有调用点已迁移
  - [x] `_save_chunked_output` 和 `_run_chunked_phase` 已完全删除

- [x] Task 4: 端到端验证（需手动测试）

## 后续发现的 Bug 修复
- [x] Bug: "完成"后没有"继续创作"按钮
  - [x] `useWebSocket.ts` 中 `phase_confirmed` 状态未设置（空break）
  - [x] 新增 `confirmedPhaseIndex` 状态，由 `phase_confirmed` 消息设置
  - [x] Workspace.tsx 的 showStream 分支底部添加"继续创作"按钮，调用 `handleContinue()`
  - [ ] 创建项目→选短剧→开始创作→选版本
  - [ ] 完整剧情阶段：第1集流式输出→出现审核按钮→通过→第2集流式输出→出现审核按钮→完成→阶段停止
  - [ ] 修改测试：修改→输入反馈→当前集重新生成→再次审核
  - [ ] auto_approve 测试：开启→所有集自动通过→阶段自动完成
  - [ ] continue_run 测试：阶段暂停后重新连接→从暂停处恢复
  - [ ] redo_phase 测试：重新生成阶段→逐集审核正常
