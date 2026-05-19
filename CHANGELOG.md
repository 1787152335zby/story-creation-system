# 更新日志

## [Unreleased]

### 逐集生成 + 审核流程

新增分集生成模式，适用于完整剧情（完整剧情规划）、完整剧本、分镜设计阶段。

- **批量分集**：Agent 根据内容复杂度和输出格式自动规划分集数量和名称
- **逐集生成**：每集独立生成，后台线程运行，流式输出到前端
- **逐集审核**：每集生成完成后弹出审核栏，三个操作按钮：
  - **通过并生成下一集** → 保留当前集，自动进入下一集
  - **完成** → 保存当前集并暂停（非最后集时）或结束阶段（最后一集）
  - **修改** → 输入意见，重新生成当前集
- **逆序生成**：支持倒序生成（如先出第3集再出第1集），最终按正确顺序合并

### 中断恢复

支持在生成/审核过程中刷新页面或退出后重进时恢复状态。

- **线程取消修复**：生成中刷新页面时，后台线程的 `CancelledError` 正确设置 `cancelled` 标志，不再泄漏线程
- **持久化 `pending_episode`**：每集生成完成后将审核状态写入 `project_config.json`，刷新后可恢复审核栏
- **恢复审核**：`_resume_chunked_approval` 读取已保存的 chunk 文件，重放流式内容，重新发送审核消息，等待用户操作

### "完成"键行为修复

- **非最后集暂停**：点"完成"时，如果还有剩余集，不再结束阶段，而是返回 `paused` 状态，保存当前集
- **调用方识别 `paused`**：`run()`、`continue_run()`、`redo_phase()` 识别 paused 状态，发送 `phase_complete` + `phase_confirmed`，不 `mark_phase_done`
- **跳过 `all_complete`**：使用 `paused_phase` 标记，暂停时不发送 `all_complete`，前端保持"继续创作"按钮

### 退出重进恢复

- **`run()` 跳转 `continue_run()`**：`run()` 中 `has_done` 检查之后增加 `pending_episode` 检测，存在时跳转到 `continue_run()`
- **`set_pending_episode` 记录 `chunk_files`**：暂停时记录所有已生成的 chunk 文件名列表
- **恢复时重建 `existing_full_parts`**：`continue_run()` 读取已有文件内容构建 `existing_full_parts`，传递给 `_run_chunked_generation(start_ci=..., existing_full_parts=...)`，断点续生

### 技术修改

- `server/async_orch.py` — `_run_chunked_generation` 新增 `start_ci`/`existing_full_parts` 参数；`run()`/`continue_run()`/`redo_phase()` 全线修改
- `core/project_manager.py` — 新增 `pending_episode`、`set_pending_episode(chunk_files)`、`clear_pending_episode`
- `agents/outline_designer.py`、`agents/plot_expander.py`、`agents/screenplay_writer.py`、`agents/storyboarder.py` — 分集生成逻辑
- `core/agent_base.py` — Agent 基类分集生成接口
- `core/chunk_strategy.py` — 新增分块策略
- `server/ws_manager.py` — WebSocket 支持逐集审核消息类型
- `src/pages/Workspace.tsx` — 逐集审核栏 UI、暂停/继续创作交互
- `src/components/PhaseTimeline.tsx` — 阶段时间线调整
- `src/hooks/useWebSocket.ts` — WebSocket hook 扩展
- 新增提示词：`prompts/outline_direction_card.txt`、`prompts/outline_full.txt`
