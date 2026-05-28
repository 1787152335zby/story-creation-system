# 验证清单

## Task 7: 确认变量修复
- [x] `_run_chunked_generation` 第 1188 行使用 `chunk_count`
- [x] `__pycache__/server/` 已清除
- [x] 服务器重启后无 `NameError`

## Task 8: continue_run 区分 resume 场景
- [x] `_resume_chunked_approval` 返回 `False` 时检查 `_proceed_resume`
- [x] 无标记时发送 `phase_paused` 消息
- [x] 无标记时 `paused_phase = True` 且 `continue`
- [x] 有标记时清除标记并保留生成流程

## Task 9: ws_manager.py 设置 _proceed_resume
- [x] proceed 处理器在 `pending_episode` 存在时设置 `_proceed_resume = True`
- [x] 调用 `project.save_config()` 持久化

## Task 10: 构建验证
- [x] Python 语法验证通过
- [x] 前端构建成功
- [x] 前端测试全部通过
- [ ] 分集模式生成第 1 集 → 点"完成" → 显示"继续生成下一集"按钮
- [ ] 退首页再回来 → 显示"继续生成下一集"按钮
- [ ] 点击"继续生成下一集" → 正确生成第 2 集
- [ ] 生成第 2 集后不点按钮 → 退首页再回来 → 显示完成/通过/修改按钮
- [ ] 点"完成" → 退首页再回来 → 显示"继续生成下一集"
- [ ] 逐集完成直到最后一集 → 正常标记阶段完成
