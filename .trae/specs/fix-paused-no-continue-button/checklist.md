# 验证清单

## Task 1: continue_run()
- [x] 阶段循环前有 `paused_phase = False`
- [x] 所有 paused handler 中设置 `paused_phase = True`
- [x] 所有 paused handler 中 `break` → `continue`
- [x] `all_complete` 前检查 `if not paused_phase`

## Task 2: run()
- [x] 阶段循环前有 `paused_phase = False`
- [x] 所有 paused handler 中设置 `paused_phase = True`
- [x] 所有 paused handler 中 `break` → `continue`
- [x] `all_complete` 前检查 `if not paused_phase`

## Task 3: redo_phase()
- [x] `return` 在当前上下文中正确（无循环、无 all_complete）

## 端到端测试
- [ ] 第1集→点"完成"→显示绿色横幅"已确认"+ 继续创作按钮
- [ ] 第2集→点"完成"→同上，第3集正常
- [ ] 点"通过并生成下一集"→自动下一集（不变）
- [ ] 最后一集→点"完成"→阶段完成→继续创作→下一阶段
