# E2E 全流程用户体验测试 Spec

## Why
系统已开发多个阶段（大纲→剧情→剧本→视觉→分镜→提示词→图像→视频），但从未作为真实用户从头到尾完整跑通过。需要模拟真实用户操作，暴露每个阶段的体验问题、bug 和功能缺失。

## What Changes
1. 完整跑通 6 工作流阶段 + 图生阶段 + 视频生成阶段
2. 记录每个阶段的 UX 问题、bug、功能缺失
3. 输出可操作的修复项清单

## Impact
- **Affected specs**: 全部现有工作流阶段
- **Affected code**: agents/*, server/*, src/pages/*
- **测试范围**: NewProjectWizard → Workspace(6 phases) → ImageGenPage → VideoGenPage

## Testing Approach

### 创建项目（用户视角）
- 首页展示项目列表、模板、快速入口
- 引导创建项目（5 个步骤）
- 选择故事类型 → 风格偏好 → 时长 → 故事描述 → 模型选择
- 关键检查点：字段校验、随机生成、模板应用、API Key 检查

### 工作区创作（用户视角）
- 阶段0 故事大纲：用户期望看到大纲，选择版本（A/B），反馈修改
- 阶段1 完整剧情：自动按集/章展开
- 阶段2 完整剧本：按选择格式（系统/市场）输出，分集查看
- 阶段3 视觉提取：自动提取角色/场景特征
- 阶段4 分镜脚本：按集逐镜生成，完整的分集审核流程
- 阶段5 提示词生成：自动生成角色/场景/分镜提示词

### 生图与视频（用户视角）
- ImageGenPage：自由模式 + 项目模式，角色定妆照、场景概念图
- VideoGenPage：自由模式 + 项目模式，图生视频、提示词生视频

---

## ADDED Requirements

### Requirement: Project Wizard UX
The multi-step project creation wizard SHALL validate all required inputs before allowing submission.

#### Scenario: Create project without API Key
- **WHEN** user clicks "开始创作"
- **THEN** system redirects to settings page with error toast

#### Scenario: Create project without story idea
- **WHEN** user clicks 下一步 on step 3 without story idea
- **THEN** system shows error toast and prevents proceeding

#### Scenario: Random idea generation
- **WHEN** user clicks 随机生成
- **THEN** system generates a story idea based on selected style

### Requirement: Streaming Generation Flow
Each phase SHALL properly stream content, complete, and transition to the next phase.

#### Scenario: Normal streaming completion
- **WHEN** phase completes streaming
- **THEN** user sees complete content and approval UI

#### Scenario: Phase redo
- **WHEN** user clicks 重新生成 on completed phase
- **THEN** system regenerates that phase's content

### Requirement: Episode Chunking (Phase 1, 2, 4)
Multi-episode phases SHALL generate content per episode/chunk and save individual files.

#### Scenario: Episode generation flow
- **WHEN** generating phase with split=true
- **THEN** system generates each episode sequentially with approval between each
- **AND** creates individual episode files in the output directory
- **AND** merges into a complete file at the end

### Requirement: Script Format Selection
The screenplay phase SHALL output in the format selected during project creation.

#### Scenario: Market format
- **WHEN** script_format=2 (市场格式)
- **THEN** output uses ▶ symbols and 1-1 scene numbering

#### Scenario: System format
- **WHEN** script_format=1 (系统格式)
- **THEN** output uses ## 第X场 and standard formatting

### Requirement: Storyboard Episode-by-Episode
The storyboard phase SHALL split by episode and generate each episode's storyboard separately.

#### Scenario: Storyboard with 5 episodes
- **WHEN** storyboarder runs with story_type='1'
- **THEN** output is split into 5 files (one per episode)
- **AND** user approves each episode before next is generated

### Requirement: Image Generation
The system SHALL generate character and scene images for a project.

#### Scenario: Generate character images
- **WHEN** user selects characters and clicks generate
- **THEN** system generates character images from visual bible data

#### Scenario: Generate scene images
- **WHEN** user selects scenes and clicks generate
- **THEN** system generates scene concept images from visual bible data

### Requirement: Video Generation (Pipeline)
The video generation phase SHALL work correctly as part of the pipeline.

#### Scenario: Video generation from project
- **WHEN** user clicks 开始生成 in project mode
- **THEN** system generates video clips for each scene
- **AND** optionally produces a final merged video

---

## MODIFIED Requirements

### Requirement: ImageGen/VideoGen page routing (FIX NEEDED)
The VideoGenPage SHALL use correct phase_index.

**Change**: WAS: VideoGenPage line 142 sends `phase_index: 7` but valid range is 0-5. **FIXED**: now shows informative message telling user to use 自由模式.

### Requirement: Video clip storage (FIX NEEDED)
The video-clips endpoint expects `08_视频/片段/` but no phase creates this directory.

**Change**: Either add a video_producer phase to workflow.yaml, or fix the endpoint to check `07_视频/` or the actual output directory used.

### Requirement: Image generation integration (FIX NEEDED)
ImageArtist agent exists but is not in workflow.yaml.

**Change**: Add image_artist phase to workflow.yaml so project-level image gen is automated.

---

## REMOVED Requirements
None.

## Known Issues (Pre-existing)
1. workspace.tsx 中的 PHASE_DIRS/PHASE_NAMES 只定义了 6 个阶段，视频生成阶段未纳入主管线
2. ImageGenPage 和 VideoGenPage 独立于工作区管线，需要用户手动导航
3. workflow.yaml 配置了 `story_type in ['1', '2', '3']` 条件，但其他类型（小说/广播剧等）条件外的阶段完全跳过
4. 部分 agents (image_artist, video_producer) 存在但未在 workflow.yaml 注册
