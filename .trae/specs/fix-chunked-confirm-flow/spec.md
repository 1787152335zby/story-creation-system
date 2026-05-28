# 修复分集模式"完成"与状态持久化的 Bug

## 为什么

上一轮修复（`fix-chunked-confirm-flow`）修正了分集模式中"完成"按钮不跳到下一阶段的问题，但仍有 2 个问题：

1. **Bug 1：点击"完成"后仍不显示"继续生成下一集"按钮**
   - 后端 `_run_chunked_generation` 中 `total_chunks` 变量名错误导致 `NameError`
   - 已修复为 `chunk_count`，但需确认服务器加载了最新代码

2. **Bug 2：退出再回来状态不持久化**
   - 生了完整一集但未点"完成"保存 → 回来时看不到该集内容（无法继续完成操作）
   - 点了"完成"后退出了 → 回来时不会显示"继续生成下一集"（而是直接进入下一阶段或出错）
   - **根本原因**：`continue_run()` 中 `_resume_chunked_approval` 返回 `False`（待生成文件不存在）时，直接降级到正常生成流程，而非显示暂停状态等待用户操作。需要区分「初始回入显示暂停」与「用户点了继续生成后自动生成」两种场景。

## 变史内容

- **确认 `total_chunks` → `chunk_count` 已修复**并确保服务器正确加载
- **`continue_run()` 中处理 `_resume_chunked_approval` 返回 False**：区分初始回入和用户继续两种场景
  - 初始回入：发送 `phase_paused`，显示"继续生成下一集"按钮
  - 用户点击继续后：正常降级到生成流程
- **`ws_manager.py` proceed 处理器**：设置 `_proceed_resume` 标记，通知后端是用户主动继续而非初始回入
- **`run()` 中 `_proceed_resume` 标记清理**：确保一次性使用

## 影响范围

- 受影响的代码：
  - `server/async_orch.py` — `continue_run()` 中 resume 回入逻辑
  - `server/ws_manager.py` — proceed 处理器设置 `_proceed_resume`
  - `src/pages/Workspace.tsx` — re-entry 时检查 pending_episode（已修复，确认生效）

---

## 详细分析

### Bug 1 根因

第 1188 行 `if ci < total_chunks - 1:` 中的 `total_chunks` 是未定义变量。`NameError` 被 `run()` 的 try/except 捕获后，向前端发送错误消息。用户实际看到的是错误提示（而非"继续生成下一集"按钮）。

修复：`total_chunks` → `chunk_count`。

### Bug 2 根因

用户在分集模式点了"完成"后，`_run_chunked_generation` 保存 `pending_episode` 指向下一集（如第 2 集）。当用户退出再回来时：

1. 前端检测到 `pending_episode`，发送 `continue` 消息
2. `run()` → `continue_run()` 定位到该阶段
3. `_resume_chunked_approval()` 尝试读取第 2 集文件 → 文件不存在 → 返回 `False`  
4. 代码降级到正常生成流程 → 发送 `phase_start` → 生成第 2 集

**问题**：步骤 4 中直接开始生成，用户看不到"继续生成下一集"按钮。用户希望先看到暂停状态，手动点击按钮后再开始生成。

### Bug 2 修复方案

引入 `_proceed_resume` 标记（项目配置中的一次性布尔值）：

- **初始回入**（用户回来后自动触发持续）：
  - `_resume_chunked_approval` 返回 `False` → 不生成
  - 发送 `phase_paused` → 前端显示"继续生成下一集"
  - `paused_phase = True`，跳过后续阶段

- **用户点击继续**（点击"继续生成下一集"按钮）：
  - `ws_manager.py` proceed 处理器设置 `_proceed_resume = True` 并保存
  - 调用 `orch.run()` → `continue_run()`
  - `_resume_chunked_approval` 返回 `False`
  - 检测到 `_proceed_resume` → 清除标记 → 正常降级生成

---

## 需求

### 需求 1：确认 `total_chunks` 变量修复

