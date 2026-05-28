# Tasks

- [x] Task 1: 新增 `ImageDemandAnalyzer` agent
  - [x] 创建 `agents/image_demand_analyzer.py`
  - [x] 实现 `analyze(storyboard_content)` 方法：扫描分镜脚本，提取每个镜头的出场角色+场景
  - [x] 去重逻辑：同一角色 → 合并为一个条目，关联多个镜头
  - [x] 输出 JSON 写入 `07_生图需求/生图清单.json`
  - [x] 分类逻辑：随身道具归入角色条目，关键道具独立

- [x] Task 2: 管线中插入生图需求分析阶段
  - [x] `workflow.yaml` 新增 `image_demand_analyzer` 阶段（分镜后）
  - [x] `async_orch.py` 注册 `AGENT_TO_CONFIG` + `_get_input` 映射

- [x] Task 3: 生图项目模式改为清单 UI
  - [x] 新增 API `GET /api/projects/{name}/image-demands`
  - [x] `api.ts` 新增 `fetchImageDemands()`
  - [x] `ProjectImageGenForm.tsx` 新增需求清单展示模式
  - [x] 无视觉圣经数据时自动 fallback 到需求清单

- [x] Task 4: 道具融入角色提示词
  - [x] `generate_character_prompt` 新增 accessories 行
  - [x] `_build_style_declaration` 新增配件指引

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 1（需要后端 API）
- Task 4 依赖 Task 1
- Task 3 和 Task 4 可并行
