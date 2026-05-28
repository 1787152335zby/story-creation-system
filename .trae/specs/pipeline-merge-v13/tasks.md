# Tasks

- [x] Task 1: 创建 `ImagePreparator` agent
  - [x] 创建 `agents/image_preparator.py`
  - [x] `prepare` 方法：读分镜脚本 → 提取出场角色/场景 → 按需调用 `VisualBibleExtractor` 补外观 → 调用 `PromptBuilder` 生成提示词 → 去重 → 写 `06_生图需求/生图清单.json`
  - [x] 输出 `06_生图需求/分析报告.md`
  - [x] 继承 `AgentBase`

- [x] Task 2: 更新 `workflow.yaml`
  - [x] 阶段4「视觉提取」condition 改为 `"story_type in ['4']"`（仅小说）
  - [x] 删除阶段6「提示词生成」
  - [x] 删除阶段7「生图需求分析」
  - [x] 新增阶段5「生图准备」agent: `image_preparator`，output: `06_生图需求/`

- [x] Task 3: 更新 `async_orch.py`
  - [x] `AGENT_TO_CONFIG` 新增 `"image_preparator": "image_prep"`，移除 `"prompt_factory"` 和 `"image_demand_analyzer"`
  - [x] `_get_input` 新增 `"image_preparator": "05_分镜脚本/分镜脚本.md"`
  - [x] `_get_output_path` filename_map 改为 `"06_生图需求/": "分析报告.md"`，移除 `"06_提示词/"`

- [x] Task 4: 更新前端阶段常量
  - [x] `src/lib/constants.ts` 更新为6阶段
  - [x] `src/pages/Workspace.tsx` MAIN_FILES 同步更新

- [x] Task 5: 更新生图 UI API 路径
  - [x] `/image-demands` 读 `06_生图需求/`（fallback 到 `07_生图需求/` 兼容旧项目）
  - [x] `/re-analyze-demands` 改为调 `ImagePreparator`

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 1
- Task 4 依赖 Task 2
- Task 5 可在 Task 1 完成后与其他并行
