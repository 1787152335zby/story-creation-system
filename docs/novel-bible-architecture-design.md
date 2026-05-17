# 超长篇小说「索引级上下文」架构设计

## 背景

现有系统已实现**分块生成策略**（D 方案），用于电影等有限长度的故事类型。但对于**超长篇小说**（10 万-300 万字，故事类型 4），D 方案存在根本性瓶颈：

- **prompt 膨胀**：第 100 章的 prompt 需包含前 99 章回顾 → 15 万字输入，超出 LLM context 窗口
- **摘要衰减**：多层摘要叠加后信息丢失严重
- **无法维护一致性**：角色状态、伏笔、势力关系在超长篇幅中难以保持连贯

## 核心思路

不是把"原文"传给下一章，而是把**对原文的高密度索引**传给下一章——称为"故事 Bible"。

```
传统 D 方案（超长文本会崩）:
第100章 prompt = 大纲 + 第99章全文 + 第98章全文 + ... → 15万字 ❌

索引级上下文（可水平扩展）:
第100章 prompt = 故事 Bible（~3000字）+ 近3章摘要（~500字）→ 稳定 ~3500字 ✅
```

无论写到 300 万字还是 1000 万字，单章 prompt 大小恒定在 5000 字以内。

## 架构总览

```
                      用户输入/大纲
                           │
                           ▼
┌──────────────────────────────────────────────┐
│               ChapterGenerator               │
│  第N章 prompt = Bible(当前) + 近3章摘要       │
│             │                        ▲       │
│             ▼                        │       │
│         生成第N章 ──── 保存到磁盘 ─────┘       │
└──────────────────┬───────────────────────────┘
                   │ 新章节内容
                   ▼
┌──────────────────────────────────────────────┐
│              BibleUpdater                    │
│  用LLM从新章节中提取增量变化：                │
│  ① 角色状态变化   ② 势力关系变化              │
│  ③ 新伏笔/已收伏笔 ④ 时间线事件              │
│  ⑤ 本章摘要                                  │
└──────────────────┬───────────────────────────┘
                   │ 增量 diff
                   ▼
┌──────────────────────────────────────────────┐
│               NovelBible                     │
│  结构化故事索引（YAML文件）                    │
│  - 角色图谱  - 势力关系  - 事件时间线          │
│  - 伏笔清单  - 世界观规则  - 章节摘要索引       │
└──────────────────────────────────────────────┘
```

## 核心组件

### 1. NovelBible — 故事圣经（数据层）

存储在 `04_novel_bible/bible.yaml` 文件中。

```yaml
# === 角色图谱 ===
characters:
  林尘:
    status: 存活
    cultivation: 金丹中期
    arc: 从复仇少年到修仙界新星
    relations:
      - 与师父白眉真人(信任)
      - 与魔教圣女苏媚(暧昧/敌对)
    last_seen_chapter: 47
    last_seen_location: 天剑宗后山
    key_items: ["师父遗物玉佩", "九天玄铁剑"]
    pending_hooks: ["玉佩中封印着上古剑魂（第3章埋下）"]
  苏媚:
    status: 存活
    cultivation: 元婴初期
    arc: 从魔教棋子到自主命运
    relations:
      - 与林尘(暧昧/敌对)
      - 与魔教教主(利用/戒备)
    last_seen_chapter: 45
    last_seen_location: 魔教总坛
    key_items: []
    pending_hooks: []

# === 势力关系 ===
factions:
  天剑宗:
    members: ["林尘", "白眉真人", "掌门清虚"]
    relations: ["与魔教敌对", "与散修联盟中立"]
    current_goal: 准备抵御魔教进攻
    influence_region: 东域
  魔教:
    members: ["苏媚", "魔教教主", "左右护法"]
    relations: ["与天剑宗敌对", "与妖族秘密联盟"]
    current_goal: 夺取九天玄铁剑
    influence_region: 西域

# === 事件时间线（仅重大转折）===
timeline:
  - chapter: 1
    type: 开端
    summary: 林尘目睹师父被杀，立誓复仇
  - chapter: 12
    type: 转折
    summary: 发现师父白眉真人竟是叛徒
  - chapter: 33
    type: 突破
    summary: 林尘突破金丹期，获得九天玄铁剑

# === 伏笔清单 ===
hooks:
  - description: 玉佩中的上古剑魂身份
    planted_at: 3
    status: 未收
    expected_resolve: 200章前后
  - description: 苏媚的真实身份（与林尘的童年渊源）
    planted_at: 15
    status: 未收
    expected_resolve: 100章前后

# === 世界观规则 ===
world_rules:
  - 修仙等级: 练气 → 筑基 → 金丹 → 元婴 → 化神
  - 九天玄铁剑每百年认主一次
  - 禁术血魂大法需献祭寿元

# === 章节摘要索引 ===
chapter_summaries:
  1: 林尘目睹师父被杀，被天剑宗收留
  2: 测试灵根发现天生剑骨
  3: 获得师父遗物玉佩
  ...
```

