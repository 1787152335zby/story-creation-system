# 修复大纲修改时错误生成方向卡 Spec

## Why
在大纲生成环节，用户点击"修改"并提交修改意见后，后端重新生成了方向卡（版本A/B）而非根据修改意见生成完整大纲。导致前端出现"方向卡选择完毕"的错乱界面，用户无法真正修改大纲内容。

## Root Cause
后端有三个代码路径在构造修改输入时使用了错误的内容变量：

1. **[async_orch.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py#L1063-L1064) `_resume_approval()`**: 使用已保存的大纲文件内容（`output_content`）拼接修改意见，该内容不包含"用户选择"或"请生成版本"关键词，导致 `OutlineDesigner.run_stream()` 的阶段检测（[outline_designer.py:L28](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/agents/outline_designer.py#L28)）误判为第一阶段，调用 `_generate_direction_card()` 而非 `_generate_full_outline()`。

2. **[async_orch.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py#L602) `continue_run()` 大纲审核循环**: 使用原始任务文本（`input_content`）拼接修改意见，同样不包含"用户选择"/"请生成版本"关键词，导致错误路由到方向卡生成。

3. **[async_orch.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py#L659) `continue_run()` 通用审核循环**: 同上。

**对比正确路径**: `run()` 方法中的大纲审核循环（[async_orch.py:L286](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py#L286)）正确使用了 `second_input`（包含"## 用户选择\n请生成版本{X}的完整大纲。"），能正确路由到 `_generate_full_outline()`。

## What Changes
- **修复 `_resume_approval()`**: 在大纲阶段修改时，构造包含"用户选择"标记的 `revised_input`，确保路由到完整大纲生成
- **修复 `continue_run()` 大纲审核循环 (L597-607)**: 使用 `second_input` 替代 `input_content` 拼接修改意见
- **修复 `continue_run()` 通用审核循环 (L649-669)**: 对大纲阶段的修改做特殊处理，使用 `second_input` 而非 `input_content`

## Impact
- Affected specs: 大纲修改与审核流程
- Affected code:
  - [async_orch.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/async_orch.py) — `_resume_approval()`, `continue_run()` 大纲审核循环, 通用审核循环
  - [outline_designer.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/agents/outline_designer.py) — 阶段检测逻辑（无需修改，明确其仅依赖 input_content 关键词检测）

## MODIFIED Requirements

### Requirement: 大纲修改必须生成完整大纲而非方向卡
系统 SHALL 在大纲阶段的"修改"操作中，始终调用 `_generate_full_outline()` 生成修正后的完整大纲，而非重新生成方向卡。

#### Scenario: 用户在审核界面点击修改并提交
- **GIVEN** 用户已选择方向卡版本，完整大纲已生成并进入审核界面（`awaiting_approval`状态）
- **WHEN** 用户点击"修改"，输入修改意见，点击"提交修改"
- **THEN** 系统 SHALL 根据修改意见重新生成完整大纲（调用 `_generate_full_outline()`）
- **AND** 前端 SHALL 保持在审核界面（`awaiting_approval`），不再显示方向卡选择（`awaiting_version`）

#### Scenario: 用户刷新页面后恢复审核状态并修改
- **GIVEN** 用户在大纲审核阶段刷新页面，系统通过 `continue_run()` 恢复审核状态
- **WHEN** 用户点击"修改"，输入修改意见，点击"提交修改"
- **THEN** 系统 SHALL 根据修改意见重新生成完整大纲（调用 `_generate_full_outline()`）
- **AND** 前端 SHALL 保持审核界面，不跳转方向卡选择

#### Scenario: 用户通过阶段恢复功能修改已保存的大纲
- **GIVEN** 用户通过 `_resume_approval()` 恢复大纲审核状态
- **WHEN** 用户提交修改意见
- **THEN** 系统 SHALL 根据修改意见重新生成完整大纲（调用 `_generate_full_outline()`）
- **AND** 不应重新生成方向卡

### Requirement: OutlineDesigner 阶段检测逻辑保持不变
[outline_designer.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/agents/outline_designer.py#L28-L35) 的阶段检测逻辑（通过检测 `input_content` 中是否包含"用户选择"或"请生成版本"关键词）保持不变。修复方案应在调用方（`async_orch.py`）层面确保传入正确的 `input_content`，而非修改 Agent 内部的检测逻辑。