**系统 SHALL** 在 `_run_chunked_generation` 中第 1188 行使用 `chunk_count` 而非 `total_chunks`。

**系统 SHALL** 在启动时确保 Python 字节码缓存已清除，服务器使用最新代码。

### 需求 2：`continue_run()` 中区分 resume 场景

**系统 SHALL** 在 `continue_run()` 中，当 `_resume_chunked_approval` 返回 `False` 时：

1. 检查项目配置中是否有 `_proceed_resume` 标记
2. 如果有标记（用户点击了"继续生成下一集"）：
   - 清除标记（`project.config.pop("_proceed_resume", None)`）
   - 保存配置
   - 保留现有生成流程（从 `chunk_resume_ci` 构建上下文后正常生成）
3. 如果没有标记（初始回入）：
   - 发送 `phase_paused` 消息
   - `paused_phase = True`
   - `continue` 到外层循环的下一阶段

```python
# 修改后的逻辑（伪代码）
if pending_ep and pending_ep.get("phase_index") == idx:
    resumed = await self._resume_chunked_approval(project, project_name, idx, pending_ep)
    if resumed:
        continue
    
    # File doesn't exist - either initial re-entry or user clicked continue
    auto_resume = project.config.pop("_proceed_resume", False)
    project.save_config()
    
    if auto_resume:
        # User clicked "继续生成下一集" → auto-generate from next CI
        chunk_resume_ci = pending_ep["chunk_index"]
        chunk_files = pending_ep.get("chunk_files", [])
        parts = [project.read_output(cf) or "" for cf in chunk_files if project.read_output(cf)]
        if parts:
            existing_full_parts = parts
    else:
        # Initial re-entry → show paused state
        await self.ws.send_message(project_name, {
            "type": "phase_paused",
            "phase_index": idx,
            "phase_name": phase.name,
        })
        paused_phase = True
        continue
```

**WHEN** 用户生成了第 1 集后点击"完成"
**WHEN** 用户退到首页再回来
**WHEN** 前端自动发送 `continue` 消息
**THEN** `continue_run()` 检测到 `pending_episode`（指向第 2 集）
**THEN** `_resume_chunked_approval` 返回 `False`（第 2 集文件不存在）
**THEN** 没有 `_proceed_resume` 标记 → 发送 `phase_paused`
**THEN** 前端显示"第 1 集已保存 — 可继续生成下一集" + **继续生成下一集** 按钮

**WHEN** 用户点击"继续生成下一集"按钮
**THEN** 前端发送 `proceed` 消息
**THEN** `ws_manager.py` proceed 处理器设置 `_proceed_resume = True`
**THEN** `orch.run()` → `continue_run()`
**THEN** `_resume_chunked_approval` 返回 `False`，但 `_proceed_resume` 为 `True`
**THEN** 清除标记，从第 2 集开始正常生成

### 需求 3：`ws_manager.py` 设置 `_proceed_resume`

**系统 SHALL** 在 `ws_manager.py` 的 `proceed` 消息处理器中，当检测到 `pending_episode` 存在时，在调用 `orch.run()` 之前设置该项目的 `_proceed_resume` 标记。

```python
# ws_manager.py proceed handler 中追加：
if project.pending_episode is not None:
    project.config["_proceed_resume"] = True
    project.save_config()
    style = project.config.get("style", {})
    orch = self.orchestrators.get(project_name)
    if orch:
        asyncio.ensure_future(orch.run(project_name, style))
```

### 需求 4：未确认状态持久化

**系统 SHALL** 在重新进入项目且 `pending_episode.chunk_index` 指向**当前**已生成未确认的集数时：

- `_resume_chunked_approval` 读取已有 chunk 文件，回放内容
- 发送 `episode_complete` 消息
- 前端显示完成/通过/修改按钮
- 用户可点击"完成"以暂停，或"通过并生成下一集"继续

**系统 SHALL** 确认前端 `useEffect` 中已正确检测到 `config.pending_episode` 并设置 `pendingContinue = true`。

## 删除的需求

无。
