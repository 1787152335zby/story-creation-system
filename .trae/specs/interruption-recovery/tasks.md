# 任务列表

- [x] Task 1: 修复线程取消 Bug
  - [x] 在 `_run_chunked_generation` 的 while True 循环外层添加 `except asyncio.CancelledError`，设置 `cancelled[0] = True`，然后 `raise`
  - [x] 验证：生成中刷新页面，后台线程不再泄漏

- [x] Task 2: 添加逐集审核状态的持久化
  - [x] 在 `core/project_manager.py` 添加 `set_pending_episode(phase_index, chunk_index, chunk_name, total_chunks)` 方法
  - [x] 添加 `clear_pending_episode()` 方法
  - [x] 添加 `pending_episode` property
  - [x] 在 `_run_chunked_generation` 中，每集生成并保存文件后，调用 `project.set_pending_episode(...)`
  - [x] 在本集审核通过（`ci += 1`）时，清除持久化状态
  - [x] 在本集审核完成（`action == "confirm"`）时，调用 `project.clear_pending_episode()`

- [x] Task 3: continue_run 检测逐集断点
  - [x] 在 `run()` 和 `continue_run()` 的循环中添加 pending_episode 检测
  - [x] 如果匹配，调用 `_resume_chunked_approval` 恢复
  - [x] 新增 `_resume_chunked_approval(project, project_name, phase_index, pending_ep)` 方法
  - [x] `_resume_chunked_approval` 读取已保存的 chunk 文件，重放内容，发送 `episode_complete`，阻塞等待用户

- [x] Task 4: 构建、验证并重启
  - [x] 验证 Python 语法通过
  - [x] 前端构建成功
  - [x] 重启系统
