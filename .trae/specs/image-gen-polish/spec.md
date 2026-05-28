# 生图体验增强 Spec

## Why

生图模块核心功能已完整，但三个体验缺口：

1. **项目模式没有风格预设** —— 角色/场景生成时无法像自由模式一样选择电影感/动漫风等预设来增强 prompt
2. **模型特色参数对用户不可见** —— 后端已支持 cfg_scale/seed/style/quality，前端只有 Seed 输入框
3. **生成过程无法取消** —— 发出去只能等完，写错 prompt 选错模型只能干等

## What Changes

### 1. 项目模式加风格预设
- `ProjectImageGenForm` 增加预设选择器，选中后 prompt_suffix 追加到 `projectPrompt`
- style_params 合并到 extra_params，通过 `ProjectImageRequest.extra_params` 传给后端

### 2. 高级参数面板
- 自由模式和项目模式各加一个折叠的「▸ 高级参数」面板
- 包含：Seed（已有，移入面板）、cfg_scale（1-20 滑块/输入）、style（vivid/natural 下拉）、quality（standard/hd 下拉）
- 每个参数标注仅对哪些模型生效（如 `仅 Seedream`、`仅 DALL-E 3`）
- 通过 `extra_params` 传递给后端

### 3. 取消生成
- 前端生成按钮加「取消」状态：开始生成后按钮变为 `[ × 取消 ]`
- 后端 `free_image_gen` 和 `project_image_gen` 增加取消检查点（每张图生成前检查）
- 用 `asyncio.Event` 或全局 `dict` 维护任务取消状态
- 前端在取消时 POST `/api/image-gen/cancel/{task_id}`

## Impact

- Affected specs: 图像生成、自由模式、项目模式
- Affected code:
  - `src/components/FreeImageGenForm.tsx` — 高级参数面板 + 取消按钮
  - `src/components/ProjectImageGenForm.tsx` — 预设选择器 + 高级参数面板 + 取消按钮
  - `src/pages/ImageGenPage.tsx` — 取消状态 + 项目模式预设逻辑
  - `server/routes/gen.py` — 取消端点 + 取消检查

## ADDED Requirements

### Requirement: 项目模式风格预设

ProjectImageGenForm 增加风格预设选择器（与自由模式相同的 presets）。选择后 prompt 追加 `prompt_suffix`，style_params 合并到 `extra_params`。

### Requirement: 高级参数面板

自由模式和项目模式表单各包含一个折叠展开的「▸ 高级参数」区域，包含 cfg_scale、style、quality 三个参数，以及已有的 Seed 输入框移入此面板。

### Requirement: 取消生成

用户点击取消时，后端停止正在进行的图片生成请求，已生成的图片保留。

## MODIFIED Requirements

无

## REMOVED Requirements

无
