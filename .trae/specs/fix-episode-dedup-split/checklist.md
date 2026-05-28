# Checklist

- [x] `set_auto_blocks(count, outline=...)` 将大纲按块数均分到各 block 的 `content` 字段
- [x] 各 block 的 `outline_section`（即 `content`）非空且互不相同
- [x] `prepare_generation()` 在 auto 模式调用 `set_auto_blocks` 时传入 `outline`（两处）
- [x] `_resolve_auto_chunks()` 在 auto 模式调用 `set_auto_blocks` 时传入 `outline`
- [x] `_resolve_auto_chunks()` 每集使用对应 `ctx.outline_section` 而非完整 `outline`
- [x] 逐集生成的各集内容互不相同（非重复）
- [x] 合并文件 `02_完整剧情/完整剧情.md` 包含各集不同内容
- [x] 电影/舞台剧固定分块模式（3幕）不受影响（回归验证）
- [x] 小说 bible_mode 不受影响（回归验证）
