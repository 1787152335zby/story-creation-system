# 修复"完成"后跳到下一阶段问题 Spec

## 为什么

当前逐集审核界面有三个按钮：**通过并生成下一集**、**完成**、**修改**。当用户点击"完成"时，后端认为"整个阶段完成"，直接跳到下一阶段。用户期望：点"完成"只是**保存当前集、停在这里**，然后点"继续创作"时继续生成下一集（而非跳到下一阶段）。

**根本原因**：`_run_chunked_generation` 中 `action == "confirm"` 直接 `break` 退出逐集循环，返回 `confirmed: True`。调用方（`run`/`continue_run`）执行 `mark_phase_done()` 并跳出阶段循环。

## 变更内容

- **修改 `_run_chunked_generation` 返回值**：当剩余集数 > 0 时，"完成"不返回 confirmed，而是返回 `paused`
- **调用方识别 `paused` 状态**：不标记阶段完成，保持 `pending_episode` 指向下一集
- **`continue_run` 支持从暂停点恢复**：`pending_episode` 指向未生成的集时，调用 `_run_chunked_generation` 继续生成
- **`_run_chunked_generation` 增加 `start_ci` 参数**：支持从指定 chunk 开始生成，跳过已完成的 chunks

## 影响范围

- 受影响的代码：
  - `server/async_orch.py` — `_run_chunked_generation`、`continue_run`、`run`
  - `src/pages/Workspace.tsx` — 前端的"继续创作"按钮行为

---

## 需求

### 需求 1：`_run_chunked_generation` 支持从指定位置继续

**系统 SHALL** 让 `_run_chunked_generation` 接受可选的 `start_ci=0` 和 `existing_full_parts=[]` 参数。

```python
async def _run_chunked_generation(self, agent_class, project, style, input_content,
                                   project_name, output_path, phase_index,
                                   start_ci=0, existing_full_parts=None):
```

- **WHEN** `start_ci > 0`，跳过前 `start_ci` 个 chunk 的生成，直接从第 `start_ci` 个开始
- **WHEN** `existing_full_parts` 非空，追加后用于最后合并输出
- 每集生成后保存文件 + 等待审核（与当前一致）

### 需求 2："完成"键在非最后集时暂停而非结束阶段

**系统 SHALL** 在 `_run_chunked_generation` 中，当用户点击"完成"且 `ci < total_chunks - 1` （还有剩余集）时：

- 不 `break`，设置 `pending_episode` 指向**下一集**（`ci+1`）
- 返回 `{"action": "paused"}`（非 `confirmed`）

仅当 `ci >= total_chunks - 1` （最后一集）时，"完成"才返回 `confirmed`，标记阶段完成。

### 需求 3：调用方识别 paused 状态

**系统 SHALL** 在 `run()` 和 `continue_run()` 中，当 `_run_chunked_generation` 返回 `paused` 时：

- 不执行 `mark_phase_done()`
- 不发送 `phase_confirmed`
- 发送 `phase_complete` 以便前端显示"继续创作"按钮
- 继续外层循环（进入下一阶段前的检查环节）

### 需求 4：继续创作恢复逐集生成

**系统 SHALL** 在 `continue_run` 中，当检测到 `pending_episode` 时：

- 读取已生成的 chunk 文件内容
- 构建 `existing_full_parts` 列表
- 调用 `_run_chunked_generation(..., start_ci=pending_ep['chunk_index'], existing_full_parts=existing_full_parts)`
- `_run_chunked_generation` 从 `start_ci` 开始生成并进入审核循环

### 场景：用户完成第一集

- **WHEN** 第一集生成完成，用户点击"完成"
- **THEN** 该集保存到磁盘，`pending_episode` 指向第 2 集（chunk_index=1）
- **THEN** 前端显示绿色横幅"已保存，可继续创作" + **[继续创作]** 按钮
- **WHEN** 用户点击"继续创作"
- **THEN** `continue_run` 检测到 pending_episode，调用 `_run_chunked_generation` 从第 2 集开始
- **THEN** 第 2 集流式生成 → 审核栏出现

### 场景：用户点击"通过并生成下一集"

（行为不变）
- **WHEN** 用户点击"通过并生成下一集"
- **THEN** 自动进入下一集生成，不暂停

### 场景：用户点击"完成"在最后一集

（行为不变）
- **WHEN** 用户在最后一集点击"完成"
- **THEN** 阶段完成，标记 done，下次"继续创作"进入下一阶段

## 删除的需求

无。
