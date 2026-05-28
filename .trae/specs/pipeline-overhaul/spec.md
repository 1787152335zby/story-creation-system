# 项目创建与管线生成流程重构 Spec

## Why

用户反馈新建项目流程中多个阶段存在结构问题：分镜脚本没有分集生成、输出文件没有按集分子文件夹、视觉提取缺少道具、提示词生成逻辑需要理顺。需要全面梳理管线，确保每个阶段的输入、输出、分集逻辑一致。

## What Changes

- **阶段0（项目创建）**：无变化，已经正确。5步向导 → 00_任务指令 → project_config.json
- **阶段1（故事大纲）**：方向版→大纲两阶段子流程已存在，确认工作正常
- **阶段2（完整剧情）**：拆分为每集子文件夹存储 `02_完整剧情/{第N集}/完整剧情.md`
- **阶段3（完整剧本）**：同上 `03_完整剧本/{第N集}/完整剧本.md`
- **阶段4（视觉提取）**：新增道具提取，输出格式扩展为 角色/场景/道具 三类
- **阶段5（分镜设计）**：修复分集生成，确保按剧本的 `## 第N集` 拆块
- **阶段6（提示词生成）**：输入来自分镜脚本+角色场景，确认流程并补充道具信息
- **项目配置**：`project_config.json` 的 phases 顺序已修复（上一轮），`updated_at` 保存时自动更新已修复

## Impact

- Affected specs: story-to-video-pipeline, episode-generation-flow
- Affected code:
  - `server/async_orch.py` — `_run_chunked_generation` 保存路径改为集子文件夹
  - `agents/plot_expander.py` — 确认分集逻辑正确
  - `agents/screenplay_writer.py` — 确认分集逻辑正确
  - `agents/storyboarder.py` — 确认 `_parse_episode_blocks` 识别多集，生成时强制 `## 第N集` 标题
  - `core/visual_bible.py` — 新增道具提取逻辑
  - `agents/prompt_factory.py` — `build_shot_prompt` 支持道具信息
  - `core/project_manager.py` — `write_output` 无需改，调用方改路径即可

---

## 当前流程确认（6阶段）

```
阶段0 项目创建      用户在首页填写故事类型/风格/时长/故事描述 → 生成 00_任务指令/任务指令.md
阶段1 故事大纲      方向版(A/B) → 用户选择 → 生成完整大纲 → 01_故事大纲/故事大纲.md
阶段2 完整剧情      大纲 → 分集剧情 → 02_完整剧情/完整剧情_第N集.md (split:true)
阶段3 完整剧本      剧情 → 分集剧本 → 03_完整剧本/完整剧本_第N集.md (split:true)
阶段4 视觉提取      剧本 → 角色/场景 JSON → 05_角色场景/角色/*.json + 场景/*.json (split:false)
阶段5 分镜设计      剧本 → 分镜脚本 → 05_分镜脚本/分镜脚本_第N集.md (split:true)
阶段6 提示词生成    分镜+角色场景 → 图像提示词 → 06_提示词/ (split:false)
```

## ADDED Requirements

### Requirement 1：每集子文件夹存储

系统 SHALL 将分集内容存入子文件夹而非平铺文件。每集一个子文件夹，如 `02_完整剧情/第1集/完整剧情.md`。同时保留合并文件在父目录。

#### Scenario：剧情阶段逐集生成
- **WHEN** plot_expander 完成第1集生成
- **THEN** 内容保存到 `02_完整剧情/第1集/完整剧情.md`
- **THEN** 完成后追加到 `02_完整剧情/完整剧情.md`（合并文件）
- **THEN** `chunk_saved` 消息携带 `file_path: "02_完整剧情/第1集/完整剧情.md"`

#### Scenario：单集项目（仅1集）
- **WHEN** plot_expander 检测到只有1集
- **THEN** 内容保存到 `02_完整剧情/第1集/完整剧情.md`（同样分子文件夹）
- **THEN** 合并文件同样写入父目录

### Requirement 2：道具提取

系统 SHALL 在视觉提取阶段（stage 4）从剧本中提取道具/物品信息。

#### Scenario：提取关键道具
- **WHEN** visual_extractor 分析剧本
- **THEN** 除了角色和场景，还提取剧中重要道具
- **THEN** 每个道具包含 name、description、owner（归属角色）、appearance（外观描述）
- **THEN** 保存为 `05_角色场景/道具/{道具名}.json`

#### Scenario：道具 JSON 结构
```json
{
  "name": "战术腕表",
  "type": "手持/佩戴",
  "description": "黑色金属表盘，倒计时数字跳动",
  "owner": "林深",
  "appearance": "黑色方形表盘，暗红数字显示，金属表带略有磨损",
  "category": "科技道具"
}
```

### Requirement 3：分镜分集生成修复

系统 SHALL 确保分镜设计的 chunk 划分与剧本的分集结构对应。

#### Scenario：剧本有 `## 第N集` 标题
- **WHEN** storyboarder 的 `_parse_episode_blocks` 匹配到 N 个集标题
- **THEN** chunk_count = N，每个 chunk 对应一个集
- **THEN** 每个 chunk 输出的分镜文件以 `## 第N集` 开头
- **THEN** 前端分镜树正确显示 集→场→镜头 三层结构

#### Scenario：剧本没有集标题（单集）
- **WHEN** 剧本仅 1 集且无 `## 第N集` 标记
- **THEN** 系统默认按1个 chunk 处理
- **THEN** 输出文件命名为 `分镜脚本_第1集.md`

### Requirement 4：提示词生成管道明确化

系统 SHALL 在输出面板显示提示词生成的完整数据流：分镜脚本（文本描述）+ 角色场景（视觉属性）→ image generation prompt。

#### Scenario：提示词文件结构
- **WHEN** prompt_factory 完成
- **THEN** 输出目录 `06_提示词/` 包含：
  - `角色提示词.md` — 每个角色的定妆照提示词（含道具）
  - `场景提示词.md` — 每个场景的概念图提示词
  - `提示词_第N集.md` — 每集所有镜头的图像生成提示词
  - `提示词.md` — 全部分镜提示词汇总

## MODIFIED Requirements

### Requirement：_run_chunked_generation 输出路径

原：文件保存到父目录 `{output_dir}/{base}_{ep}.md`
改为：文件保存到子目录 `{output_dir}/{ep}/{base}.md`

### Requirement：project_config phases 顺序

已在上轮修复（`visual_extract` 和 `storyboard` 顺序与 workflow.yaml 对齐）。新项目创建时自动使用正确顺序，旧项目加载时自动迁移。

### Requirement：_get_input 输入链

确认数据流：
- 大纲 → 剧情：`01_故事大纲/故事大纲.md`
- 剧情 → 剧本：`02_完整剧情/完整剧情.md`（合并文件）
- 剧本 → 分镜：`03_完整剧本/完整剧本.md`
- 剧本 → 视觉提取：`03_完整剧本/完整剧本.md`
- 分镜 → 提示词：`05_分镜脚本/` 所有分集文件
