# 修复"退出后重进重新生成"问题 Spec

## 为什么

用户生成两集后点"完成"保存（暂停），退出后重进，`run()` 不检测 `pending_episode` 状态，从第1集重新生成。

**根因**：`run()` 方法仅靠 `has_done` 判断是否需要跳转到 `continue_run()`。但由于暂停（paused）的 phase 没有被标记为 `done`，`has_done` 为 False，`run()` 直接进入全量循环，无视 `pending_episode` 的存在。

## 变更内容

- **`run()` 检测 `pending_episode`**：在进入阶段循环前，如果项目有 `pending_episode`，直接跳转到 `continue_run()`
- **`_resume_chunked_approval` 文件名修正**：确保读文件时使用正确的 chunk 文件名（`第{idx+1}集` 而非 `第{idx+2}集`）
- **暂停时保存 `full_parts` 到持久化状态**：`set_pending_episode` 记录已生成的 chunk 文件名列表，供恢复时重建 `existing_full_parts`

## 影响范围

- 受影响的代码：
  - `server/async_orch.py` — `run()`、`_resume_chunked_approval`、`_run_chunked_generation` 的暂停路径
  - `core/project_manager.py` — `set_pending_episode` 增加 `chunk_files` 参数

---

## 需求

### 需求 1：`run()` 检测 `pending_episode`

**系统 SHALL** 在 `run()` 中，`has_done` 检查之后、阶段循环之前，增加 `pending_episode` 检查：

```python
if has_done:
    await self.continue_run(project_name, style_data)
    return

# 新增：paused 状态下转到 continue_run
pending_ep = project.pending_episode
if pending_ep is not None:
    await self.continue_run(project_name, style_data)
    return
```

### 需求 2：`set_pending_episode` 记录已生成的文件列表

**系统 SHALL** 修改 `set_pending_episode`，增加 `chunk_files` 参数：

```python
def set_pending_episode(self, phase_index, chunk_index, chunk_name, total_chunks, chunk_files=None):
    self.config["pending_episode"] = {
        "phase_index": phase_index,
        "chunk_index": chunk_index,
        "chunk_name": chunk_name,
        "total_chunks": total_chunks,
        "chunk_files": chunk_files or [],
    }
    self.save_config()
```

**系统 SHALL** 在 `_run_chunked_generation` 的 paused 路径中，传入已生成的 chunk 文件名列表：

```python
# 在 paused 返回前
saved_chunk_files = []
for i in range(ci + 1):  # 0..ci 是已保存的
    name = names[i]  # 从 chunk_names 取实际名
    saved_chunk_files.append(f"{base_stem}_{name}.md")
project.set_pending_episode(phase_index, ci + 1, ..., saved_chunk_files)
```

### 需求 3：恢复时重建 `existing_full_parts`

**系统 SHALL** 在 `_resume_chunked_approval` 返回 False（文件不存在 → 继续生成）的情况下，调用方读取已保存的 chunk 文件内容来构建 `existing_full_parts`：

```python
# 在 continue_run 的 pending_episode 降级路径中
pending_ep = project.pending_episode
chunk_files = pending_ep.get("chunk_files", [])
existing_parts = []
for fname in chunk_files:
    content = project.read_output(fname) or ""
    if content:
        existing_parts.append(content)

cr = await self._run_chunked_generation(
    ..., start_ci=chunk_resume_ci,
    existing_full_parts=existing_parts
)
```

#### 场景：生成两集后暂停→重进→继续

- **WHEN** 用户生成第1集（"通过"）、第2集（"完成"），退出系统
- **THEN** `pending_episode` 持久化：`chunk_index=2`（第3集），`chunk_files=["完整剧情_第1集.md", "完整剧情_第2集.md"]`
- **WHEN** 用户重进，点击"继续创作"
- **THEN** `run()` 检测到 `pending_episode` → 跳转到 `continue_run()`
- **THEN** `continue_run` 恢复，读取两集文件构建 `existing_full_parts`
- **THEN** `_run_chunked_generation(start_ci=2, existing_full_parts=[ep1, ep2])` 从第3集开始
- **THEN** 3集全部通过后，合并文件包含所有三集内容

## 删除的需求

无。
