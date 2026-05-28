# 生图模块对标市面产品的缺口分析 Spec

## Why

当前生图模块支持了基本流程，但相比 Midjourney、DALL·E 3、Stable Diffusion WebUI 等产品，在核心交互、功能完备性和代码质量上存在明显差距。细分三类问题：**Bug（功能不正常）**、**缺失（功能没有）**、**优化（功能有但体验差）**。

---

## What Changes

### P0 — Bug 修复（用户能用但会出错）

| # | 问题 | 表现 | 修复方式 |
|---|------|------|----------|
| B1 | 版本号竞态条件 | 两人同时为同一角色生成，版本 `_next_version` 返回相同值，后一个覆盖前一个的文件 | `project_image_gen` 中加 `threading.Lock()` |
| B2 | `key={i}` 导致 DOM 复用错乱 | 新结果插到列表前面时，React 复用旧 DOM 节点，hover 残留、图片错位 | 所有生成结果/history 用文件名或 URL 作为 key |
| B3 | `handleRemix` 漏了 `freeCount` | 画同款时 prompt/model/size 都恢复了，但生成数量回到 1 | 补上 `if (entry.count) setFreeCount(entry.count)`，元数据加 `count` 字段 |
| B4 | 场景列表按 name 去重，变体场景全部丢失 | `seenScenes` 只保留首个 name 的场景，所有变体场景在项目模式不可见 | 改用场景的 `_file` 或 `scene_base` 分组显示 |

### P0 — 功能缺失（市面产品标配但这里没有）

| # | 功能 | 对比对象 | 实现方式 |
|---|------|----------|----------|
| F1 | **图片预览无缩放/拖拽** | 所有平台都支持 | `ImagePreview.tsx` 加滚轮缩放、拖拽平移、点击关闭 |
| F2 | **生成进度展示** | MJ 的 `Starting... → Rendering...`、WebUI 的进度条 | 后端流式返回进度事件或前端计时器+轮询 |
| F3 | **没有独立的历史页面** | Leonardo.ai | 独立 `HistoryPage.tsx` + 后端 `/api/history` 分页 |

### P1 — 体验缺失

| # | 功能 | 说明 | 实现方式 |
|---|------|------|----------|
| F4 | **种子（seed）控制** | 前端没有 seed 输入框，`extra_params` 只能用代码设置 | 自由模式表单加 Seed 输入框（默认值留空=随机） |
| F5 | **图片放大（Upscale）** | 没有独立放大功能 | 后端加 `/api/image-gen/upscale` 端点（调用 Seedream 的放大能力） |
| F6 | **风格预设** | 没有可保存/复用的风格模板 | 后端加 `presets.json` 存储+前端预设选择器 |

### P1 — 代码优化

| # | 问题 | 现状 | 修复方式 |
|---|------|------|----------|
| O1 | **死代码：两套调用路径** | `gen.py._call_image_api` 和 `image_api.py.create_image_backend` 互不关联，后者从未被调用 | 统一到一条路径，删除image_api_seedream.py/image_api_openai_compat.py中未被引用的类（或标记为废弃） |
| O2 | **Gemini 参考图重复编码** | 每次循环 `for i in range(n)` 都重新编码参考图 | 移到循环外部 |
| O3 | **any 类型泛滥** | characters/scenes/大部分回调用 `any` | 定义 `CharacterInfo`、`SceneInfo` 接口 |
| O4 | **共享状态冲突** | resolutions/ratioGroups/selectedRatio 在 free/project 模式混用 | 拆分独立状态 |


## Impact

- Affected specs: 图像生成、ImagePreview
- Affected code:
  - `server/routes/gen.py` — 加锁、元数据加 count、删死代码路径
  - `src/components/ImagePreview.tsx` — 重写（加缩放/拖拽）
  - `src/components/FreeImageGenForm.tsx` — 加 Seed 输入
  - `src/components/ProjectImageGenForm.tsx` — 场景变体修复
  - `src/pages/ImageGenPage.tsx` — 修复 handleRemix + 场景去重 + 状态拆分
  - `src/lib/types.ts` — 加 CharacterInfo/SceneInfo 接口

## ADDED Requirements

### Requirement: 版本号并发安全

The system SHALL prevent race conditions when assigning version numbers.

#### Scenario: 并发角色生成
- **WHEN** 两个请求同时为同一个角色生成图片
- **THEN** 使用 `threading.Lock()` 保护 `_next_version` 的读/写
- **AND** 两个请求分别获得不同的版本号

### Requirement: 图片预览缩放

The system SHALL support zoom and pan in image preview.

#### Scenario: 滚轮缩放
- **WHEN** 用户在预览弹窗中滚动滚轮
- **THEN** 图片按比例缩放（0.5x ~ 5x）

#### Scenario: 拖拽平移
- **WHEN** 图片被放大后超出可视区域
- **THEN** 用户可以拖拽平移查看

### Requirement: 生成进度展示

The system SHALL show generation progress to the user.

#### Scenario: 进度更新
- **WHEN** 生成请求发出后
- **THEN** 按钮变为 "生成中... (step X/Y)" 或显示进度条
- **AND** 后端 `_call_image_api` 每完成一步返回进度事件

### Requirement: 场景变体可见

The system SHALL display scene variants in project mode.

#### Scenario: 场景树形结构
- **WHEN** 项目加载场景列表
- **THEN** 按 `is_base` 分组，基础场景为一级，变体为子节点
- **AND** 不再用 `name` 去重（改用树形结构展示）

## MODIFIED Requirements

### Requirement: ImagePreview（原）

完整重写预览组件，增加缩放/拖拽/加载态/错误处理。

### Requirement: handleRemix（原有）

增加 `freeCount` 恢复逻辑。

## REMOVED Requirements

无
