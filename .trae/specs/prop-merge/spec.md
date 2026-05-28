# Spec C: 道具融入角色/场景

## Why
当前道具是独立类别，生成了大量无意义的道具图。道具只有三种归宿：
1. 随身道具（配饰）→ 是角色外观的一部分
2. 场景道具（装置）→ 是场景环境的一部分
3. 线索道具（独立）→ 需要独立图，但极少

## 目标
- 生图 UI 中不再有独立的"道具"生图面板
- 随身道具融入角色提示词（`accessories` 字段）— Spec A 已完成
- 场景道具融入场景提示词（`props` 字段）
- 仅线索道具保留在生图清单 `key_props` 中

## What Changes

### 前端：ProjectImageGenForm 去除道具独立面板
- 删除 `{type: 'props'}` 的参考图上传区
- 删除 `📦 道具` CollapsibleSection
- 角色条目中显示配饰标签（已有）
- 场景条目中显示装置标签

### 不影响
- 视觉圣经的 `list_props()` 方法保留（其他阶段可能读）
- `prompt_factory.generate_prop_prompt()` 保留（线索道具用）

## Impact
- Affected code:
  - `src/components/ProjectImageGenForm.tsx` — 删除道具面板
  - `src/components/VideoProjectPanel.tsx` — 同上

## ADDED Requirements

### Requirement: 道具不再独立生成
系统 SHALL 不再提供独立的道具图生成入口。

#### Scenario: 角色生图
- **GIVEN** 角色"林辰"有配饰["指虎", "黑色绷带"]
- **WHEN** 用户生成林辰的定妆照
- **THEN** 提示词中已包含配饰描述，生成的角色形象自然含指虎和绷带
- **AND** 不需要单独生成"指虎"图
