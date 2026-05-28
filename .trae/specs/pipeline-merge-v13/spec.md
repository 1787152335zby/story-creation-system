# 管线合并 Spec A

## Why
当前短剧管线7个阶段：故事大纲 → 完整剧情 → 完整剧本 → 视觉提取 → 分镜设计 → 提示词生成 → 生图需求分析。其中3个阶段存在重叠或浪费：
1. 阶段4「视觉提取」全量提取所有角色/场景，阶段7「生图需求分析」再做精准去重——两者数据来源不同但输出重叠
2. 阶段6「提示词生成」产出 static .md 文件，生图 UI 根本不用（UI 实时调 API 生成），纯浪费 token
3. 阶段7 反向依赖阶段4 的外观数据，但阶段4 又全量跑一遍

## 目标
- 短剧管线从 7 阶段缩减为 5 阶段
- 合并阶段4+6+7 为新的「生图准备」阶段
- 小说/网文模式完全不动

## What Changes

### 新阶段：「生图准备」（image_preparator）
- **外观提取**：从分镜脚本提取出场角色/场景 → 调用 VisualBibleExtractor 仅在必要时提取外观
- **提示词嵌入**：实时生成角色/场景提示词，嵌入生图清单 JSON
- **生图清单**：去重 + 输出 `06_生图需求/生图清单.json`
- **condition**: `"story_type in ['1', '2', '3']"`

### 阶段4「视觉提取」→ 仅小说模式
- condition 改为 `"story_type in ['4']"`

### 删除
- **阶段6「提示词生成」**: 从 workflow.yaml 移除，`prompt_factory.py` 保留为纯工具类（UI API 仍用）
- **阶段7「生图需求分析」**: 功能合并进新阶段，`image_demand_analyzer.py` 保留为工具类

### BREAKING
- 旧项目的 `04_角色场景/` 短剧模式下不再自动生成
- `06_提示词/` 不再产出
- `07_生图需求/` 改为 `06_生图需求/`

## Impact
- Affected specs: pipeline-overhaul, storyboard-driven-gen
- Affected code:
  - `workflow.yaml` — 阶段配置
  - `agents/image_preparator.py` — 新增
  - `agents/image_demand_analyzer.py` — 保留为工具类
  - `agents/prompt_factory.py` — 保留为纯工具类
  - `server/async_orch.py` — AGENT_TO_CONFIG
  - `src/lib/constants.ts` — PHASE_NAMES 调整
  - `src/pages/Workspace.tsx` / `src/components/PhaseTimeline.tsx` / `src/pages/HomePage.tsx` — 阶段名调整

## ADDED Requirements

### Requirement: 生图准备合并阶段
系统 SHALL 在分镜设计完成后自动运行「生图准备」阶段，一站式完成外观提取、提示词生成、去重生图清单。

#### Scenario: 短剧管线运行
- **GIVEN** 项目已完成分镜设计
- **WHEN** 生图准备阶段自动运行
- **THEN** 产出 `06_生图需求/生图清单.json` 和 `06_生图需求/分析报告.md`
- **AND** 清单包含每个角色的出场状态、配饰、已生成提示词模板

## REMOVED Requirements

### Requirement: 视觉提取（短剧模式）
**Reason**: 功能合并进生图准备
**Migration**: 小说模式保持不变

### Requirement: 提示词生成
**Reason**: static 文件无人使用，生图 UI 实时生成替代
**Migration**: 已有 `06_提示词/` 目录不做清理，新项目不再产出
