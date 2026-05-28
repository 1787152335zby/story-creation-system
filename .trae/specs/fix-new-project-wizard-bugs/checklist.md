# 验证清单

## Task 1: 步骤逻辑
- [x] 步骤 3（故事描述）点击"下一步"进入步骤 4（模型选择）
- [x] 步骤 4 显示"开始创作"按钮而非"下一步"
- [x] 步骤 4 点击"开始创作"正常创建项目

## Task 2: 传递模型
- [x] `CreateProjectPayload` 有 `model: string`
- [x] `handleCreate` 传了 `selectedModel`
- [x] `CreateProjectRequest` 有 `model: str`
- [x] 后端保存了 `selected_model` 到项目配置

## Task 3: mood 字段
- [x] `StyleConfig` 接口有 `mood: string`
- [x] 后端保存了 `project.config["mood"]`

## Task 4: 必填校验
- [x] 步骤 0 不选故事类型点"下一步"提示
- [x] 步骤 3 不填故事描述点"下一步"提示

## Task 5: API Key 检查
- [x] aggregated_configs 中的 key 被正确检查

## Task 6: 错误处理
- [x] `fetchAvailableModels` 有 `.catch()`
- [x] `fetchTemplates` 有 `.catch()`

## Task 7: 构建验证
- [x] Python 语法验证通过
- [x] 前端构建成功
- [x] 前端测试通过
- [x] 服务器重启成功
