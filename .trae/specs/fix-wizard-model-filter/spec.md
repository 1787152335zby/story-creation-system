# 新建项目向导按实际 LLM 后端过滤模型选择

## 为什么

当前模型选择器在新建项目向导中显示所有来源的所有模型（DeepSeek、OpenAI、Claude + 所有聚合平台的 LLM 模型），而实际系统只使用一个特定的 LLM 后端。用户只需要看到真正能用的模型的来源。

## 变更内容

- **后端**：`/settings/models` 返回 `active_llm_source` 字段，标识当前系统实际使用的 LLM 来源
- **前端**：`NewProjectWizard` 只显示 `active_llm_source` 对应的模型分组

## 影响范围

- `server/routes/settings.py` — 新增 `active_llm_source` 字段
- `src/pages/NewProjectWizard.tsx` — 过滤模型显示

---

## 需求

### 需求 1：后端标记当前使用的 LLM 来源

**系统 SHALL** 在 `/settings/models` 响应中增加 `active_llm_source` 字段。

确定规则：
1. 检查 `aggregated_configs.json`：是否有 `type == "llm"` 且 `active == true` 的配置
2. 如果有 → `{"type": "aggregated", "name": "xxx", "base_url": "..."}`
3. 如果没有 → 读取 `.env` 中的 `LLM_BACKEND` → `{"type": "official", "backend": "deepseek"}`

**WHEN** 用户有激活的 LLM 聚合配置（如 dmx）
**THEN** `active_llm_source = {"type": "aggregated", "name": "dmx", "base_url": "https://www.dmxapi.cn"}`

**WHEN** 用户使用官方 API（如 DeepSeek）
**THEN** `active_llm_source = {"type": "official", "backend": "deepseek"}`

### 需求 2：前端过滤模型显示

**系统 SHALL** 在 `NewProjectWizard.tsx` 中根据 `active_llm_source` 过滤模型列表：

- 如果 `active_llm_source.type == "aggregated"`：
  - 只显示名称匹配该聚合平台的模型分组（根据 `base_url` 判断）
  - 如果没有匹配的分组，显示该聚合平台的所有 LLM 模型作为一个分组
- 如果 `active_llm_source.type == "official"`：
  - 只显示对应官方提供商的分组（如 `active_llm_source.backend == "deepseek"` 只显示 DeepSeek 分组）

**WHEN** `active_llm_source = {type: "official", backend: "deepseek"}`
**THEN** 模型选择器中只显示 DeepSeek 分组的模型

**WHEN** `active_llm_source = {type: "aggregated", name: "dmx", base_url: "https://www.dmxapi.cn"}`
**THEN** 模型选择器中只显示从 dmx 平台拉取的模型

## 删除的需求

无。
