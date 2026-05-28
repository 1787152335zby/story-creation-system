# 修复剧情逐集生成内容重复（所有集同一内容+四份相同文件） Spec

## Why
剧情生成时，短剧/电视剧等自动分集模式（auto chunks）下：
1. 所有集生成了**完全相同的内容**（每集都是完整故事），而非按集拆分
2. 导致 `02_完整剧情/第1集/完整剧情.md` ~ `02_完整剧情/第N集/完整剧情.md` 全部内容相同

## Root Cause
`ChunkIter.set_auto_blocks()` ([chunk_strategy.py:L106](file:///e:/AI/Trae CN/book/story-creation-system1.2/core/chunk_strategy.py#L106)) 创建所有 block 时 `content` 字段全部设为空字符串：
```python
self.blocks = [{"index": i, "name": self.plan.chunk_names[i], "content": ""} for i in range(count)]
```

而 `PlotExpander.generate_chunk()` ([plot_expander.py:L149](file:///e:/AI/Trae CN/book/story-creation-system1.2/agents/plot_expander.py#L149)) 在 `outline_section` 为空时会 fallback 到整个大纲：
```python
prompt = prompt.replace("{outline}", ctx.outline_section or outline)
```

**结果**：每集 LLM 收到相同的完整大纲，生成完整的全量故事，导致 N 份内容完全相同的文件。

## What Changes
- **修复 `prepare_generation`**：在 auto 模式确定 chunk_count 后，用 LLM 预分析大纲的分集边界，将大纲按集切分到各 block 的 `content` 字段
- **新增 `_assign_outline_split` 方法**：将大纲文本按 episode 分配，保证每集的 `outline_section` 是相关段落而非空字符串
- 这样 `generate_chunk` 的 `{outline}` 占位符会被替换为对应集的大纲片段，LLM 能够按集生成差异化内容

## Impact
- Affected specs: 剧情逐集生成
- Affected code:
  - [chunk_strategy.py](file:///e:/AI/Trae CN/book/story-creation-system1.2/core/chunk_strategy.py) — `set_auto_blocks()` 新增 `outline` 参数，让每块承载不同的大纲片段
  - [plot_expander.py](file:///e:/AI/Trae CN/book/story-creation-system1.2/agents/plot_expander.py) — `prepare_generation()` 在 auto 模式调用 LLM 做大纲分集切分

## MODIFIED Requirements

### Requirement: 自动分集模式下每集收到专属大纲片段
系统 SHALL 在自动分集模式（短剧/电视剧/广播剧）下，通过 LLM 预分析将大纲切分为 N 段，每集 `generate_chunk` 的 `{outline}` 占位符替换为该集对应的大纲片段，而非完整大纲。

#### Scenario: 短剧4集生成
- **GIVEN** 故事类型为"短剧"，LLM 判断应分为 4 集
- **WHEN** `prepare_generation()` 确定 chunk_count=4
- **THEN** 调用 LLM 将大纲按 4 集切分（或按比例均分）
- **AND** 第1集的 `outline_section` 包含大纲前1/4内容
- **AND** 第2集的 `outline_section` 包含大纲第2/4内容
- **AND** 依此类推
- **AND** 每集 `generate_chunk` 的 prompt 使用对应集的大纲片段

#### Scenario: 用户配置集数
- **GIVEN** 用户在项目配置中设置了 6 集
- **THEN** 按 6 集切分大纲

### Requirement: 各集内容差异化
每集生成的内容 SHALL 对应其大纲片段范围，不得产生完整故事的重复内容。
