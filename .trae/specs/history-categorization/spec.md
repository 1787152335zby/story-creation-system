# 创作历史分类优化 Spec

## Why

当前历史页只有 4 个平铺 Tab：全部 / 自由模式 / 项目模式 / 视频。问题：

1. **视频无元数据** — 不存 `mode` / `project_name`，所有视频混在一起，看不出是自由生成还是项目生成的
2. **项目图片不分项目** — 项目模式的所有图片平铺显示，用户想找"某个项目的图片"得逐张翻
3. **Tab 粒度太粗** — "视频"是一个 Tab 但里面可能混了自由和项目模式的内容，用户无法按场景筛选

## What Changes

### 后端

1. **视频生成后也写入元数据 JSON** — `_meta/{filename}.json` 中存 `mode`（free/project）、`prompt`、`model`、`resolution`、`duration`、`negative_prompt`、`project_name`（仅项目模式）、`timestamp`
2. **历史 API 返回结构扩展** — 从 `{images_free, images_project, videos}` 改为 `{images_free, images_project, videos_free, videos_project, video_raw}`，同时支持按项目分组

### 前端

3. **历史页 Tab 重构** — 二级分组结构：

```
Tab 栏：全部 | 图片 | 视频

┌─ 全部 ───────────────────┐
│  [图片网格 (free+project) ]  │
│  [视频网格]                  │
└────────────────────────────┘

┌─ 图片 ────────────────────┐
│  筛选: [自由模式 ▼]         │
│  ┌ 自由模式（平铺）         │
│  └ 项目模式 → 按项目分组    │
│     ├─ 项目A (3张)          │
│     ├─ 项目B (5张)          │
│     └─ ...                  │
└────────────────────────────┘

┌─ 视频 ────────────────────┐
│  筛选: [自由模式 ▼]         │
│  ┌ 自由模式                 │
│  └ 项目模式 → 按项目分组    │
└────────────────────────────┘
```

- **图片 Tab**：二级筛选 dropdown（自由模式 / 项目模式），项目模式下按 project_name 分组展示，每组带项目名标题
- **视频 Tab**：同理，自由模式 / 项目模式，项目模式下按项目分组
- **全部 Tab**：保持当前布局，图片 + 视频混排，但视频卡片标注来源（自由/项目·项目名）

## Impact

- Affected specs: 历史页、视频生成
- Affected code:
  - `server/routes/gen.py` — `free_video_gen` 写入元数据；`list_generated_history` 返回结构扩展
  - `src/pages/HistoryPage.tsx` — Tab 重构、二级分组、项目分组渲染
  - `src/lib/types.ts` — 可能需扩展 HistoryEntry / HistoryVideo

## ADDED Requirements

### Requirement: 视频元数据持久化

The system SHALL store metadata for generated videos, matching the image metadata pattern.

#### Scenario: 自由模式视频生成
- **WHEN** `free_video_gen` 成功返回视频
- **THEN** 在 `_meta/{filename}.json` 写入 `{mode: "free", prompt, model, resolution, duration, negative_prompt, timestamp}`

#### Scenario: 项目模式视频生成（项目镜头）
- **WHEN** 项目模式生成视频
- **THEN** 元数据额外包含 `project_name: req.project_name`、`mode: "project"`

### Requirement: 历史 API 返回结构扩展

The system SHALL return grouped video data in the history API.

#### Scenario: 历史查询
- **WHEN** 前端调用 `GET /generated-history`
- **THEN** 返回体包含 `images_free`, `images_project`, `videos_free`, `videos_project`, `video_raw`（全部视频）
- **AND** 每个条目带 `mode` 和可选的 `project_name` 字段

### Requirement: 历史页二级分组 Tab

The system SHALL support hierarchical browsing in the history page.

#### Scenario: 图片浏览
- **WHEN** 用户切换到"图片"Tab
- **THEN** 显示筛选 dropdown（自由模式 / 项目模式）
- **AND** 项目模式下按 `project_name` 分组展示
- **AND** 每个分组的头部显示项目名和图片数量

#### Scenario: 视频浏览
- **WHEN** 用户切换到"视频"Tab
- **THEN** 同理显示自由模式/项目模式筛选
- **AND** 项目模式下按项目分组展示

## MODIFIED Requirements

### Requirement: 历史 API（原）

原返回体 `{images_free, images_project, videos}` 保留 `videos` 字段向后兼容，新增 `videos_free` 和 `videos_project`。`videos` 字段可标记为未来弃用。

## REMOVED Requirements

无
