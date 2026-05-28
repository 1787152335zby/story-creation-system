# 生图模式增强 Spec — 场景动态拼装 + 生图→视频自动同步

## Why

两个核心缺口：

1. **场景提示词仍是旧的** — 角色已改为从 JSON 动态拼装，但场景 `handleSceneSelect` 还在读 `06_提示词/场景提示词.md` 这个扁平 Markdown，变体场景拿不到提示词
2. **生图结果不会自动进入视频素材池** — 生好角色/场景图后，视频侧看不到，需要用户手动翻目录。项目模式的"生图→视频"全流程在"素材同步"这一环断裂

另外用户反馈高级参数面板偶尔无法展开，需要一并修复。

## What Changes

### A. 场景提示词动态拼装

#### 后端

1. **`POST /projects/{name}/scene-prompt`** — 接受场景名（含变体），调用 `PromptBuilder.generate_scene_prompt()` 返回实时拼装的场景提示词
   - 基础场景 → 环境/光线/色调/道具 + 视角描述
   - 变体场景 → 基础环境+差异变化 + 返回 `base_scene` 供前端加载参考图
   - 风格声明注入

2. **`GET /projects/{name}/scene-confirmed-images/{sceneName}`** — 返回指定场最已确认的最新图片 URL 列表

#### 前端

3. **修改 `handleSceneSelect`** — 从调 `generateSelectionPrompt` 改为调新的 `fetchScenePrompt` API
4. **变体自动加载参考图** — 返回 base_scene 时自动加载基础场景的已确认图片
5. **前端新增 `fetchScenePrompt` + `fetchSceneConfirmedImages`**

### B. 生图→视频自动打通

#### 生图侧

6. **自动确认版本** — `projectImageGen` 成功返回后，后端自动在 `generated/projects/{name}/characters|scenes/{entityName}/v{version}/` 写入 `_confirmed` 标记，不用用户手动点确认
7. **多版本累积** — 每次生成都是新版本号，旧版本保留不覆盖

#### 视频侧

8. **自动匹配参考图** — `VideoProjectPanel` 打开项目时，自动扫描 `generated/projects/{name}/characters|scenes/` 下的已确认版本，匹配当前分镜中的角色/场景名
   - 显示在「自动匹配参考图」区域，每个匹配项一张缩略图 + 角色名 + 版本号
9. **手动选择区** — 同区域下方展开后，可浏览该角色所有历史版本，点击替换
10. **路径切换** — `generate_project_shot` 从 `07_视觉素材` 改为从 `generated/` 路径读取已确认版本

#### 后端

11. **视频侧新增端点** — `GET /projects/{name}/asset-library` — 返回项目下所有角色/场景的已确认图版本汇总（供视频页自动匹配用）

### C. 修复高级参数面板

12. 排查高级参数面板在自由/项目模式下无法展开的问题，大概率是 z-index 或事件冒泡问题

## Impact

- Affected specs: 图像生成（项目模式）、视频生成（项目模式）
- Affected code:
  - `server/routes/projects.py` — 新增 scene-prompt + scene-confirmed-images + asset-library 端点
  - `src/pages/ImageGenPage.tsx` — handleSceneSelect 改造
  - `src/lib/api.ts` — 新增 fetchScenePrompt + fetchSceneConfirmedImages
  - `server/routes/gen.py` — projectImageGen 自动确认版本；generate_project_shot 路径切换
  - `src/components/VideoProjectPanel.tsx` — 自动匹配参考图区
  - `src/components/ProjectAssetPicker.tsx` — 从 generated/ 读取
  - `src/components/AdvancedParamsPanel.tsx` — 修复不可点展开

## ADDED Requirements

### Requirement: 场景提示词动态拼装

#### Scenario: 点击基础场景
- **WHEN** 用户在项目模式点击「空洞·第一次接触」
- **THEN** 后端从 `05_角色场景/场景/空洞·第一次接触.json` 读取结构化数据
- **AND** 调用 `PromptBuilder.generate_scene_prompt()` 拼装提示词
- **AND** 包含环境/光线/色调/道具 + 视角描述

#### Scenario: 点击变体场景
- **WHEN** 用户点击变体场景
- **THEN** 后端拼装变体提示词（基础环境+差异变化）
- **AND** 返回 `base_scene` 字段
- **AND** 前端自动加载基础场景的已确认图片

### Requirement: 自动同步参考图

#### Scenario: 项目模式生图完成
- **WHEN** 项目模式 `projectImageGen` 成功返回
- **THEN** 后端自动在角色/场景的版本目录写入 `_confirmed` 标记

#### Scenario: 视频页自动匹配
- **WHEN** 用户打开视频生成页（项目模式）
- **THEN** 页面自动扫描 `generated/projects/{name}/characters|scenes/` 下已确认版本
- **AND** 按分镜解析出的角色/场景名自动匹配展示
- **AND** 用户可手动替换为其他版本或其他角色

## MODIFIED Requirements

### Requirement: generate_project_shot（原）

参考图读取路径从 `projects/{name}/07_视觉素材/` 改为 `generated/projects/{name}/characters|scenes/` 下的已确认版本。

### Requirement: handleSceneSelect（原）

改为调用 `fetchScenePrompt` 而非 `generateSelectionPrompt`。

## REMOVED Requirements

无
