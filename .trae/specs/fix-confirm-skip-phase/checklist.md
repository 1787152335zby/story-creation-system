# 验证清单

## Task 1: 参数化 _run_chunked_generation
- [x] 函数签名为 `async def _run_chunked_generation(self, agent_class, project, style, input_content, project_name, output_path, phase_index, start_ci=0, existing_full_parts=None)`
- [x] `ci` 初始值 = `start_ci`
- [x] `full_parts` = `list(existing_full_parts or [])`
- [x] while 循环条件 `ci < len(indices)` 正确

## Task 2: 完成键暂停
- [x] `action == "confirm"` 时检查 `ci < total_chunks - 1`
- [x] 有剩余集：更新 pending_episode 为 ci+1，返回 paused
- [x] 无剩余集：返回 confirmed
- [x] 返回 paused 时不写入合并文件

## Task 3: 调用方处理 paused
- [x] `run()` 中 `cr.get("action") == "paused"` 时不 mark_phase_done
- [x] `continue_run()` 中同上
- [x] `redo_phase()` 中同上

## Task 4: 恢复逐集生成
- [x] `_resume_chunked_approval` 文件不存在时返回 False
- [x] `continue_run` 中降级到正常流程，传递 `start_ci=chunk_resume_ci`
- [x] `run()` 设 `chunk_resume_ci = 0`
