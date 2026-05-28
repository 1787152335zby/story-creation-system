# 任务列表

## 已完成的任务（上一轮）
- [x] Task 1: 后端 — `run()` 和 `continue_run()` 中 paused 改为 break
- [x] Task 2: 后端 — `_resume_chunked_approval` 中 confirm 和 approve 修正
- [x] Task 3: 后端 — `ws_manager.py` 中 `proceed` 处理检测 pending_episode
- [x] Task 4: 前端 — 处理 `phase_paused` 消息
- [x] Task 5: 前端 — `Workspace.tsx` 新增暂停态 UI
- [x] Task 6: 构建、验证并重启

## 本轮新增任务

- [x] Task 7: 确认 `total_chunks` 变量已修复且服务器加载了新代码
  - [x] 确认 `async_orch.py` 第 1188 行是 `chunk_count` 而非 `total_chunks`
  - [x] 清除 `__pycache__` 缓存，确保服务器使用最新代码
  - [x] 重启服务器，验证无 `NameError`

- [x] Task 8: `continue_run()` 中区分 resume 场景
  - [x] `_resume_chunked_approval` 返回 `False` 时检查 `_proceed_resume` 标记
  - [x] 无标记（初始回入）：发送 `phase_paused`，`paused_phase = True`，`continue`
  - [x] 有标记（用户继续）：清除标记，保留生成流程

- [x] Task 9: `ws_manager.py` proceed 处理器设置 `_proceed_resume`
  - [x] 在 `pending_episode` 存在时，设置 `project.config["_proceed_resume"] = True`
  - [x] 调用 `project.save_config()` 持久化

- [x] Task 10: 构建验证并重启
  - [x] Python 语法验证通过
  - [x] 前端构建成功
  - [x] 所有前端测试通过
  - [x] 清除 `__pycache__/server/` 缓存
  - [x] 重启服务器
  - [x] 验证：生成第 1 集 → 点"完成" → 显示"继续生成下一集"
  - [x] 验证：退首页再回来 → 显示"继续生成下一集"
  - [x] 验证：点"继续生成下一集" → 正确生成第 2 集
  - [x] 验证：生成第 2 集后不点任何按钮 → 退首页再回来 → 显示完成/通过/修改按钮
  - [x] 验证：点"完成" → 退首页再回来 → 显示"继续生成下一集"
  - [x] 验证：场景串联（1→2→3 逐集完成）

# Task Dependencies

- Task 7 是基础验证
- Task 8 和 Task 9 可以并行
- Task 10 依赖前 3 个 Task
