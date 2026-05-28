# Tasks: 管线重构

- [ ] **Task 1: plot_expander / screenplay_writer 输出路径改为集子文件夹**
  - [ ] 1.1 `server/async_orch.py` `_run_chunked_generation`: 修改 chunk_fname 从 `{base}_{ep}.md` → `{ep}/{base}.md`
  - [ ] 1.2 确保 PhaseTimeline.tsx 的 `fetchPhaseContent` 和 `_get_input` 能正确读取子文件夹
  - [ ] 1.3 Workspace.tsx 的 `PHASE_DIRS` 和文件映射保持不变（父目录合并文件仍然存在）
  - 验证：生成一个多集项目 → 检查 `02_完整剧情/第1集/完整剧情.md` 存在

- [ ] **Task 2: visual_extractor 新增道具提取**
  - [ ] 2.1 `core/visual_bible.py`: 在 `extract_all` 中新增 `extract_props` 方法，从剧本提取道具
  - [ ] 2.2 道具 JSON 保存到 `05_角色场景/道具/{道具名}.json`
  - [ ] 2.3 `server/routes/projects.py`: 视觉素材 API 返回时包含道具列表
  - [ ] 2.4 `src/components/VideoProjectPanel.tsx`: 道具列表展示在角色/场景旁边
  - [ ] 2.5 `agents/prompt_factory.py`: `build_shot_prompt` 注入道具外观信息
  - 验证：新建项目 → 视觉提取 → 检查 道具/ 目录有 JSON 文件

- [ ] **Task 3: storyboarder 分集生成确认与修复**
  - [ ] 3.1 `agents/storyboarder.py`: 确认 `_parse_episode_blocks` 在剧本有 `## 第N集` 时正确识别
  - [ ] 3.2 `agents/storyboarder.py`: `generate_chunk` prompt 中强制要求输出以 `## {chunk_name}` 开头
  - [ ] 3.3 检查 `test_episode_split_in_storyboarder` — 如果剧本确实只有1集，分镜1集是正确行为
  - 验证：用测试48（5集）重新生成分镜 → 每个文件以 `## 第N集` 开头

- [ ] **Task 4: 端到端验证**
  - [ ] 4.1 新建项目 → 走完整 6 阶段 → 检查所有输出目录结构
  - [ ] 4.2 检查 prompt_factory 输出的 `06_提示词/` 结构与规格一致
  - [ ] 4.3 检查首页项目卡片 phases 进度条与 config 一致

# Task Dependencies

- Task 1 (子文件夹) 和 Task 2 (道具) 可并行
- Task 3 依赖 Task 1（分镜保存路径也改子文件夹）
- Task 4 依赖 Task 1+2+3
