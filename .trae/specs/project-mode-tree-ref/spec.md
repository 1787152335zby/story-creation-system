# 项目模式：角色/场景变体树形选择 + 参考图增强 Spec

## Why

项目模式的角色/场景列表是扁平的一条，基础角色和它的变体（如"林溪"与"林溪_变身"、"林溪_觉醒"）混在一起显示。用户无法直观地看到哪个是基础、哪个是变体；选中不同变体时提示词和参考图也不能自动切换。

## What Changes

### 1. 角色列表改为树形结构（基础 + 变体下拉）
- 基础角色（`is_base: true`）作为一级条目显示
- 点击基础角色展开其变体列表（从数据的 `variants` 字段或按 `character_base` 分组）
- 点击基础角色 → 自动选择基础角色的提示词 + 基础角色的确认图为参考图
- 点击变体 → 自动选择变体的提示词 + 变体的确认图为参考图
- 角色和变体只能单选（而不是多选），点谁谁进提示词框

### 2. 场景列表同理
- 基础场景作为一级条目，展开变体
- 点击基础场景 → 该场景提示词 + 确认参考图
- 点击变体场景 → 变体提示词 + 变体确认参考图

### 3. 项目模式增加参考图上传
- 同自由模式，项目模式表单增加参考图上传区域（拖拽/选择/URL）
- 自动加载的确认参考图 + 手动上传的参考图一起发送到生成请求

### 4. 迁移选择逻辑：从多选改为单选
- 角色/场景从 checkbox 多选改为点击单选
- 每次只能选择一个角色或一个场景（或一个都不选）
- 选择自动触发提示词加载 + 参考图加载
- 项目模式保留"多角色+多场景"的批量生成能力（通过版本系统），但默认交互改为逐个选择

## Impact

- Affected specs: 图像生成（项目模式）
- Affected code:
  - `src/components/ProjectImageGenForm.tsx` — 树形选择 + 参考图 UI + 单选逻辑
  - `src/pages/ImageGenPage.tsx` — 状态适配
  - `src/lib/api.ts` — 可能新增 API
  - `src/lib/types.ts` — 类型调整

## ADDED Requirements

### Requirement: 角色树形选择

The system SHALL display base characters and their variants in a tree structure.

#### Scenario: 基础角色可展开
- **WHEN** 项目模式加载角色列表
- **THEN** 只显示基础角色（`is_base: true`）作为一级条目
- **AND** 每个基础角色旁显示展开按钮
- **AND** 展开后列出子变体（`is_base: false` 且 `character_base === 当前角色名`）

#### Scenario: 点击基础角色加载提示词
- **WHEN** 用户点击基础角色名称
- **THEN** 调用 `POST /api/projects/{name}/generate-prompt` 传入该角色 name
- **AND** 提示词填入项目模式提示词框
- **AND** 如果该角色有已确认图片，自动加载为参考图
- **AND** 角色条目高亮显示为选中状态

#### Scenario: 点击变体加载变体提示词
- **WHEN** 用户点击变体名称
- **THEN** 调用 `POST /api/projects/{name}/generate-prompt` 传入变体的 name
- **AND** 提示词框中显示变体特有的提示词（含外貌变化/服装变化描述）
- **AND** 如果该变体有已确认图片，加载为参考图
- **AND** 变体条目高亮显示为选中状态

### Requirement: 场景树形选择

The system SHALL display base scenes and their variants in a tree structure.

#### Scenario: 场景可展开
- **WHEN** 项目模式加载场景列表
- **THEN** 只显示基础场景作为一级条目
- **AND** 展开后列出变体场景

#### Scenario: 点击场景加载
- **WHEN** 用户点击基础场景或变体
- **THEN** 调用提示词 API 获取该场景/变体的提示词
- **AND** 填入提示词框 + 自动加载参考图

### Requirement: 项目模式参考图上传

The system SHALL allow reference image upload in project mode.

#### Scenario: 上传/URL 参考图
- **WHEN** 用户在项目模式拖拽/选择/粘贴 URL
- **THEN** 参考图上传到服务器，显示缩略图预览
- **AND** 生成请求中携带 reference_urls（自动加载的确认图 + 手动上传的图）

### Requirement: 单选切换逻辑

The system SHALL switch character/scene selection on click (not checkbox).

#### Scenario: 切换角色
- **WHEN** 用户点击另一个角色
- **THEN** 前一个角色取消选中
- **AND** 新角色的提示词和参考图替换
- **AND** 提示词框内容刷新

#### Scenario: 取消选择
- **WHEN** 用户再次点击已选中的角色
- **THEN** 取消选中，提示词框清空，参考图清空

## MODIFIED Requirements

### Requirement: 项目模式历史（原）

前端确认：自由模式历史和项目模式历史**已经分离**（后端按 `free_` / `proj_` 文件名前缀分类），无需改动。

## REMOVED Requirements

### Requirement: 角色批量多选

**Reason**: 改为单选后交互更清晰，用户逐个选择角色并查看其提示词和参考图。批量生成需求通过系统的"多角色版本"机制满足。
**Migration**: 如果用户需要生成多个角色，可以依次为每个角色生成，系统自动分配版本。
