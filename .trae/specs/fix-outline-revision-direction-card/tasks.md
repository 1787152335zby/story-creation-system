# Tasks

- [x] Task 1: 修复 `_resume_approval()` 大纲修改输入
  - [x] 在 [async_orch.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py#L1063-L1064) 的 `_resume_approval()` 方法中，判断当前阶段是否为大纲阶段（`phase.agent == "outline_designer"`）
  - [x] 如果是大纲阶段，将 `revised_input` 构造为 `"## 用户选择\n请生成版本A的完整大纲。\n\n## 修改意见\n{feedback}"` 格式，确保包含"用户选择"和"请生成版本"关键词
  - [x] 如果是非大纲阶段，保持原有逻辑不变（使用 `output_content` 拼接修改意见）
  - [x] 验证：修改后的大纲内容能被正确写入原输出文件路径

- [x] Task 2: 修复 `continue_run()` 大纲审核循环修改输入
  - [x] 在 [async_orch.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py#L597-L607) 的 `continue_run()` 大纲审核循环中，将 `revised_input = input_content + "\n\n## 修改意见\n" + feedback` 改为 `revised_input = second_input + "\n\n## 修改意见\n" + feedback`
  - [x] 确保修改后重新发送 `phase_complete` 通知前端刷新内容
  - [x] 验证：修改后的大纲内容不是方向卡格式，而是完整大纲格式

- [x] Task 3: 检查并修复 `continue_run()` 通用审核循环 (L649-669) 对大纲阶段的处理
  - [x] 确认 L649-669 的通用审核循环不会对大纲阶段触发（大纲有自己的审核循环 L597-607）：已验证，L654 位于 L621 `else:` 非大纲分支内，大纲阶段通过 L620 `continue` 跳过
  - [x] 无需修改

# Task Dependencies
- Task 1, Task 2, Task 3 相互独立，可以并行处理
