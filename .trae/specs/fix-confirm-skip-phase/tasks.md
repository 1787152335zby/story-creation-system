# 任务列表

- [x] Task 1: `_run_chunked_generation` 增加 start_ci / existing_full_parts 参数
  - [x] 函数签名增加 `start_ci=0, existing_full_parts=None`
  - [x] `ci` 的初始值改为 `start_ci`
  - [x] `full_parts` 初始化为 `existing_full_parts or []`
  - [x] `while ci < len(indices):` 循环从 start_ci 开始

- [x] Task 2: "完成"在非最后集时暂停
  - [x] `action == "confirm"` 时检查 `ci < total_chunks - 1`
  - [x] 有剩余集：更新 `pending_episode` 为下一集（ci+1），返回 `{"action": "paused"}`
  - [x] 最后一集：继续现有行为，返回 `{"action": "confirm", "confirmed": True}`

- [x] Task 3: 调用方识别 paused
  - [x] `run()` 的 chunk 调用点检查 `cr.get("action") == "paused"`，不 mark_phase_done，发送 phase_complete + phase_confirmed，break
  - [x] `continue_run()` 的 chunk 调用点同上
  - [x] `redo_phase()` 的 chunk 调用点同上

- [x] Task 4: continue_run 恢复逐集生成
  - [x] `_resume_chunked_approval` 返回 False 时（文件不存在），`continue_run` 降级到正常生成流程
  - [x] `continue_run` 设 `chunk_resume_ci` 变量，传递 `start_ci` 给 `_run_chunked_generation`
  - [x] `run()` 也设 `chunk_resume_ci = 0`

- [x] Task 5: 构建、验证并重启
  - [x] Python 语法验证通过
  - [x] 前端构建成功
  - [x] 系统已重启
