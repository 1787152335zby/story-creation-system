# 剧情阶段逐集生成与审核流程 Spec

## 为什么

当前剧情阶段（完整剧情 / 完整剧本 / 分镜脚本 / 提示词生成等分块阶段）所有集是一次性生成的——由 `run_stream()` 内部的 `for ctx in iterator:` 循环连续生成全部 chunk，然后 `_save_chunked_output()` 才逐一保存并请求审批。用户希望在**第1集生成完后立即看到审核按钮**，通过后再生成第2集，以此类推。

三种审核操作的行为也有问题：
- ✅ "通过并生成下一集" → 继续生成并审核下一集
- ✅ "完成" → **停止整个阶段**，不再进入下一阶段，回到工作台显示"继续创作"按钮
- ✅ "修改" → 输入修改意见后**重新生成当前集**，重新审核

## 变更内容

- **架构变更**：从"先生成全部块→再逐集保存+审核"改为"逐集生成→逐集保存→逐集审核→通过后才生成下一集"
- 重构 `_run_chunked_phase` 方法，按块调用 agent 生成、保存、审核
- 重构 Agent 的 `run_stream`，提取 `generate_chunk(ctx, feedback)` 方法以支持单块生成
- 修复"完成"操作：停止整个阶段（标记完成+断开前端循环+不再进入下一阶段）
- 修复"修改"操作：重新生成当前块并替换内容

## 影响范围

- 受影响的规格：分块生成与审核流程（重大架构变更）
- 受影响的代码：
  - `server/async_orch.py` — 新增 `_run_chunked_phase` 替代 `_save_chunked_output`
  - `agents/plot_expander.py` — 提取 `generate_chunk` 方法
  - `agents/screenplay_writer.py` — 提取 `generate_chunk` 方法
  - `server/ws_manager.py` — 无需大改
  - `src/pages/Workspace.tsx` — 保持在所有分支显示审核栏
  - `src/hooks/useWebSocket.ts` — 保持现状

---

## 需求

### 需求 1：逐集生成的端到端流程

**系统 SHALL** 按以下流程执行每个分块阶段：

#### 场景：标准逐集生成
- **前置条件**：Agent 的 `get_chunk_plan()` 返回 chunk 列表（名称、大纲内容）
- **WHEN** 进入该阶段
- **THEN** 对于每个 chunk（按索引 i 从 0 到 N-1）：
  1. 发送 `phase_start` + chunk i 的名称到前端（可选）
  2. 清空流内容缓冲区
  3. 调用 `agent.generate_chunk(ctx, feedback="")` 生成 chunk i
  4. Agent 通过 `yield token` 流式输出内容到前端
  5. 生成完成后，保存 chunk 文件到磁盘（`{base_stem}_{display_name}.md`）
  6. 发送 `chunk_saved` 消息到前端
  7. 发送 `episode_complete` 消息，**阻塞**等待用户操作
  8. 解析用户操作（通过/完成/修改）：
     - **通过并生成下一集** → 如果 i < N-1，i++ 回到步骤 1
     - **完成** → **跳出循环**，标记当前阶段完成，断开整个 pipeline
     - **修改** → 显示修改输入框，用户提交反馈后，用 `agent.generate_chunk(ctx, feedback)` 重新生成，回到步骤 4

#### 场景：生成中暂停
- **WHEN** 当前 chunk 正在流式生成
- **THEN** 前端显示流式内容 + 光标闪烁
- **THEN** 用户不可操作审核按钮（按钮未出现）

#### 场景：审核中等待
- **WHEN** `episode_complete` 消息到达
- **THEN** 前端显示审核按钮栏（⏸ 第i/N集已生成 — 请选择下一步操作）
- **THEN** 后端阻塞等待用户操作

### 需求 2：三种审核操作的完整行为

#### 场景：通过并生成下一集
- **WHEN** 用户点击"通过并生成下一集"
- **THEN** 当前 chunk 标记已审核通过
- **THEN** `episode_approve` 消息发送到后端
- **THEN** 后端 `_run_chunked_phase` 继续循环，生成并审核下一 chunk
- **THEN** 前端侧边栏该集显示 ✅
- **THEN** 前端审核栏消失，下一集流式内容开始出现

#### 场景：完成
- **WHEN** 用户点击"完成"
- **THEN** 当前 chunk 标记已审核通过
- **THEN** `episode_confirm` 消息发送到后端
- **THEN** 后端跳出 `_run_chunked_phase` 循环
- **THEN** 后端标记当前阶段 completed（`project.mark_phase_done`）
- **THEN** 后端**不进入下一阶段**
- **THEN** 后端发送 `phase_complete` 和 `phase_confirmed` 消息
- **THEN** 前端显示"已确认，内容已保存"横幅 + "继续创作"按钮
- **THEN** 最终合并文件写入磁盘（所有已通过的 chunk 拼接）

#### 场景：修改
- **WHEN** 用户点击"修改"
- **THEN** 前端显示修改意见输入框
- **WHEN** 用户提交修改意见
- **THEN** `episode_revise` + `feedback` 消息发送到后端
- **THEN** 以后端反馈为输入，重新调用 `agent.generate_chunk(ctx, feedback)`
- **THEN** Agent 流式输出重新生成的内容到前端
- **THEN** 新内容替换已保存的 chunk 文件
- **THEN** 再次发送 `episode_complete`，重新等待审核

### 需求 3：Agent 重构 — 支持单块生成

**系统 SHALL** 为所有分块 Agent 提供独立单块生成能力。

每个分块 Agent（plot_expander / screenplay_writer）SHALL：
- `get_chunk_plan(style, outline)` 方法：返回 ChunkPlan 对象（chunk 名称列表 + 大纲内容分割）
- `generate_chunk(ctx, feedback="")` 方法：生成单个 chunk，yield 流式 token
- `run_stream(project, style, input_content)` 保持向后兼容（通过循环调用 `generate_chunk` 实现）

### 需求 4：前端审核栏渲染

**系统 SHALL** 确保审核按钮在以下场景均可见：
- 流式模式（`showStream`）
- 浏览模式（`viewContent`）
- 后台生成模式（`connected && currentPhase >= 0`）

### 需求 5：auto_approve

**系统 SHALL** 在 auto_approve 开启时，`wait_for_episode_approval` 立即返回 `{"action": "approve", "auto": true}`。全部集数自动通过后，阶段不显示额外审核，直接标记完成并通知前端。

## 删除的需求

### 旧的 `_save_chunked_output` 方法
**原因**：该方法从预生成的 `chunks` 列表中迭代保存，无法支持"逐块生成→审核→下一块"的流程。被 `_run_chunked_phase` 替代。
**迁移**：所有分块阶段使用新的 `_run_chunked_phase` 方法。

### 旧的 `run_stream` 全部块生成
**原因**：全部块一次性生成无法在块间暂停审核。改为按块调用的 `generate_chunk` 模式。
**迁移**：`run_stream` 保持向后兼容，通过循环调用 `generate_chunk` 实现。
