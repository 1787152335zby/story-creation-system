# 修复分集模式：浏览历史、按钮逻辑、集数标识

## 为什么

分集模式下逐集生成时存在 4 个问题：

1. **不能查看已生成的上一集内容** — 生成第 2 集后，界面只显示最新内容，无法查看第 1 集
2. **两个"继续"按钮逻辑混乱** — "通过并生成下一集"（审核栏内）和"继续生成下一集"（暂停后）功能重叠、用户困惑
3. **同一集生成了两次** — 在后一个集的 `set_pending_episode` 前刷新页面，`pending_episode` 为空，导致系统重新从第 1 集开始生成
4. **生成的剧情没有明确标第几集** — `generate_chunk` 的 prompt 中没有传入集数标识，AI 不知道自己在生成第几集

## 变更内容

- **前端新增集列表浏览面板** — 点击侧边栏中的"第 X 集"可查看该集已保存的内容
- **合并两个按钮为单一逻辑** — 移除"通过并生成下一集"，保留"完成"按钮，点"完成"后显示"继续生成下一集"
- **修复刷新丢失进度** — 确保 `clear_pending_episode()` 和 `set_pending_episode()` 之间不丢状态
- **传入集数标识到 prompt** — `generate_chunk` 的参数中增加 `display_name`（如"第1集"），让 AI 在输出中明确标注

## 影响范围

- `server/async_orch.py` — `_run_chunked_generation` 中 prompt 传入集数标识
- `agents/plot_expander.py` — `generate_chunk` 接收并注入 display_name
- `agents/screenplay_writer.py` — `generate_chunk` 接收并注入 display_name
- `src/pages/Workspace.tsx` — 集列表浏览 UI、按钮简化
- `src/hooks/useWebSocket.ts` — 按钮逻辑简化

---

## 详细分析

### Bug 1：无法查看已生成的历史集

