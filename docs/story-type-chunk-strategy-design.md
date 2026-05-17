# 按故事类型适配的分块生成策略

## 背景

当前系统所有故事类型都使用相同的生成策略：`call_llm_stream_with_continuation` 一次性生成全文 + 自动续写。这导致：

- **长内容衰减**：LLM 在后段质量下降，剧情虎头蛇尾
- **续写机制脆弱**：依赖 LLM 输出结束标记，判断不准确
- **无法跨类型优化**：电影的三幕结构与短剧的多集结构共用同一套逻辑

## 核心思路

不改 workflow.yaml 的阶段定义（仍然是 6 个阶段），在**每个 Agent 内部**根据 `style.story_type` 选择生成策略：

```
workflow.yaml: outline_designer → plot_expander → screenplay_writer → storyboarder → prompt_engineer → video_producer
                          ↓              ↓               ↓               ↓               ↓
                    Agent 内部根据 story_type 选择分块策略
```

## 新增模块

### 1. core/chunk_strategy.py — 分块策略定义

根据故事类型返回分块计划（ChunkPlan）：

```python
class ChunkPlan:
    chunk_count: int | str    # 分块数 或 "auto" 让 LLM 自动决定
    chunk_names: list[str] | None  # 块名称列表，None=自动命名
    reverse_order: bool       # 是否逆向生成（先写最后一块）
    delimiter: str            # 正则，用于从大纲提取分块边界
    context_window: int       # 桥接时传入前几块（0=全部）
    summarize: bool           # 是否提取摘要
```

各故事类型的配置：

| 类型 | chunk_count | reverse_order | context_window | summarize |
|:-----|:-----------:|:-------------:|:--------------:|:---------:|
| 电影 2 | 3 | true | 0（全部） | true |
| 短剧 1 | auto | false | 3 | true |
| 电视剧 3 | auto | false | 2 | true |
| 小说 4 | auto | false | 3 | true |
| 舞台剧 5 | 3 | true | 0（全部） | true |
| 广播剧 6 | auto | false | 0（全部） | true |

### 2. core/summary_extractor.py — 摘要提取

每个块生成后提取结构化摘要：

```
## 关键元素追踪
- 未解悬念: ...
- 角色状态变化: ...
- 重要道具位置: ...
- 时间线推进: ...
- 情绪基调: ...
```

摘要会附加到后续块的 prompt 中，作为 `{summary_chain}` 变量。

### 3. ChunkIter — 分块迭代器

```python
class ChunkIter:
    def __init__(self, plan: ChunkPlan, outline: str):
        self.plan = plan
        self.blocks = self._parse_blocks(outline)  # 从大纲提取块边界

    def __iter__(self):
        indices = range(len(self.blocks))
        if self.plan.reverse_order:
            indices = reversed(indices)  # C方案：逆向
        for idx in indices:
            yield ChunkContext(
                index=idx,
                name=self.blocks[idx].name,
                content=self.blocks[idx].content,
                previous_full=[self.blocks[j].output for j in range(idx) if j < idx],  # D方案：前序全文
                summaries=self._get_summaries(idx),  # D方案：摘要链
            )
```

## 修改 Agent

### plot_expander.py（完整剧情）

```python
def run_stream(self, project, style, input_content):
    plan = ChunkStrategy.get_plan(style.story_type, input_content)
    iterator = ChunkIter(plan, input_content)
    
    for ctx in iterator:
        prompt = self._build_prompt(template, ctx, plan)
        chunk_output = ""
        for token in self.call_llm_stream(prompt, ...):
            chunk_output += token
            yield token
        
        # 保存当前块输出到磁盘
        self._save_chunk(project, plan, ctx, chunk_output)
        
        # 提取摘要
        if plan.summarize:
            summary = SummaryExtractor.extract(chunk_output)
            ctx.summary = summary
```

### screenplay_writer.py（完整剧本）

从"一次生成"改为按幕循环。输入的剧情已经是分幕的，剧本对应生成：

```
完整剧情_第一幕.md → 完整剧本_第一幕.md
完整剧情_第二幕.md → 完整剧本_第二幕.md
完整剧情_第三幕.md → 完整剧本_第三幕.md
```

### storyboarder.py（分镜脚本）

分镜目前已经按幕拆分输出（split=true），输入侧改为读对应的分幕剧本：

```
输入: 03_完整剧本/完整剧本_第一幕.md → 输出: 04_分镜脚本/分镜脚本_第一幕.md
```

### prompt_engineer.py（提示词）

同上。

## 保存策略

每个块保存为独立文件：

```
02_完整剧情/
├── 完整剧情.md                ← 合并文件（所有幕拼接）
├── 完整剧情_第一幕.md          ← 第1幕独立文件
├── 完整剧情_第二幕.md          ← 第2幕独立文件
└── 完整剧情_第三幕.md          ← 第3幕独立文件
```

- `_save_split_output` 改为在生成时直接保存分块，而不是事后用 `split_by_headings` 分割
- 合并文件在最后一步拼接生成（用于向下兼容、API 读取用）

## 前端影响

**不需要修改。** 前端已经支持分幕文件的读取：

- `fetchPhaseContent` 会检查 `file_list` 字段
- 侧边栏已支持分幕展开/折叠
- 流的显示仍然是逐 token 输出（所有块通过同一个 stream 通道发出）

## 文件改动清单

| 文件 | 操作 | 改动量 |
|:-----|:-----|:------|
| `core/chunk_strategy.py` | **新增** | ~80行 |
| `core/summary_extractor.py` | **新增** | ~50行 |
| `agents/plot_expander.py` | 重写 `run_stream` | 核心改动 |
| `agents/screenplay_writer.py` | 重写 `run_stream` | 核心改动 |
| `agents/storyboarder.py` | 重写 `run_stream` | 中等改动 |
| `agents/prompt_engineer.py` | 重写 `run_stream` | 中等改动 |
| `server/async_orch.py` | 修改 `_save_split_output` | 小改 |
| `server/async_orch.py` | 修改 `_get_input` 分幕匹配 | 小改 |
| `agents/orchestrator.py` | 修改 `_run_agent_phase` | 小改 |
| `prompts/plot_expander.txt` | 新增 `{summary_chain}` 占位 | 小改 |
| `prompts/screenplay_writer.txt` | 新增 `{summary_chain}` 占位 | 小改 |

## 分两轮实施

### 第一轮：D 方案通用化

实现 `ChunkStrategy` + `SummaryExtractor`，修改 `plot_expander` 和 `screenplay_writer`。

所有故事类型都按正序分块生成 + 摘要桥接。这一轮完成后：
- 所有故事类型的输出质量提升（不再一次性长篇生成）
- 但电影仍然是正序生成（第1→2→3幕），没有逆向优化

### 第二轮：C 方案逆向优化

`ChunkStrategy` 中为电影（类型 2）和舞台剧（类型 5）启用 `reverse_order=True`。

这一轮完成后：
- 悬念类故事的结局质量大幅提升
- 所有伏笔精准指向结局

## 验证方式

1. 创建电影项目 → 观察是否按 3 幕生成、幕文件是否独立保存
2. 创建短剧项目 → 观察分集生成、摘要桥接是否正常
3. 创建电影项目（C方案） → 观察生成顺序是否为 3→2→1
4. 刷新页面重新进入 → 继续创作从断点恢复
5. 对比改版前后的生成字数/完整性
