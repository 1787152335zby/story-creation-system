# 任务列表

- [x] Task 1: 后端 — `/settings/models` 增加 `active_llm_source` 字段
  - [x] 读取 `aggregated_configs.json` 查找活跃的 LLM 配置
  - [x] 无活跃 LLM 聚合配置时读取 `LLM_BACKEND` 环境变量
  - [x] 返回 `active_llm_source` 字段

- [x] Task 2: 前端 — 根据 `active_llm_source` 过滤模型列表
  - [x] `fetchAvailableModels` 返回值类型增加 `active_llm_source`
  - [x] `NewProjectWizard.tsx` 获取到数据后过滤 `llm_groups`
  - [x] 聚合平台只显示该平台的 LLM 模型分组
  - [x] 官方 API 只显示对应提供商的分组

- [x] Task 3: 构建验证
  - [x] Python 语法验证通过
  - [x] 前端构建成功
  - [x] 重启服务器

# Task Dependencies

- Task 1 和 Task 2 可以并行
- Task 3 依赖前 2 个 Task
