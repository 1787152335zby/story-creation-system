# 验证清单

## Task 1: 简化按钮
- [x] `episode_complete` 后只显示"完成"和"修改"
- [x] 没有"通过并生成下一集"按钮
- [x] "完成"后正确进入暂停态

## Task 2: 修复刷新丢失进度
- [x] approve 时不调用 `clear_pending_episode()`
- [x] confirm 时仍调用 `clear_pending_episode()`
- [x] 刷新后 pending_episode 指向上次生成的集

## Task 3: 左侧集列表
- [x] 侧边栏显示已保存的集列表
- [x] 点击集显示对应内容
- [x] 新集生成后列表更新

## Task 4: 集数标识
- [x] `_build_gen_kwargs` 传入 `chunk_name`
- [x] `plot_expander.py` prompt 注入集数
- [x] `screenplay_writer.py` prompt 注入集数

## Task 5: 构建验证
- [x] Python 语法验证通过
- [x] 前端构建成功
- [x] 测试通过
- [x] 重启成功
- [x] 端到端验证通过
