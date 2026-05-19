# 中断恢复 Spec

## 为什么

当前系统在用户意外退出或刷新页面时，逐集审核状态和流式生成进度丢失。具体两个问题：

1. **生成完一集后刷新/退出**：该集的 .md 文件已保存到磁盘，但"等待用户审核该集"的状态仅存在内存中。重新进来时找不到该状态，阶段从头重新生成。
2. **生成中刷新/退出**：后台 LLM 线程未正确取消（`cancelled` 标志未被设置），线程泄漏；部分输出未保存到磁盘，阶段从头重新生成。

用户希望无论何时退出，已保存的内容不丢失，重新进来时能从断点继续。

## 变更内容

- **内存状态持久化**：在 `project.config` 中保存逐集审核的断点状态（当前 phase_index、chunk_index、chunk_name）
- **新增 `_resume_chunked_approval`**：恢复逐集审核流程的方法
- **修复线程取消 Bug**：在 asyncio 任务取消时设置 `cancelled[0] = True`，防止线程泄漏
- **continue_run 识别断点**：检测到 chunk 断点时，优先恢复逐集审核而非重置阶段

## 影响范围

- 受影响的规格：分块生成流程、断线重连、中断恢复
- 受影响的代码：
  - `server/async_orch.py` — `_run_chunked_generation`、`continue_run`、`run`
  - `server/ws_manager.py` — `connect`、`disconnect`、新增持久化状态读写
  - `core/project_manager.py` — 新增 `set_pending_episode` / `clear_pending_episode` / `pending_episode` 属性
  - `src/pages/Workspace.tsx` — 前端加载时检测断点状态，决定显示什么

---

## 需求

### 需求 1：逐集审核状态的持久化

**系统 SHALL** 在每集生成完成并保存文件后，将审核待定状态持久化到 `project.config`：

```python
project.config["pending_episode"] = {
    "phase_index": phase_index,
    "chunk_index": ci,
    "chunk_name": display_name,
    "total_chunks": chunk_count,
    "merged_chunks": full_parts[:],  # 已通过/已保存的块内容副本（用于最后合并）
}
```

**系统 SHALL** 在该集通过或完成后清除此状态：

```python
project.config["pending_episode"] = None
project.save_config()
```

#### 场景：用户在一集生成完后刷新
- **WHEN** 用户完成第一集生成（文件已保存），未点击审核按钮，刷新页面
- **THEN** `continue_run` 检测到 `pending_episode` 不为空
- **THEN** 读取已保存的 chunk 文件并重放到前端
- **THEN** 发送 `episode_complete` 消息，弹出审核栏，恢复等待

### 需求 2：生成中的中断恢复

**系统 SHALL** 在 `_run_chunked_generation` 中处理 `CancelledError`：

```python
except asyncio.CancelledError:
    cancelled[0] = True  # 立即停止后台线程
    raise
```

#### 场景：用户在流式生成中刷新
- **WHEN** 用户在第 1 集流式生成过程中刷新页面
- **THEN** 后台线程立即停止（`cancelled[0] = True`）
- **THEN** 该集未生成完，不保存任何文件
- **THEN** 重新连接后，`continue_run` 检测到 `pending_episode` 为空（因为该集未完成）
- **THEN** 阶段从头重新生成

> 说明：部分生成的内容不保存，因为不完整的内容提交到审核没有意义。用户重新进来后重新生成该集。

### 需求 3：continue_run 识别逐集断点

**系统 SHALL** 在 `continue_run` 中优先检测 `pending_episode` 状态：

```python
pending_ep = project.config.get("pending_episode")
if pending_ep and pending_ep.get("phase_index") == idx:
    # 恢复逐集审核
    await self._resume_chunked_approval(project, project_name, idx, pending_ep)
    continue
```

**系统 SHALL** 新增 `_resume_chunked_approval` 方法：

```python
async def _resume_chunked_approval(self, project, project_name, phase_index, pending_ep):
    """恢复上一集审核：重放内容 + 重新发送 episode_complete + 等待用户"""
    phase_index = pending_ep["phase_index"]
    chunk_name = pending_ep["chunk_name"]
    chunk_index = pending_ep["chunk_index"]
    total_chunks = pending_ep["total_chunks"]
    
    # 读取已保存的 chunk 文件
    chunk_fname = ...  # 构造文件名
    content = project.read_output(chunk_fname) or ""
    if not content.strip():
        return  # 文件不存在，放弃恢复
    
    # 重放流式内容
    await self.ws.send_message(project_name, {"type": "stream_clear"})
    await self.ws.send_message(project_name, {
        "type": "stream", "phase_index": phase_index, "chunk": content,
    })
    
    # 发送 episode_complete，进入逐集审核等待
    await self.ws.send_message(project_name, {
        "type": "episode_complete",
        "phase_index": phase_index,
        "chunk_name": chunk_name,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
    })
    
    # 等待用户操作
    ep_result = await self.ws.wait_for_episode_approval(
        project_name, phase_index, chunk_name, chunk_index, total_chunks
    )
    # ... 处理通过/完成/修改
```

### 需求 4：前端检测断点状态

**系统 SHALL** 在 `Workspace.tsx` 的前端加载时检查 `pending_episode`：

- **WHEN** 用户刷新页面，`fetchProject` 返回的配置中包含 `pending_episode`
- **THEN** 前端设置 `awaitingEpisodeApproval = true`
- **THEN** 前端连接 WebSocket 并等待 `episode_complete` 消息
- **THEN** 前端显示审核栏

## 删除的需求

无。
