# 验证清单

## Task 1: Agent 重构
- [x] `plot_expander.prepare_generation()` 存在，返回 (chunk_count, chunk_names)
- [x] `plot_expander.generate_chunk(ctx, feedback)` 存在
- [x] `plot_expander.run_stream` 通过循环调用 `generate_chunk` 实现（向后兼容）
- [x] `screenplay_writer.prepare_generation()` 存在
- [x] `screenplay_writer.generate_chunk(ctx, feedback)` 存在
- [x] `screenplay_writer.run_stream` 通过循环调用 `generate_chunk` 实现（向后兼容）

## Task 2: `_run_chunked_generation` 方法
- [x] 方法存在，完整实现逐集生成→保存→审核逻辑
- [x] 每集在后台线程中调用 `agent.generate_chunk()`，流式输出到前端
- [x] 每集保存 `{base_stem}_{name}.md` 文件
- [x] 每集保存后调用 `wait_for_episode_approval` 阻塞等待
- [x] 所有块通过后写入合并文件 `{base_stem}.md`
- [x] "通过并生成下一集"：循环继续，生成下一块（真实LLM调用）
- [x] "完成"：break 循环，返回 confirmed
- [x] "修改"：用 feedback 重新调用 `generate_chunk`，替换文件，重新审核
- [x] `run()` 和 `continue_run()` 和 `redo_phase()` 中的所有分块阶段调用点已迁移
- [x] `ChunkIter.get_chunk_context(index)` 方法存在

## Task 3: 移除旧方法
- [x] `_save_chunked_output` 方法已删除
- [x] `_run_chunked_phase` 方法已删除
- [x] 所有原有调用点已替换为 `_run_chunked_generation`

## Task 4: 端到端验证（需手动测试）

## 修复：完成后的"继续创作"按钮
- [x] `useWebSocket.ts` 中 `phase_confirmed` 消息设置 `confirmedPhaseIndex` 状态
- [x] Workspace.tsx 的 showStream 分支底部显示"继续创作"按钮（绿色横幅）
- [x] 点击"继续创作"后调用 `handleContinue()` 进入下一阶段
- [ ] 第1集流式输出→出现审核按钮→通过→第2集流式输出→出现审核按钮→完成→阶段停止
- [ ] "完成"后不自动进入下一阶段，显示"继续创作"按钮
- [ ] "修改"后当前集重新生成（输入 feedback，重新调用 LLM）
- [ ] auto_approve 开启时所有集自动通过
- [ ] continue_run 时从暂停处恢复
