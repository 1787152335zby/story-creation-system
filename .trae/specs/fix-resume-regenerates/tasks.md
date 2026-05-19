# 任务列表

- [x] Task 1: `run()` 检测 `pending_episode` 并跳转
  - [x] 在 `run()` 的 `has_done` 检查之后，添加 `pending_ep` 检查
  - [x] 如果存在，调用 `continue_run()` 并 `return`

- [x] Task 2: `set_pending_episode` 增加 `chunk_files` 参数
  - [x] 函数签名增加 `chunk_files=None`
  - [x] 保存到 config 中

- [x] Task 3: `_run_chunked_generation` 暂停时记录 chunk_files
  - [x] 在 paused 返回前，收集已生成的 chunk 文件名（i=0..ci）
  - [x] 调用 `set_pending_episode` 时传入

- [x] Task 4: `continue_run` 恢复时读取已有文件构建 `existing_full_parts`
  - [x] 在 `pending_episode` 降级路径中，读取 `chunk_files` 内容
  - [x] 传递给 `_run_chunked_generation(existing_full_parts=...)`

- [x] Task 5: 编译、构建并重启
  - [x] Python 语法验证通过
  - [x] 前端构建成功
  - [x] 系统已重启
