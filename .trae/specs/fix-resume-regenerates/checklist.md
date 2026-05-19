# 验证清单

## Task 1: run() 跳转 continue_run
- [x] `run()` 中 `has_done` 检查之后，有 `pending_ep` 检查
- [x] 存在时调用 `continue_run()` 并 `return`

## Task 2: set_pending_episode 记录 chunk_files
- [x] 函数签名含 `chunk_files=None`
- [x] 保存到 config["pending_episode"]["chunk_files"]

## Task 3: 暂停时记录已生成文件名
- [x] `_run_chunked_generation` 的 paused 路径中调用 `set_pending_episode` 传入 `chunk_files`
- [x] 文件名列表覆盖 ci=0 到当前 ci 的所有已保存文件

## Task 4: 恢复时重建 existing_full_parts
- [x] `continue_run` 的降级路径中读取 `chunk_files` 内容
- [x] 构建 `existing_parts` 列表传递给 `_run_chunked_generation`

## 端到端测试
- [ ] 生成两集→点"完成"→退出重进→点"继续创作"→从第3集开始生成
- [ ] 所有集通过后合并文件包含全部内容
- [ ] 刷新恢复（生成完一集后刷新→审核栏恢复）