**根因**：每次生成新集时（[async_orch.py L1139](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py#L1139)），后端发送 `stream_clear` 消息清空前端 `streamContent`。当用户处于暂停态时，只能看到"第 X 集已保存"的标签，但没有查看该集内容的途径。

**修复方案**：左侧边栏显示已保存的集列表。点击某集时，从后端读取该集的 chunk 文件内容展示。

### Bug 2：两个"继续"按钮逻辑混乱

**当前状态**：
- `episode_complete` 事件后，前端显示 3 个审核按钮："通过并生成下一集"、"完成"、"修改"
- "通过并生成下一集"（`episodeApprove`）直接 approve + 自动生成下一集
- "完成"（`episodeConfirm`）→ 后端返回 `{action:"paused"}` → 前端显示"继续生成下一集"
- "继续生成下一集" → `proceed` → `_proceed_resume` → 继续生成

**问题**：两个按钮本质都是"保存当前集 + 生成下一集"，区别只是有没有中间的暂停让用户查看。这个区别对用户不清晰。

**修复方案**：移除"通过并生成下一集"按钮，保留"完成"+"继续生成下一集"双步骤：
1. 每集生成后 → 只显示"完成"和"修改"两个按钮
2. 点击"完成" → 保存当前集，进入暂停态，显示"继续生成下一集"
3. 暂停时，用户可以浏览已生成的内容
4. 点击"继续生成下一集" → 生成下一集

### Bug 3：刷新导致同一集生成两次

**根因**：当 `_run_chunked_generation` 中处理完用户审核（approve）后，会先 `clear_pending_episode()`（L1195），然后在 while 循环下一轮 `set_pending_episode()`（L1177）。如果用户在此时刷新：

1. `pending_episode` 为 None
2. `run()` → 检查 `project.pending_episode is not None` → 否
3. `has_done` 为 False → 直接进入相位循环
4. chunked phase → `existing_content` 为空（合并文件不存在）
5. `_run_chunked_generation(start_ci=0)` → 从第 1 集重新生成

**修复方案**：在 `_run_chunked_generation` 的 while 循环中，**先** `set_pending_episode` 到下一集，**再** `clear_pending_episode` 当前集。或者更简单：在 `set_pending_episode` 被调用之前不 `clear_pending_episode`。即：

```python
# 修改前（L1193-1195）
if action == "approve":
    ci += 1
    project.clear_pending_episode()

# 修改后
if action == "approve":
    ci += 1
    # 不清除 pending_episode — 让下一轮循环的 set_pending_episode 覆盖它
    # project.clear_pending_episode()  # 删除此行
```

因为下一轮循环必然会在 L1177 调用 `set_pending_episode`，这个调用会覆盖掉旧的 `pending_episode`，所以不需要先清空。这样即使在 `set_pending_episode` 之前刷新，`pending_episode` 仍然指向当前集，恢复后用户可以看到当前集并重新审核。

### Bug 4：生成的剧情没写第几集

**根因**：`generate_chunk` 的 prompt 中没有传入当前是第几集的信息。

在 `_run_chunked_generation` 中（L1113），`display_name` 是 `ctx.name` 或 `f"第{ci+1}集"`，但这个名称只用于文件名和前端通知，**没有传入 generate_chunk** 的参数。

`_build_gen_kwargs`（L1081）构建的参数中没有包含 `ctx.name` 或 `display_name`。

**修复方案**：在 `_build_gen_kwargs` 中增加 `chunk_name=display_name`，并在 agent 的 `generate_chunk` 中将 `{chunk_name}` 注入 prompt。

---

## 需求

### 需求 1：左侧显示已保存集列表

**系统 SHALL** 在 workspace 左侧侧边栏中，对分集模式下的当前相位，显示已完成的集列表。

**WHEN** 第 1 集生成完成并保存
**THEN** 左侧侧边栏对应相位下显示"第1集"列表项
**WHEN** 用户点击"第1集"
**THEN** 从后端读取该集的 chunk 文件内容，在主区域展示

**WHEN** 第 2 集生成
**THEN** 左侧侧边栏显示"第1集"和"第2集"两个列表项

### 需求 2：简化审核按钮

**系统 SHALL** 在 `episode_complete` 后只显示两个按钮："完成"和"修改"。

**系统 SHALL** 移除"通过并生成下一集"按钮。

**WHEN** 每集生成完毕
**THEN** 前端显示：
  - "完成"（保存当前集，暂停，显示"继续生成下一集"）
  - "修改"（弹出修改意见输入框）

**WHEN** "完成"被点击
**THEN** 后端 `action == "confirm"` → 暂停 → 前端显示"继续生成下一集"按钮

**WHEN** "继续生成下一集"被点击
**THEN** 后端通过 `_proceed_resume` 机制继续生成下一集

### 需求 3：修复刷新丢失进度

**系统 SHALL** 在 `_run_chunked_generation` 中，approve 处理时不调用 `clear_pending_episode()`，让下一轮循环的 `set_pending_episode` 自然覆盖它。

```python
# async_orch.py L1192-L1198 修改
if action == "approve":
    ci += 1
    current_feedback = ""
    # 已通过，下一轮循环的 set_pending_episode 会覆盖当前状态
    # 不调用 clear_pending_episode() 以防止刷新时丢失进度
elif action == "confirm":
    project.clear_pending_episode()
    ...
```

**WHEN** 用户点击"通过"后瞬间刷新
**THEN** `pending_episode` 仍指向当前集（文件存在）
**THEN** `_resume_chunked_approval` 读取文件，重放内容
**THEN** 用户重新看到该集内容，可以再次点击"完成"

### 需求 4：生成内容标明第几集

**系统 SHALL** 在 `_build_gen_kwargs` 中传入 `chunk_name=display_name`。

**系统 SHALL** 修改 agent 的 `generate_chunk` 方法，在 prompt 中注入 `{chunk_name}`，让 AI 在生成的内容开头写明当前集数。

**WHEN** 生成第 1 集
**THEN** prompt 包含 `chunk_name="第1集"` 或对应的实际名称
**THEN** AI 生成的内容开头包含明确的集数标识

**注意**：chunk_name 的注入必须兼容所有使用了 `generate_chunk` 的 agent：
- `plot_expander.py`
- `screenplay_writer.py`
- `storyboarder.py`
- `prompt_engineer.py`

## 删除的需求

无。
