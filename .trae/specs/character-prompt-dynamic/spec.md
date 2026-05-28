# 角色提示词动态拼装 Spec

## Why

当前角色生图流程存在 5 个问题：

1. **提示词混在一起** — 点击「林溪」拿到的是三种形象的混合描述，因为前端读的是 `06_提示词/角色提示词.md` 这个扁平 Markdown，变体信息没有独立段落
2. **变体提示词为空** — 点击「林溪_濒死」拿不到任何提示词，因为 Markdown 里没有这个标题
3. **变体不带基础图** — 点变体时应该自动加载基础角色的已确认图片作为参考图，但现在不会
4. **无风格注入** — 项目配置的 2D/3D/写实等风格不会体现在提示词中
5. **与视频生成脱节** — 生图用的提示词和视频用的角色描述来自两个不同的数据源

## What Changes

### 核心思路

放弃读 `06_提示词/角色提示词.md` 这个扁平的 Markdown 文件，改用已有的 `05_角色场景/角色/*.json` 结构化数据，通过后端的 `PromptBuilder.generate_character_prompt()` 方法实时动态拼装提示词。

### 具体改动

#### 后端

1. **新建 `/projects/{name}/character-prompt` 端点** — 接受角色名（含变体名如 `林溪_濒死`），返回动态拼装的提示词+参考图信息
   - 基础角色 → 只拼外貌/服装/特征 + 纯白背景
   - 变体角色 → 拼基础外貌+差异变化，同时返回 `base_character` 字段供前端加载基础图的参考图
   - 从项目配置读取 `style_type`（2D/3D/写实等）注入到提示词开头

2. **新建 `/projects/{name}/character-confirmed-images` 端点** — 返回指定角色已确认的最新图片 URL 列表（供变体场景自动加载参考图）

#### 前端

3. **修改 `handleCharSelect`** — 从调用 `generateSelectionPrompt` 改为调用新的 `fetchCharacterPrompt` API
4. **变体自动加载参考图** — 当 selectedChar 是变体时，自动加载基础角色的已确认图片
5. **风格标记渲染** — 项目选择区域显示当前项目的风格标记

#### 管线生成优化（仅 LLM 生成阶段影响）

6. **`PromptFactory` 生成提示词时** — 如果角色描述中有"服装：第一场穿A，第二场穿B"这种跨场次差异，在角色 JSON 中自动拆分为变体（`is_base: false, clothing_change: "换穿B"`），减少人工编辑

## Impact

- Affected specs: 图像生成（项目模式）、提示词生成管线
- Affected code:
  - `server/routes/projects.py` — 新建 character-prompt + character-confirmed-images 端点
  - `server/routes/gen.py` — 无改动（生图 API 本身逻辑不变，只是输入变了）
  - `src/pages/ImageGenPage.tsx` — handleCharSelect 改造、变体参考图自动加载
  - `src/lib/api.ts` — 新增 fetchCharacterPrompt + fetchCharacterConfirmedImages
  - `agents/prompt_factory.py` — PromptBuilder.generate_character_prompt 增加 style 参数注入

## ADDED Requirements

### Requirement: 角色提示词动态拼装

The system SHALL assemble character generation prompts dynamically from structured JSON data.

#### Scenario: 点击基础角色
- **WHEN** 用户在项目模式点击「林溪」
- **THEN** 后端从 `05_角色场景/角色/林溪.json` 读取结构化数据
- **AND** 调用 `PromptBuilder.generate_character_prompt()` 拼装提示词
- **AND** 提示词包含外貌、服装、特征、姿态等字段
- **AND** 结尾有「纯白背景，角色居中，全身照」纯角色约束
- **AND** 风格声明（2D/3D/写实）注入到提示词

#### Scenario: 点击变体角色
- **WHEN** 用户点击「林溪_濒死」
- **THEN** 后端拼装变体提示词（基于林溪的差异描述）
- **AND** 返回 `base_character: "林溪"` 字段
- **AND** 前端自动加载「林溪」已确认的图片作为参考图

#### Scenario: 服装变化自动拆分为变体
- **WHEN** LLM 生成的角色描述包含跨场次服装变化
- **THEN** `PromptFactory` 在写入 JSON 时自动拆分为 `is_base: false` 的变体 JSON 文件

## MODIFIED Requirements

### Requirement: handleCharSelect（原有）

修改为调用新 API `fetchCharacterPrompt` 而非 `generateSelectionPrompt`。当返回结果包含 `base_character` 字段时，自动加载基础角色已确认图片。

### Requirement: generateSelectionPrompt（原有）

保留作为项目批量场景生成使用，不再用于角色生图。前端角色选择不再走此路径。

## REMOVED Requirements

无
