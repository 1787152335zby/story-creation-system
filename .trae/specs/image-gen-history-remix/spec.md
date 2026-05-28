# 智能生图：画同款 + 参考图增强 Spec

## Why

生图系统缺少两个必要的功能闭环：用户无法"复用"之前的生成成果（画同款），自由模式下完全没有参考图上传能力，导致创意延续困难。

## What Changes

### 1. 画同款（历史记录复用）
- 自由模式和项目模式的历史记录存储完整生成参数（prompt、negative_prompt、model、size、reference_urls）
- 历史卡片上增加"画同款"按钮，点击后自动回填所有参数到生成表单
- 回填包括参考图片，自动下载/加载到参考图展示区

### 2. 自由模式参考图片
- 自由模式表单增加参考图上传区域（拖拽上传 / 点击选择 / URL 输入）
- 支持多张参考图，可预览、可删除
- 参考图会随生成请求一起发送到后端

### 3. 历史记录展示增强
- 历史卡片显示 prompt 摘要、模型名称、尺寸、生成时间
- 鼠标悬停可查看完整 prompt
- 区分自由模式和项目模式的历史

## Impact

- Affected specs: 图像生成
- Affected code:
  - `src/pages/ImageGenPage.tsx` — 历史展示 + 画同款
  - `src/components/FreeImageGenForm.tsx` — 参考图输入
  - `src/components/ProjectImageGenForm.tsx` — 画同款
  - `server/routes/gen.py` — 保存/返回元数据
  - `src/lib/api.ts` — 新增历史详情 API
  - `src/lib/types.ts` — 新增历史记录类型

## ADDED Requirements

### Requirement: 生成参数持久化

The system SHALL save generation parameters alongside each generated image.

#### Scenario: 自由模式生图保存
- **WHEN** 用户点击自由模式下的"生成"按钮
- **THEN** 后端保存图片文件到 `generated/` 目录
- **AND** 后端同时写入 `generated/_meta/{filename}.json`，包含 `prompt`，`negative_prompt`，`model`，`size`，`reference_urls`，`timestamp`，`mode: "free"`

#### Scenario: 项目模式生图保存
- **WHEN** 用户在项目模式下生成图片
- **THEN** 后端保存图片到 `generated/` 目录
- **AND** 同时写入元数据 JSON，额外包含 `project_name`，`character_names`，`scene_names`，`version`，`mode: "project"`

### Requirement: 历史记录 API 增强

The system SHALL provide generation parameters when querying history.

#### Scenario: /generated-history 返回元数据
- **WHEN** 前端调用 `GET /api/generated-history`
- **THEN** 返回每个文件对应的元数据（如有），包含 `prompt`，`model`，`size`，`reference_urls`，`timestamp`，`mode`

#### Scenario: /generated-history/{filename} 获取单条详情
- **WHEN** 前端调用 `GET /api/generated-history/{filename}`
- **THEN** 返回该文件的完整元数据，包含所有生成参数

### Requirement: 画同款（历史→表单回填）

The system SHALL allow users to reload a historical generation's parameters.

#### Scenario: 自由模式画同款
- **WHEN** 用户点击自由模式历史卡片上的「画同款」按钮
- **THEN** 前端请求该历史记录的元数据
- **AND** 自动填充 prompt、negative_prompt、model、size、reference_urls 到自由模式表单
- **AND** 参考图片自动加载显示在参考图预览区

#### Scenario: 项目模式画同款
- **WHEN** 用户点击项目模式历史卡片上的「画同款」按钮
- **THEN** 前端切换到自由模式
- **AND** 填充所有参数，包括项目名称信息

### Requirement: 自由模式参考图上传

The system SHALL allow users to upload/input reference images in free mode.

#### Scenario: 拖拽/选择参考图
- **WHEN** 用户在自由模式拖拽图片到参考图区域，或点击选择文件
- **THEN** 图片上传到服务器，返回可访问 URL
- **AND** 显示缩略图预览，可点击删除

#### Scenario: URL 输入参考图
- **WHEN** 用户粘贴图片 URL 到参考图输入框
- **THEN** URL 添加到参考图列表
- **AND** 显示缩略图预览

#### Scenario: 参考图参与生成
- **WHEN** 用户点击生成
- **THEN** reference_urls 包含所有已添加的参考图 URL
- **AND** 发送到后端参与生成

### Requirement: 参考图上传 API

The system SHALL provide an image upload endpoint for reference images.

#### Scenario: POST /api/upload-reference
- **WHEN** 前端上传图片文件或 base64
- **THEN** 后端保存到 `generated/_refs/{uuid}.{ext}`
- **AND** 返回 `{"url": "/api/gen-files/_refs/{uuid}.{ext}"}`

## MODIFIED Requirements

### Requirement: 历史展示（原 `/generated-history`）

前端历史区域改为卡片式布局，每张卡片显示：
- 缩略图
- Prompt 摘要（前 40 字）
- 模型名称
- 尺寸（如 `1024x1024`）
- 生成时间（相对时间，如"3 分钟前"）
- 参考图数量标记（如 `📎 2`）
- 操作按钮：**画同款**、下载、删除

## REMOVED Requirements

无
