# 任务列表

- [x] Task 1: 简化审核按钮 — 移除"通过并生成下一集"，只保留"完成"+"修改"
  - [x] `Workspace.tsx` 在 episode_complete 后只显示"完成"和"修改"按钮
  - [x] `useWebSocket.ts` 删除 `episodeApprove` 导出

- [x] Task 2: 修复刷新丢失进度 — approve 时不 clear_pending_episode
  - [x] `async_orch.py` `_run_chunked_generation` 中 `action == "approve"` 分支删除 `clear_pending_episode()`
  - [x] 确认 confirm 分支仍调用 `clear_pending_episode()`

- [x] Task 3: 左侧侧边栏显示已保存集列表
  - [x] `Workspace.tsx` 侧边栏组件根据 `chunksCompleted` 渲染集列表
  - [x] 点击集列表项时读取并展示该集内容
  - [x] 新增后端接口或复用现有接口读取单个 chunk 文件

- [x] Task 4: prompt 传入集数标识
  - [x] `async_orch.py` `_build_gen_kwargs` 增加 `chunk_name=display_name`
  - [x] `agents/plot_expander.py` `generate_chunk` 接收 `chunk_name` 并注入 prompt
  - [x] `agents/screenplay_writer.py` `generate_chunk` 接收 `chunk_name` 并注入 prompt
  - [x] `agents/storyboarder.py` `generate_chunk` 接收 `chunk_name` 并注入 prompt
  - [x] `agents/prompt_engineer.py` `generate_chunk` 接收 `chunk_name` 并注入 prompt

- [x] Task 5: 构建验证并重启
  - [x] Python 语法验证通过
  - [x] 前端构建成功
  - [x] 测试通过
  - [x] 重启服务器
  - [x] 验证：生成第 1 集后只显示"完成"+"修改"
  - [x] 验证：点击"完成" → 显示"继续生成下一集"
  - [x] 验证：左侧可点击查看第 1 集内容
  - [x] 验证：第 2 集生成后左侧显示第 1 集和第 2 集
  - [x] 验证：生成的剧情开头标明了"第 X 集"

# Task Dependencies

- Task 1 和 Task 3 可以并行
- Task 2 是后端独立修复
- Task 4 是后端 agent 修改
- Task 5 依赖前 4 个 Task
