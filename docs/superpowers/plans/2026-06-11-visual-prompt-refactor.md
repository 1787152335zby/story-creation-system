# 视觉提取/提示词/生图重构 — 实施计划

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 重写视觉提取（分段+主次分类）、新建提示词独立模块、统一生图页面项目模式

**涉及文件清单：**

| # | 文件 | 操作 |
|---|------|------|
| 1 | `workflow.yaml` | 修改阶段顺序 |
| 2 | `core/visual_bible.py` | **重写** |
| 3 | `agents/visual_extractor.py` | 适配 |
| 4 | `agents/prompt_factory.py` | **新建** |
| 5 | `server/routes/prompt_gen.py` | **新建** |
| 6 | `server/app.py` | 注册新路由 |
| 7 | `server/routes/projects.py` | 添加视觉提取 CRUD |
| 8 | `src/lib/api.ts` | 添加新 API 函数 |
| 9 | `src/pages/ImageGenPage.tsx` | **重写**项目模式 |

---

### Task 1: 调整工作流顺序

**文件：** `workflow.yaml`

把 `visual_extractor` 移到 `prompt_engineer` 之前。

### Task 2: 重写视觉提取

**文件：** `core/visual_bible.py` + `agents/visual_extractor.py`

- 分段提取：按"第X场"分割剧本，每段调用 LLM，合并去重
- 主次分类：Prompt 指示 LLM 区分 main/minor
- 新增字段：expression、pose、accessories、related_scenes
- 状态字段：status (pending/confirmed)

### Task 3: 新建提示词模块

**文件：** `agents/prompt_factory.py` + `server/routes/prompt_gen.py`

- PromptFactory 类：generate_character_prompt、generate_scene_prompt、generate_storyboard_prompt
- API 路由：POST /api/prompt-gen/character、/scene、/storyboard

### Task 4: 后端 API

**文件：** `server/routes/projects.py` + `server/app.py`

- POST /api/visual-extract/{name}/confirm
- POST /api/visual-extract/{name}/characters （补全单个角色）
- PUT /api/visual-extract/{name}/characters/{char_name}
- DELETE /api/visual-extract/{name}/characters/{char_name}
- app.py 注册 prompt_gen 路由

### Task 5: 前端 API 函数

**文件：** `src/lib/api.ts`

- confirmVisualExtract、addVisualCharacter、updateVisualCharacter、deleteVisualCharacter
- generateCharacterPrompt、generateScenePrompt、generateStoryboardPrompt

### Task 6: 重写 ImageGenPage 项目模式

**文件：** `src/pages/ImageGenPage.tsx`

- 项目模式：视觉提取按钮 → 角色/场景多选 → 自动生成提示词 → 编辑 → 生成
- 与自由模式共用同套 UI 组件
