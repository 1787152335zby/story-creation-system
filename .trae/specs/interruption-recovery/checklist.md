# 验证清单

## Task 1: 线程取消 Bug
- [x] `_run_chunked_generation` 的 while 循环有 `except asyncio.CancelledError` 捕获
- [x] 捕获后设置 `cancelled[0] = True`
- [x] 生成中刷新页面，后台线程不再泄漏

## Task 2: 持久化
- [x] `project.set_pending_episode(...)` 方法存在，保存到 config 并持久化
- [x] `project.clear_pending_episode()` 方法存在
- [x] `project.pending_episode` property 存在
- [x] `_run_chunked_generation` 每集生成后调用 `set_pending_episode`
- [x] `_run_chunked_generation` 在通过/完成时清理状态

## Task 3: 断点恢复
- [x] `_resume_chunked_approval` 方法存在
- [x] 方法读取已保存的 chunk 文件并重放
- [x] 方法发送 `episode_complete` 并等待用户操作
- [x] `continue_run` 在进入阶段前检查 `pending_episode`
- [x] `run` 在进入阶段前检查 `pending_episode`
- [x] 匹配时调用 `_resume_chunked_approval`

## 端到端测试
- [ ] 生成完第一集后刷新 → 恢复审核栏
- [ ] 生成中刷新 → 不泄漏线程，重新连接后重新生成该集
- [ ] auto_approve 开启时不受影响
- [ ] 所有集通过后 `pending_episode` 被清空
