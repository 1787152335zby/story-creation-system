# 生图/生视频全模型功能优化 Spec

## Why

当前系统支持 9 个图像模型和 6 个视频模型，但所有模型都只走了最基本的 `text_to_image`，每个模型的特色参数（cfg_scale、style、quality、seed、真实参考图等）全部被忽略。视频模型的 model 选型被硬编码。结果是用户选什么模型都得到差不多的质量，模型间的差异没有体现出来。

## What Changes

### 图像生成

#### 1. `_call_image_api` 支持模型特色参数
- 新增 `FreeImageRequest.extra_params: dict` 和 `ProjectImageRequest.extra_params: dict`，承载模型特定参数
- 新增 `ModelParams` 统一数据结构（cfg_scale、seed、style、quality），前端可不传，后端用默认值
- 将 `_call_image_api` 扩展为根据模型类型自动选择调用方式：
  - **Seedream** 模型 → 走 raw HTTP POST（因为需要传 `cfg_scale`、`seed` 非标准 OpenAI 参数）
  - **DALL-E 3** → 走 OpenAI SDK，额外传 `style`、`quality`
  - **GPT-Image-1** → 走 OpenAI SDK，额外支持参考图（`file_ids`）
  - **Gemini** → 保持当前 chat/completions 路径
  - **其他 OpenAI 兼容** → 走 OpenAI SDK，传 `negative_prompt`（兼容接口支持）

#### 2. 真实参考图（img2img）
- Gemini 路径：已实现，保持
- GPT-Image-1 路径：新增文件上传到 OpenAI，获取 `file_id`，作为 `file_ids` 参数传入 `images.generate()`
- Seedream 路径：Seedream API 不支持参考图，提示用户

#### 3. `negative_prompt` 在非 Gemini 路径中实际传递
- 当前 `negative_prompt` 被请求模型接收但从未传给 OpenAI client
- 改为：如果后端支持，在 payload 中加入 `negative_prompt`

### 视频生成

#### 4. Seedance 动态模型选择
- `_call_seedance_text_to_video` 和 `_call_seedance_image_to_video` 增加 `model` 参数
- 移除硬编码 `"doubao-seedance-2-0-260128"`
- `SeedanceBackend.text_to_video` 和 `image_to_video` 增加 `model` 参数
- `free_video_gen` 和 `generate_project_shot` 路由传入用户选择的 model

#### 5. Seedance 增加 negative_prompt
- 两个视频生成函数增加 `negative_prompt` 参数
- 如果 API 端点支持，在 payload 中加入

### 工具类引用

#### 6. 打通后端类调用链路
- 确认 `SeedreamBackend`、`GPTImageBackend` 等类当前在 `_call_image_api` 中完全未被使用
- 方案一（推荐）：**扩展 `_call_image_api` 逻辑而非重构整个调用链**，因为改架构风险太大
- 在每个模型分支中，引用对应 backend 类的方法作为参数格式化参考，但保持实际调用走 `_call_image_api`

## Impact

- Affected specs: 图像生成、视频生成
- Affected code:
  - `server/routes/gen.py` — `_call_image_api` 大幅改造、`_call_seedance_*` 加参数、请求模型加 `extra_params`
  - `tools/video_api_seedance.py` — `text_to_video` 和 `image_to_video` 加 `model` 和 `negative_prompt` 参数
  - `tools/video_api.py` — `VideoBackend` 基类 `text_to_video`/`image_to_video` 加 `model` 参数
  - `tools/image_api_seedream.py` / `tools/image_api_openai_compat.py` — 参数签名对照（不改动，仅确认）
  - 前端无改动（所有新参数从后端默认填充）

## ADDED Requirements

### Requirement: 模型参数传递

The system SHALL support model-specific generation parameters.

#### Scenario: Seedream 使用 cfg_scale
- **WHEN** 模型为 Seedream 系列
- **THEN** `_call_image_api` 使用 raw POST 到 Seedream API
- **AND** payload 中包含 `cfg_scale`（默认 7.0）
- **AND** payload 中包含 `seed`（可选，默认不传）

#### Scenario: DALL-E 3 使用 style + quality
- **WHEN** 模型为 DALL-E 3
- **THEN** `_call_image_api` 调用 OpenAI SDK 时传入 `style`（默认 "vivid"）和 `quality`（默认 "standard"）

#### Scenario: GPT-Image-1 真实参考图
- **WHEN** 模型为 GPT-Image-1 且 `reference_urls` 不为空
- **THEN** 先将参考图上传到 OpenAI 获取 file_ids
- **AND** `client.images.generate()` 中传入 `file_ids` 参数
- **AND** prompt 中不再拼接"保持参考图风格"文字

#### Scenario: 非 Gemini 模型传递 negative_prompt
- **WHEN** 模型非 Gemini 且 `negative_prompt` 不为空
- **THEN** 在 API payload 中加入 `negative_prompt`（兼容接口支持）

### Requirement: Seedance 动态模型选择

The system SHALL allow dynamic model selection for Seedance video generation.

#### Scenario: 自由模式视频生成
- **WHEN** 用户选择 Seedance 2.0 Pro 并生成视频
- **THEN** `free_video_gen` 将用户选择的 model 传入 `_call_seedance_text_to_video`
- **AND** payload 中使用传入的 model，而非硬编码值

#### Scenario: 项目模式镜头生成
- **WHEN** 用户生成项目镜头
- **THEN** `generate_project_shot` 传入 model
- **AND** `SeedanceBackend.text_to_video` 使用传入的 model

### Requirement: Seedance negative_prompt

The system SHALL support negative prompt for video generation.

#### Scenario: 视频带负面提示词
- **WHEN** 用户生成视频时填写了负面提示词
- **THEN** 在 payload 中加入 `negative_prompt` 字段

## MODIFIED Requirements

无

## REMOVED Requirements

无
