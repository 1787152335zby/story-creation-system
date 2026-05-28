# Spec B: 生图清单驱动 UI

## Why
Spec A 合并了管线，生图清单 JSON 包含了每个条目的 `prompt` 字段。但生图 UI 的"一键生成"按钮仍然用旧的 `charTree`/`sceneTree`，没有对接清单。需求清单做了分析，但没人用它来驱动生成。

## 目标
- "一键生成所有角色定妆照" → 用生图清单的 `characters` 数组
- "一键生成所有场景概念图" → 用生图清单的 `scenes` 数组
- 清单条目可单独点击 → 自动填提示词 + 一键生成
- 已生成的图片出现在对应条目下

## What Changes

### 前端：ProjectImageGenForm 改为清单驱动
- 保留"📋 生图需求清单"面板，增强交互
- 每个角色条目右侧新增"⚡生成"按钮，点击自动用条目内置的 `prompt` + 关联场景参考图 → 生成
- "一键生成所有角色/场景"按钮改为遍历清单数组
- 旧的 charTree/sceneTree 选择面板退役（但保留 collapse 展示角色外观信息）
- 生成完成后图片出现在清单条目下方（而非独立的历史区）

### 后端：新增按清单条目生成 API
- 新增 `/gen/project-image-by-demand` 接受 `{project_name, type: "character"|"scene", index: number}`
- 从生图清单 JSON 读取 prompt 和历史参考图 → 调用 image_artist

## Impact
- Affected code:
  - `src/components/ProjectImageGenForm.tsx` — 主要改动
  - `server/routes/gen.py` — 新增 API

## ADDED Requirements

### Requirement: 清单驱动生成
系统 SHALL 支持从生图清单条目直接生成图片。

#### Scenario: 点击角色条目生成
- **GIVEN** 生图清单中有角色"林辰"
- **WHEN** 用户点击该条目旁的"⚡生成"
- **THEN** 系统自动使用条目内置 prompt + 关联场景参考图生成角色定妆照
- **AND** 生成结果出现在该条目下方
