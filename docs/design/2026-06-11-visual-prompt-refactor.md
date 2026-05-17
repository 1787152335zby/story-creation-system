# 视觉提取 → 提示词生成 → 生图 重构方案

## 一、现状与问题

### 工作流顺序问题
```
当前: 05_提示词 → 06_视觉提取 → 07_生图
                           ↑ 视觉提取在提示词之后！
```
提示词生成器（PromptEngineer）写视频提示词时，**不知道角色外貌/场景布局**，
只能写角色名，生图时再临时提取外貌，导致不一致。

### 视觉提取问题
1. **一次全量提取** — 剧本太长时会截断，漏角色
2. **JSON 解析脆弱** — LLM 输出稍微偏离格式就崩
3. **主次不分** — 主角和路人甲同等对待
4. **无用户确认** — 提取了什么用户不知道

### 项目模式生图问题
1. **只能批量全部生成**，不能选角色/场景
2. **和自由模式 UI 不一致**，缺少模型选择、参数控制

---

## 二、整体架构

### 2.1 新的工作流顺序

```
workflow.yaml 改为:
  04_分镜 → 05_视觉提取 → 06_提示词生成 → 07_生图 → 08_视频
```

### 2.2 模块关系

```
                  ┌──────────────────┐
                  │  VisualExtractor  │
                  │  (05_视觉提取)     │
                  │  输出: 角色/场景   │
                  │  JSON 文件         │
                  └────────┬─────────┘
                           │ 依赖
                  ┌────────▼─────────┐
                  │  PromptFactory    │
                  │  (06_提示词生成)   │  ← 独立模块，可单独调用
                  │  三类输出:         │
                  │   - 角色提示词     │
                  │   - 场景提示词     │
                  │   - 分镜提示词     │
                  └────────┬─────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ImageGenPage      VideoGenPage        管线自动
   (选角色→生图)    (选场景→生视频)      (顺序执行)
```

### 2.3 数据格式约定

**角色 JSON（扩展字段）：**
```json
{
  "name": "张三",
  "type": "main",          // main | minor
  "appearance": "...",
  "age": "25",
  "gender": "男",
  "clothing": "...",
  "expression": "冷峻",    // 新增
  "pose": "站立",          // 新增
  "accessories": ["剑"],   // 新增
  "key_features": [],
  "related_scenes": ["第1场-古堡大厅", "第3场-森林小径"],  // 新增
  "status": "confirmed"    // pending | confirmed
}
```

**场景 JSON（不变）：**
```json
{
  "name": "古堡大厅",
  "environment": "...",
  "lighting": "...",
  "color_tone": "...",
  "props": [],
  "status": "confirmed"
}
```

---

## 三、模块详细设计

### 模块 A：VisualExtractor（重构）

**文件：** `agents/visual_extractor.py` + `core/visual_bible.py`

**改进点：**

#### A1. 分段提取 + 去重

不再一次读全文，而是按分镜/场次逐段提取：

```
剧本全文 → 按"第X场"分割 → 每段调用 LLM → 合并结果 → 去重
                                                   ↑ name 相同则合并字段
```

这样即使剧本很长也不会丢角色。

#### A2. 主次角色分类

新增 Prompt 指示 LLM 判断角色类型：
```
判断标准：
- 主要角色：出现在 3+ 场，有台词，推动剧情
- 次要角色：出现在 1-2 场，台词少或无
```

#### A3. 字段增加

新增 `expression`、`pose`、`accessories`、`related_scenes`。
在提取 Prompt 里加入：
```
请为每个角色分析：
- 表情/神态（如：冷峻、温柔、阴险）
- 典型姿态/动作（如：站立、骑马、持剑）
- 配饰/携带物品（如：眼镜、项链、长剑）
- 该角色出现在哪些场景中
```

#### A4. 用户确认/补全

新增 API：
```
POST /api/visual-extract/{project}/confirm
  → 标记所有角色/场景为 confirmed

POST /api/visual-extract/{project}/characters
  body: { name: "李四" }
  → LLM 根据剧本自动补全该角色的外貌描述

PUT /api/visual-extract/{project}/characters/{name}
  body: { appearance: "..." }
  → 手动编辑角色信息

DELETE /api/visual-extract/{project}/characters/{name}
  → 删除错误提取的角色
```

---

### 模块 B：PromptFactory（新建独立模块）

