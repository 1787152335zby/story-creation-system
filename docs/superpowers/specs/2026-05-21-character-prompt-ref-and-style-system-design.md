# 角色提示词分层 & 风格系统 & 参考图标签化 — 设计文档

**日期：** 2026-05-21  
**状态：** 待审核  
**关联项目：** story-creation-system1.2

---

## 背景与动机

当前系统的生图功能存在三个架构性问题，导致生成的角色/场景图难以直接用于视频生成管线：

1. **角色提示词混杂**：外貌、服装、动作、配饰全部混在同一段 prompt 里。定妆照带了动作（如"靠在机舱壁上"），视频模式拿来做参考时人物姿态被锁死。配饰无法独立管理——下一场戏匕首没了或书包摘了，无法只换配饰不换人物。

2. **风格决策缺失**：用户选择 `art_style=7（自动适配）` 时，系统只把"自动适配"当作文本标签传递给模型，从未做出具体决策。用户通过 `custom_requirements` 写"参考冰雪奇缘的风格"也只当文本传给 LLM，没有利用视觉模型分析参考图。

3. **参考图无分类**：所有参考图存在一个扁平数组里，无法告诉模型"这张图是用来决定画风的，那张是用来决定角色外貌的"。导致图生图效果不稳定。

---

## 目标

1. **角色提示词分层**：每个角色生成 L1 基础形象（定妆照）和 L2 道具资产（独立物品图），互不污染。
2. **风格系统智能化**：自动适配模式根据故事属性规则匹配具体画风；自定义模式支持上传风格参考图并用多模态模型分析。
3. **参考图标签化**：参考图 UI 改为四标签页（画风/人物/场景/道具），每类参考图有独立的处理流程。

---

## 一、角色提示词分层（L1 + L2）

### 1.1 数据模型

**现有 `CharacterInfo` 字段利用（不变更 JSON 结构）：**

| 字段 | L1 基础形象 | L2 道具 |
|---|---|---|
| `appearance` | ✅ 使用 | — |
| `clothing` | ✅ 使用 | — |
| `age` | ✅ 使用 | — |
| `gender` | ✅ 使用 | — |
| `expression` | ❌ 忽略（带语境） | — |
| `pose` | ❌ 忽略（动作不应入定妆照） | — |
| `accessories` | ❌ 忽略 | ✅ 逐项生成 |
| `key_features` | ✅ 使用（外貌特征） | — |

### 1.2 L1 基础形象提示词

**生成逻辑位置：** `agents/prompt_factory.py` → `PromptBuilder.generate_character_prompt`

**改动：** 新增模式参数 `mode: "base" | "prop" | "all"`，默认 `"all"` 保持向后兼容。

**L1 输出格式：**
```
'林深' 的定妆照，主要角色。
外貌特征：成年男性，额角有旧伤疤，面色冷峻。
服装：极地防寒服。
标志性特征：领袖气质、冷静果断、额角旧伤疤。
纯白背景，角色居中，全身照，自然站立姿态，无动作，无手持物品。
```

**L2 输出格式（每个配饰一条）：**
```
'高频振动匕首' — 林深的配饰道具。
战术匕首，钨钢刀刃，握柄有防滑纹路。
白色背景，产品展示角度，高清细节。
```

### 1.3 道具资产管理

**后端：**
- 新增 `POST /api/projects/{name}/prop-prompt` — 仿照 `character-prompt` 端点，接收 `character_name` + `prop_name`，返回道具提示词。
- 道具生图调用现有的 `projectImageGen`（复用，提示词不同）。

**前端改动：**
- [ProjectImageGenForm.tsx] 左侧面板新增"🔧 道具"区块（跟在场景区块后面），列出当前项目中所有角色的 `accessories`，格式 `角色名 / 道具名`。
- 点击道具 → 自动填充道具提示词 + 加载已有版本预览。
- 道具选中时场景/角色选择互斥（与现有逻辑一致）。

### 1.4 L2 道具命名约定

```
{角色名}_道具_{道具名}_{version}.png
例：林深_道具_匕首_v1.png
```

存储路径：`generated/projects/{project}/props/{角色名}/{道具名}/`

---

## 二、风格系统（自动适配 + 自定义）

### 2.1 自动适配规则

**位置：** `core/style_config.py` → `StyleConfig.resolve_art_style()`

当 `art_style == "7"`（自动适配）时，根据故事属性自动选择：

```python
AUTO_ART_STYLE_RULES = {
    ("科幻",): "3",
    ("奇幻",): "3",
    ("悬疑",): "1",
    ("剧情",): "1",
    ("动作",): "1",
    ("日韩生活",): "2",
    ("治愈",): "2",
    ("日常",): "2",
    ("古装",): "5",
    ("仙侠",): "5",
    ("国风",): "5",
    ("爱情",): "1",
    ("喜剧",): "4",
}
```

匹配逻辑：`genre` 按逗号拆分，遍历关键词，第一个命中即返回；无匹配返回 `"1"`（写实/真人）。

**UI 反馈：** 生成提示词时，如果 `art_style == "7"`，系统在 style_decl 中输出：

```
- 渲染风格：写实/真人（由「自动适配」根据故事类型「科幻,悬疑」自动选择）
```

### 2.2 自定义风格参考图分析

**流程：**

