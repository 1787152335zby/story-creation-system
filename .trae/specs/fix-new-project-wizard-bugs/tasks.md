# 任务列表

- [x] Task 1: 修复步骤逻辑（步骤 3 → 步骤 4 而非直接创建）
  - [x] 修改按钮条件：`step < 3` → `step < 4`
  - [x] 确认步骤 3 有"下一步"按钮指向步骤 4
  - [x] 确认步骤 4 显示"开始创作"按钮调用 handleCreate

- [x] Task 2: 传递选中的模型到后端
  - [x] `NewProjectWizard.tsx`：`createProject({ ..., model: selectedModel })`
  - [x] `api.ts`：`CreateProjectPayload` 增加 `model` 字段
  - [x] `schemas.py`：`CreateProjectRequest` 增加 `model: str = ""`
  - [x] `projects.py`：保存 `project.config["selected_model"] = req.model`

- [x] Task 3: 修复 mood 字段
  - [x] `api.ts`：`StyleConfig` 增加 `mood: string`
  - [x] `projects.py`：`project.config["mood"] = req.style.mood`

- [x] Task 4: 必填校验
  - [x] 步骤 0 点击"下一步"时检查 `style.story_type`
  - [x] 步骤 3 点击"下一步"时检查 `storyIdea`
  - [x] 为空时弹出 alert 提示

- [x] Task 5: API Key 检查增加 aggregated_configs
  - [x] `NewProjectWizard.tsx` handleCreate 中增加 aggKeys 检查

- [x] Task 6: 增加错误处理
  - [x] `fetchAvailableModels().catch()`
  - [x] `fetchTemplates().catch()`

- [x] Task 7: 构建验证并重启
  - [x] Python 语法验证通过
  - [x] 前端构建成功
  - [x] 前端测试通过
  - [x] 重启服务器

# Task Dependencies

- Task 1、2、3、4、5、6 可以并行
- Task 7 依赖前 6 个 Task
