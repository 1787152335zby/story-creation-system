# 修复新建项目向导的 7 个 Bug

## 为什么

新建项目向导（NewProjectWizard）是入口页面，存在多个 Bug 影响用户体验：模型选择页面不可见、情绪氛围数据丢失、模型选择不生效等。

## 变更内容

- **修复模型选择页面不可达**：第 3 步后显示第 4 步（模型选择），而非直接创建
- **修复选模型不生效**：前端传 selectedModel，后端保存到 project_config
- **修复 `mood` 字段前端类型缺失**：StyleConfig 接口增加 `mood: string`
- **修复后端未保存 `mood`**：create_project handler 保存 mood
- **新增必填校验**：故事类型/故事描述为空时按钮禁用并提示
- **修复 API Key 检查不全**：增加 aggregated_configs 检查
- **修复无错误处理**：fetchAvailableModels 和 fetchTemplates 增加 .catch()

## 影响范围

- 受影响的代码：
  - `src/pages/NewProjectWizard.tsx` — 步骤逻辑、校验、传参
  - `src/lib/api.ts` — StyleConfig 接口增加 mood
  - `server/routes/projects.py` — 保存 mood 和 selected_model
  - `server/schemas.py` — CreateProjectRequest 增加 model 字段

---

## 需求

### 需求 1：修复步骤逻辑

**系统 SHALL** 支持 4 步流程：步骤 0→1→2→3→4（故事类型→风格偏好→时长设置→故事描述→模型选择）。

- 步骤 0-3 显示"下一步"按钮
- 步骤 4（模型选择）显示"开始创作"按钮
- 第 3 步（故事描述）不显示"开始创作"

**WHEN** 用户在步骤 4 点击"开始创作"
**THEN** 调用 `handleCreate()` 创建项目

### 需求 2：传递选中的模型

**系统 SHALL** 在 `handleCreate()` 中把 `selectedModel` 传递给 API。

前端：
```typescript
const r = await createProject({
    name: projectName || 'untitled',
    story_idea: storyIdea,
    style,
    duration_line: dl,
    model: selectedModel,
})
```

后端：
```python
# CreateProjectRequest 新增 model 字段
# create_project handler 保存
project.config["selected_model"] = req.model
project.save_config()
```

### 需求 3：修复 mood 字段

**系统 SHALL** 在 `api.ts` 的 `StyleConfig` 接口中增加 `mood: string`。

**系统 SHALL** 在 `create_project` handler 中保存 `req.style.mood` 到 `project.config`。

### 需求 4：必填校验

**系统 SHALL** 在点击"下一步"时校验当前步骤必填项：

- 步骤 0：故事类型 `story_type` 不能为空
- 步骤 3：故事描述 `storyIdea` 不能为空

**WHEN** 必填项为空时点击"下一步"
**THEN** 弹出提示消息

### 需求 5：API Key 检查增加 aggregated_configs

**系统 SHALL** 在 `handleCreate()` 中检查 `settings.aggregated_configs` 是否包含有效的配置。

```typescript
const aggKeys = settings?.aggregated_configs?.filter((c: any) => c.api_key) || []
const hasKey = settings?.deepseek_api_key || settings?.openai_api_key || settings?.claude_api_key || aggKeys.length > 0
```

### 需求 6：增加错误处理

**系统 SHALL** 在 `fetchAvailableModels()` 和 `fetchTemplates()` 调用后增加 `.catch()`：

```typescript
fetchAvailableModels().then(data => { ... }).catch(() => {})
fetchTemplates().then(setTemplates).catch(() => {})
```

## 删除的需求

无。
