# Checklist

- [x] `_resume_approval()` 大纲阶段修改使用包含"用户选择"和"请生成版本"标记的输入
- [x] `continue_run()` 大纲审核循环（L597-607）使用 `second_input` 而非 `input_content` 拼接修改意见
- [x] `continue_run()` 通用审核循环（L649-669）不对大纲阶段错误触发
- [x] 大纲修改后生成的是完整大纲内容（包含人物设定、情节梗概等），而非方向卡（版本A/B对比）
- [x] 大纲修改后前端保持 `awaiting_approval` 状态，不跳转到 `awaiting_version` 方向卡选择界面
- [x] 非大纲阶段的修改逻辑不受影响（回归验证）
- [x] `run()` 初始流程中的大纲审核循环（L281-291）保持原有正确逻辑不变