```
用户选择标签页 [🎨 画风]，上传参考图（如冰雪奇缘截图）
         ↓
前端调用 POST /api/projects/{name}/analyze-style-reference
         ↓
后端将图片转 base64，通过聚合平台调用 Gemini 多模态
  system: "你是一个视觉风格分析器..."
  user: [图片] + "分析此图的视觉风格特征..."
         ↓
Gemini 返回：{"render_style": "3D CG", "tone": "冷蓝紫色调", ...}
         ↓
结果保存到项目 config 的 analyzed_style 字段
         ↓
所有后续角色/场景/道具提示词注入时附带此风格关键词
```

**API 设计：**

```
POST /api/projects/{name}/analyze-style-reference
Content-Type: multipart/form-data
  file: 图片文件

Response:
{
  "render_style": "3",
  "tone": "冷蓝紫色调，冰雪质感",
  "material": "半透明材质，镜面反射，次表面散射",
  "proportion": "迪士尼角色比例，头部略大，四肢修长",
  "raw_keywords": "3D CG, 冷色调, 冰雪,..."
}
```

**模型调用：** 复用现有聚合平台 Gemini 配置，`_call_llm_with_image`（新增辅助函数，单张图片 + 文本分析，不涉及生图）。

### 2.3 画风关键词注入点

分析结果注入位置：

| 注入点 | 内容 |
|---|---|
| 角色定妆照 prompt | `tone` + `material` + `proportion` |
| 场景 prompt | `tone` + `material` |
| 道具 prompt | `material` |
| style_decl | `render_style`（映射为具体画风名） |

---

## 三、参考图标签化（四标签页 UI）

### 3.1 数据结构

**之前（扁平数组）：**
```typescript
referenceUrls: string[]
```

**之后（分组对象）：**
```typescript
interface ReferenceUrlsByType {
  style: string[]     // 画风参考
  character: string[] // 人物参考
  scene: string[]     // 场景参考
  prop: string[]      // 道具参考
}
```

### 3.2 UI 改造

**组件：** `ReferenceImageUploader.tsx`

```
┌──────────────────────────────────────┐
│ 参考图片                              │
│ [🎨 画风] [👤 人物] [🏠 场景] [🔧 道具] │
├──────────────────────────────────────┤
│                                      │
│  (当前选中标签页的上传区 + 缩略图列表)    │
│                                      │
├──────────────────────────────────────┤
│  从历史作品选择                        │
└──────────────────────────────────────┘
```

**Props 变更：**
```typescript
interface ReferenceImageUploaderProps {
  urls: ReferenceUrlsByType
  onChange: (urls: ReferenceUrlsByType) => void
  // 移除原有的 urls: string[] / onChange: (urls: string[]) => void
}
```

**标签页特性：**
- 切换到哪个标签页，上传/粘贴/历史选择都归该类型
- 每个标签页下方展示该类型的已上传缩略图，悬停显示 X 按钮删除
- 默认标签页为 👤 人物

### 3.3 后端处理

**gen.py 改动：**

| 参考图类型 | 处理方式 |
|---|---|
| `style` | 不直接传给生图 API；先经 `analyze-style-reference` 分析，关键词注入 prompt |
| `character` | 传给生图 API，prompt 前缀 `【人物参考图】请保持以下人物特征...` |
| `scene` | 传给生图 API，prompt 前缀 `【场景参考图】请保持以下场景风格...` |
| `prop` | 传给生图 API，prompt 前缀 `【道具参考图】请参考以下道具造型...` |

**FreeImageRequest 模型变更：**
```python
class FreeImageRequest(BaseModel):
    # ... 现有字段 ...
    reference_urls_by_type: dict = {}  # {"style": [...], "character": [...], ...}
    # reference_urls 保留向后兼容
```

### 3.4 兼容性处理

- 旧版 `reference_urls`（list）仍接受，后台自动归类为 `character` 类型。
- 前端逐步迁移，`FreeImageGenForm` 和 `ProjectImageGenForm` 都改为使用 `ReferenceUrlsByType`。

---

## 四、文件改动清单

### 后端

| 文件 | 改动 |
|---|---|
| `agents/prompt_factory.py` | `generate_character_prompt` 新增 mode 参数，L1/L2 拆分 |
| `core/style_config.py` | 新增 `resolve_art_style()` 自动适配规则 + `analyzed_style` 字段 |
| `server/routes/projects.py` | 新增 `analyze-style-reference` 端点 + `prop-prompt` 端点 |
| `server/routes/gen.py` | `_call_image_api` 按参考图类型分组处理；`FreeImageRequest` 增加 `reference_urls_by_type` |
| `core/visual_bible.py` | 无需改动（复用现有 `accessories` 字段） |

### 前端

| 文件 | 改动 |
|---|---|
| `src/components/ReferenceImageUploader.tsx` | 四标签页 UI 改造，props 改为 `ReferenceUrlsByType` |
| `src/components/FreeImageGenForm.tsx` | 适配新的参考图分组接口 |
| `src/components/ProjectImageGenForm.tsx` | 新增道具区块 + 适配参考图分组 |
| `src/pages/ImageGenPage.tsx` | 参考图 state 改为 `ReferenceUrlsByType` |
| `src/lib/api.ts` | 新增 `analyzeStyleReference()`、`fetchPropPrompt()` |
| `src/lib/types.ts` | 新增 `ReferenceUrlsByType` 接口 |

---

## 五、不做的事

- ❌ L3 动作姿态层（后续迭代）
- ❌ 新建 `equipment` / `items` 数据库字段（复用现有 `accessories`）
- ❌ 大规模重写 gen.py（渐进式增加分组处理）
- ❌ 项目配置向导中新增画风选择步骤（画风当前已在创建项目时选择，本次只改动自动适配逻辑）
