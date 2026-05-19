# 修复"暂停"后无继续按钮问题 Spec

## 为什么

用户点"完成"（非最后集）时，`_run_chunked_generation` 返回 `paused`。调用方处理 `paused` 后执行 `break` 退出阶段 for 循环，然后代码无条件发送 `{"type": "all_complete"}`。前端收到 `all_complete` 后显示"全部完成"状态，没有任何"继续创作"按钮。

**根本原因**：`paused` handler 中 `break` 导致阶段循环提前终止，后续 `all_complete` 被错误发送。

## 变更内容

- **`continue_run` 的 paused 处理**：`break` 改为 `continue`，让阶段循环自然结束
- **跳过 `all_complete`**：当 paused 时，不发送 `all_complete`，只发送 `phase_complete` + `phase_confirmed` 后继续循环
- **相同修复应用于 `run()` 和 `redo_phase()` 中所有 paused handler**

## 影响范围

- 受影响的代码：
  - `server/async_orch.py` — `run()`、`continue_run()`、`redo_phase()` 中的所有 paused handler

---

## 需求

### 需求 1：paused 时阶段循环继续而非退出

**系统 SHALL** 在所有 paused handler 中将 `break` 改为 `continue`。

#### 场景：用户在第1集点"完成"（共3集）
- **WHEN** paused handler 执行
- **THEN** 发送 `phase_complete` + `phase_confirmed`
- **THEN** `continue` 进入下一个循环迭代（后续阶段无匹配，跳过）
- **THEN** 阶段循环自然结束

### 需求 2：paused 时不发送 `all_complete`

**系统 SHALL** 使用 `paused_phase` 标记，在发送 `all_complete` 前检查该标记。

```python
paused_phase = False
for idx in range(start_idx, total):
    ...
    elif phase.split:
        cr = await self._run_chunked_generation(...)
        if cr.get("confirmed"):
            ...
            break
        elif cr.get("action") == "paused":
            paused_phase = True
            ...
            continue

if not paused_phase:
    await self.ws.send_message(project_name, {"type": "all_complete"})
```

#### 场景：用户在第1集点"完成"（共3集）
- **WHEN** paused handler 执行，`paused_phase = True`
- **THEN** 跳过 `all_complete` 发送
- **THEN** 前端不进入"全部完成"状态
- **THEN** 前端保持已确认状态，显示"继续创作"按钮

### 需求 3：相同修复应用于所有方法

**系统 SHALL** 对 `run()` 和 `redo_phase()` 中所有 paused handler 做同样的 `break→continue` 修复。

- `run()` 有两个 paused handler（大纲路径 + 非大纲路径）
- `continue_run()` 有三个 paused handler（大纲路径、非大纲路径、`else` 分支的非大纲路径）
- `redo_phase()` 有一个 paused handler

## 删除的需求

无。