**关键设计原则**：
- 每个条目含 `last_seen_chapter`，跟踪信息时效
- 角色/势力/伏笔用独立条目，非大段描述
- 章节摘要是**事实性**的（20 字以内），非文学性评价

### 2. BibleUpdater — 增量更新引擎

每次新章节生成后，用一次 LLM 调用提取变更 diff：

```
BibleUpdater prompt:

以下是最新写的第{N}章内容。请分析变更并输出YAML格式的更新指令。

只输出有变化的部分，没有变化的部分不要输出。

## 格式
updates:
  characters:
    ? 角色名:
        status: "变化后的状态"  # 如果变化
        cultivation: "..."      # 如果变化
        last_seen_chapter: {N}
        last_seen_location: "..."
        pending_hooks: ["新增伏笔描述"]
  factions:
    ? 势力名:
        current_goal: "..."
  hooks:
    - description: "新伏笔描述"
      planted_at: {N}
      status: 未收
  timeline:
    - chapter: {N}
      type: 转折|高潮|铺垫
      summary: "一句话描述"
  chapter_summary: "本章20字以内摘要"
```

BibleUpdater 读取 LLM 输出的 YAML 增量，合并到当前 Bible 中：

```python
class BibleUpdater:
    def update(self, bible: NovelBible, chapter_num: int, content: str) -> NovelBible:
        # 1. 用 LLM 提取增量 diff
        diff_yaml = self._extract_diff(bible, chapter_num, content)
        # 2. 合并到 bible（不重写，只增量更新）
        bible.merge_diff(diff_yaml)
        # 3. 更新章节摘要
        bible.chapter_summaries[chapter_num] = diff_yaml.get("chapter_summary", "")
        # 4. 保存到磁盘
        self._save(bible)
        return bible
```

### 3. ChapterGenerator — 分章生成器

```python
class ChapterGenerator:
    def generate_chapter(self, bible: NovelBible,
                          chapter_num: int,
                          outline: str,
                          style: StyleConfig) -> str:
        
        recent_summaries = self._get_recent_summaries(bible, chapter_num)
        active_hooks = self._get_active_hooks(bible)
        active_chars = self._get_active_characters(bible, chapter_num)
        
        prompt = f"""
你正在写一部小说的第{chapter_num}章。

## 世界设定
{format_world_rules(bible.world_rules)}

## 当前角色状态
{format_active_characters(active_chars)}

## 活跃伏笔（需在本章或近期收束）
{format_active_hooks(active_hooks)}

## 近期章节回顾
{chr(10).join(recent_summaries[-3:])}

## 本章创作方向
{outline}

请只写本章内容。写完后在末尾加上结束标记：【本集完】
"""
        # 用流式 LLM 生成
        for chunk in self.llm.stream(prompt):
            yield chunk
```

## 数据流（以 300 章小说为例）

