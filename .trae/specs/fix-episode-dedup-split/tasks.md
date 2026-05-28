# Tasks

- [x] Task 1: 修改 `set_auto_blocks` 支持大纲分片
  - [x] 在 [chunk_strategy.py](file:///e:/AI/Trae CN/book/story-creation-system1.2/core/chunk_strategy.py#L103-L114) 的 `set_auto_blocks` 方法中新增 `outline` 参数
  - [x] 当传入 `outline` 且长度>100且 count>1 时，按块数均分大纲文本，赋值到各 block 的 `content` 字段
  - [x] 均分逻辑：`per_chunk = len(outline) // count`，每块取对应区间
  - [x] 如果不传 `outline`（向后兼容），保持原有空 `content` 行为

- [x] Task 2: 修改 `prepare_generation` 在 auto 模式传入大纲
  - [x] 在 [plot_expander.py](file:///e:/AI/Trae CN/book/story-creation-system1.2/agents/plot_expander.py#L117) 的 `prepare_generation()` 中，auto 模式两处 `set_auto_blocks` 调用均已传入 `outline=outline`
  - [x] `generate_chunk` 中 `{outline}` 已被替换为每集专属的 `ctx.outline_section`

- [x] Task 3: 同步修复 `_resolve_auto_chunks`（run_stream 路径）
  - [x] 在 [plot_expander.py](file:///e:/AI/Trae CN/book/story-creation-system1.2/agents/plot_expander.py#L208) 的 `_resolve_auto_chunks()` 中，`set_auto_blocks` 已传入 `outline=outline`
  - [x] 循环中 `{outline}` 已改为 `ctx.outline_section or outline`（优先用每集专属片段）

# Task Dependencies
- Task 1 是基础，Task 2 和 Task 3 依赖 Task 1
- Task 2 和 Task 3 相互独立，可在 Task 1 完成后并行