**文件：** `agents/prompt_factory.py`

不继承 AgentBase，是纯函数式模块，可被任意地方调用。

#### B1. 三类提示词生成器

```python
class PromptFactory:
    @staticmethod
    def generate_character_prompt(char: dict) -> str:
        """生成角色定妆照提示词"""
        type_tag = "主要角色" if char["type"] == "main" else "次要角色"
        return (
            f"'{char['name']}' 定妆照，{type_tag}。"
            f"外貌：{char['appearance']}。"
            f"服装：{char['clothing']}。"
            f"表情：{char.get('expression', '自然')}。"
            f"姿态：{char.get('pose', '站立')}。"
            f"配饰：{'、'.join(char.get('accessories', []))}。"
            f"纯白背景，角色居中。"
        )

    @staticmethod
    def generate_scene_prompt(scene: dict, angle: str = "正视图") -> str:
        """生成场景概念图提示词"""

    @staticmethod
    def generate_storyboard_prompt(
        storyboard_text: str,
        characters: list[dict],
        scenes: list[dict],
        style_context: str
    ) -> str:
        """生成分镜逐镜头提示词，自动嵌入角色外貌和场景描述"""
```

#### B2. API 路由

新增 `server/routes/prompt_gen.py`：

```
POST /api/prompt-gen/character
  body: { project_name, character_name }
  → 返回角色提示词

POST /api/prompt-gen/scene
  body: { project_name, scene_name, angle }
  → 返回场景提示词

POST /api/prompt-gen/storyboard
  body: { project_name, chunk_name }
  → 返回该分段的提示词
```

#### B3. 前端调用场景

```
ImageGenPage 项目模式：
  1. 用户勾选角色 → 调 POST /api/prompt-gen/character
  2. 返回提示词，显示在文本框中
  3. 用户可编辑 → 调 POST /api/image-gen/free
```

---

### 模块 C：ImageGenPage 项目模式（重写）

**文件：** `src/pages/ImageGenPage.tsx`

#### C1. 布局

项目模式和自由模式统一 UI：

```
┌── 选择项目 ────────────────────────────────────┐
│  [我的故事  ▼]  角色:3 场景:2  ✅ 已提取        │
│  [🔄 视觉提取] [📋 查看/编辑角色]              │
└─────────────────────────────────────────────────┘

┌── 选择生成目标 ────────────────┐
│  ☐ 张三 (主要角色)   ← 角色    │
│  ☑ 李四 (次要角色)             │
│  ☑ 古堡大厅           ← 场景  │
│  ☐ 森林小径                    │
│  选中的项会拼入下方提示词       │
└─────────────────────────────────┘

┌── 提示词 ──────────────────────────────────────┐
│ [根据选择的角色/场景自动填充...]                  │
│                                                   │
│ 模型 [GPT-Image ▼] 尺寸 [1024² ▼] 数量 [1 ▼]     │
│ [✨ 生成]                                         │
└───────────────────────────────────────────────────┘

┌── 生成结果 ─────────────────────────────────────┐
│  [img] [img] [img] [img]                        │
└──────────────────────────────────────────────────┘
```

#### C2. 项目模式流程

```
1. 选择项目 → 自动加载角色/场景列表
2. 如果没提取 → 点「视觉提取」→ 后端分段提取 → 刷新列表
3. 勾选想生成的角色/场景（支持多选）
4. 自动生成提示词（也可手动修改）
5. 选模型/尺寸/数量 → 点生成
6. 生成的图保存到该项目目录
```

---

## 四、涉及文件清单

| 文件 | 操作 |
|:-----|:-----|
| `workflow.yaml` | 改成 05 = 视觉提取, 06 = 提示词生成 |
| `core/visual_bible.py` | 重写：分段提取+去重+主次分类+新字段 |
| `agents/visual_extractor.py` | 适配新的 VisualBibleExtractor |
| `agents/prompt_factory.py` | **新建** |
| `server/routes/prompt_gen.py` | **新建** |
| `server/app.py` | 注册 prompt_gen 路由 |
| `server/routes/projects.py` | 添加视觉提取的 CRUD API |
| `tools/image_api_openai_compat.py` | 已支持 model 参数，无需改 |
| `src/lib/api.ts` | 添加 promptGen 等 API 函数 |
| `src/pages/ImageGenPage.tsx` | 重写项目模式 |