```
阶段1: 初始化 Bible
  - 用户提供世界观设定 + 大纲 → BibleUpdater 初始化空 bible
  - Bible 写入 04_novel_bible/bible.yaml

阶段2: 前三章（预热期）
  - 第1-3章：用传统 D 方案生成
  - 每章后 BibleUpdater 更新一次 bible
  - Bible 逐步积累角色和事件

阶段3: 第4-300章（稳定期）
  - 第N章 prompt = Bible(当前状态, ~3000字) + 近3章摘要(~500字)
  - ≈ 3500 字/章，恒定不变
  - 每章后 BibleUpdater 增量更新
  - 文件保存为 02_完整剧情/第001章.md ~ 第300章.md

阶段4: 每50章一致性校验（可选）
  - 用一次 LLM 调用通读 bible 各字段
  - 自动修复冲突（角色状态矛盾、伏笔重复等）
```

## Bible 容量估算

| 小说进度 | 角色数 | Bible 大小 | 单章 prompt | 可行性 |
|:---------|:------:|:----------:|:-----------:|:------:|
| 10 章 | 5 | 1.5K | 3.5K | ✅ |
| 100 章 | 20 | 3K | 5K | ✅ |
| 500 章 | 50 | 5K | 7K | ✅ |
| 1000 章 | 80 | 8K | 10K | ✅（16K窗口内）|
| 3000 章 | 150 | 18K | 20K | ⚠️ 需压缩摘要索引 |

**3000 章后的优化**：章节摘要从"每章 20 字"改为"每 10 章合并为一条 100 字概括"，3000 章摘要从 6 万字降到 3 万字。Bible 总大小可控制在 12K 以内。

## 和现有系统的集成

### 对 ChunkStrategy 的扩展

在 `ChunkStrategy.get_plan("4")`（小说类型）中新增标志：

```python
"4": ChunkPlan(
    chunk_count=0,  # auto
    chunk_names=[],
    reverse_order=False,
    delimiter=r"^#\s*第\d+章",
    context_window=3,
    summarize=True,
    bible_mode=True,  # ← 新增：启用圣经模式
)
```

### 对 workflow 的扩展

在 `workflow.yaml` 中新增 `bible_keeper` Agent：

```yaml
- name: 小说圣经维护
  agent: bible_keeper
  output: 04_novel_bible/
  condition: "story_type in ['4']"
  auto_skip: true
```

`bible_keeper` 不是一个单独的"阶段"，而是**在 plot_expander 生成每章后被回调**的阶段。它的核心方法是 `update_after_chapter()`。

### 修改 async_orch.py

`run` 和 `continue_run` 中的生成循环需要改为按章循环：

```python
# 伪代码
if phase.agent == "plot_expander" and style.story_type == "4":
    # 小说模式：逐章生成
    chapter_count = await self._determine_chapter_count(...)
    bible = NovelBible.load(project)
    for chapter_num in range(1, chapter_count + 1):
        # 生成一章
        chapter_content = await self._generate_chapter(agent, style, bible, chapter_num, ...)
        # 保存文件
        self._save_chapter(project, chapter_num, chapter_content)
        # 更新 bible
        bible = BibleUpdater().update(bible, chapter_num, chapter_content)
```

## 文件改动计划

| 文件 | 操作 | 说明 |
|:-----|:-----|:------|
| `core/novel_bible.py` | **新增** | NovelBible 数据类 + YAML 序列化 |
| `core/bible_updater.py` | **新增** | BibleUpdater 增量更新引擎 |
| `agents/bible_keeper.py` | **新增** | BibleKeeper Agent（管理 bible 更新） |
| `agents/plot_expander.py` | **修改** | story_type=4 时启用逐章+bible 模式 |
| `server/async_orch.py` | **修改** | 小说模式走逐章循环 |
| `core/chunk_strategy.py` | **修改** | ChunkPlan 新增 `bible_mode` 字段 |
| `workflow.yaml` | **修改** | 新增 bible_keeper 阶段 |

## 验证方式

1. 创建小说类型项目（story_type=4）
2. 观察生成的章节文件：`02_完整剧情/第001章.md` ...
3. 检查 `04_novel_bible/bible.yaml` 是否正确积累角色和事件
4. 生成 10 章后检查 bible 中的角色状态是否与章节内容一致
5. 检查每章 prompt 大小是否稳定在 5000 字以内
