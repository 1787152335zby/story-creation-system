# 修复生图/视频项目模式无法提取角色场景道具信息 Spec

## Why
生图模式和视频模式的"项目模式"无法提取角色、场景、道具信息，视频模式甚至没有道具勾选框。导致用户无法在项目模式下使用已有的角色/场景/道具数据进行生图和视频创作。

## Root Cause
三个层面的缺陷叠加导致：

1. **后端 asset-library 端点缺失道具扫描**：[projects.py:L901-L939](file:///e:/AI/Trae CN/book/story-creation-system1.2/server/routes/projects.py#L901-L939) 的 `/api/projects/{name}/asset-library` 仅遍历 `characters` 和 `scenes`，完全没有扫描 `道具` 目录，而前端 `AssetLibrary` 类型定义中已包含 `props` 字段。

2. **VideoProjectPanel 缺少道具选择 UI**：[VideoProjectPanel.tsx](file:///e:/AI/Trae CN/book/story-creation-system1.2/src/components/VideoProjectPanel.tsx) 只有角色和场景的勾选框，完全没有道具勾选区域。对比 [ProjectImageGenForm.tsx:L801-L838](file:///e:/AI/Trae CN/book/story-creation-system1.2/src/components/ProjectImageGenForm.tsx#L801-L838)，生图模式有完整的道具选择界面。

3. **数据来源依赖视觉提取阶段**：`VisualBibleExtractor.list_characters/scenes/props()` 从 `04_角色场景/` 目录读取 JSON 文件。如果管线跳过了第4阶段（视觉提取），该目录为空，`fetchCharacters/fetchScenes/fetchProps` 返回空数组。VideoProjectPanel 有"视觉提取"按钮，但 ImageGenPage 的项目模式没有。

## What Changes
- **修复 asset-library 端点**：新增道具目录扫描，返回 `props` 数据
- **VideoProjectPanel 新增道具勾选区**：在角色和场景选择区之后添加道具选择 UI
- **ImageGenPage 新增视觉提取按钮**：当角色/场景/道具为空时允许用户手动触发提取

## Impact
- Affected specs: 生图项目模式、视频项目模式
- Affected code:
  - [projects.py](file:///e:/AI/Trae CN/book/story-creation-system1.2/server/routes/projects.py#L901-L939) — `get_project_asset_library` 端点
  - [VideoProjectPanel.tsx](file:///e:/AI/Trae CN/book/story-creation-system1.2/src/components/VideoProjectPanel.tsx) — 组件 UI 和状态
  - [ImageGenPage.tsx](file:///e:/AI/Trae CN/book/story-creation-system1.2/src/pages/ImageGenPage.tsx) — 视觉提取按钮和状态

## ADDED Requirements

### Requirement: asset-library 端点返回道具数据
系统 SHALL 在 `/api/projects/{name}/asset-library` 端点的返回数据中包含 `props` 字段，结构与 `characters` 和 `scenes` 一致。

#### Scenario: 项目有已生成的道具素材
- **GIVEN** 项目的 `07_生成素材/道具/` 目录下有版本目录和图片
- **WHEN** 调用 `/api/projects/{name}/asset-library`
- **THEN** 返回的 `result.props` 包含每个道具的 `confirmed_versions`、`all_versions` 和 `latest_confirmed` 信息

#### Scenario: 项目没有道具素材
- **GIVEN** 项目的 `07_生成素材/道具/` 目录不存在或为空
- **WHEN** 调用 `/api/projects/{name}/asset-library`
- **THEN** 返回的 `result.props` 为空对象 `{}`

### Requirement: VideoProjectPanel 包含道具选择 UI
系统 SHALL 在 VideoProjectPanel 中提供与 ProjectImageGenForm 一致的道具选择界面。

#### Scenario: 道具列表有数据
- **WHEN** `propsList` 非空
- **THEN** 显示道具勾选列表，包含道具名称、类型标签和勾选框

#### Scenario: 道具列表为空
- **WHEN** `propsList` 为空
- **THEN** 显示"暂无道具数据，点击「视觉提取」获取"

### Requirement: ImageGenPage 项目模式提供视觉提取入口
系统 SHALL 在 ImageGenPage 项目模式中，当角色/场景/道具数据为空时提供"视觉提取"按钮，允许用户手动触发数据提取。

#### Scenario: 数据为空时显示提取按钮
- **GIVEN** 用户进入生图项目模式，`characters` 和 `scenes` 均为空
- **THEN** 显示"🔄 视觉提取"按钮
- **WHEN** 点击按钮
- **THEN** 调用 `/api/projects/{name}/re-extract-visual`，提取完成后自动刷新角色/场景/道具列表
