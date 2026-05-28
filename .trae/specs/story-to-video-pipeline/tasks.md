# Tasks: 故事→视频完整管线架构

## 阶段2：图像一致性收尾

- [x] **Task 2.2：角色生图默认 2 张 → 已回退为1张（用户选择保持1张）**
  - [x] 保持 `useState(1)`，手动调数量即可

## 阶段3：视频一致性

- [x] **Task 3.1：场景图按名称精确匹配为参考图**
  - [x] 3.1.1 `server/routes/gen.py`: `ProjectShotRequest` 解析 `scene_name`
  - [x] 3.1.2 `server/routes/gen.py`: 参考图收集按 `scene_name` 过滤
  - [x] 3.1.3 `src/components/VideoProjectPanel.tsx`: L256-L263 传 `scene_name: shot.scene`
  - 验证：大厅镜头只用大厅图，走廊镜头只用走廊图

- [x] **Task 3.2：分镜 prompt 注入空间约束**
  - [x] 3.2.1 `prompts/storyboarder.txt`: 末尾追加 6 条空间约束规则
  - [x] 3.2.2 `agents/storyboarder.py`: `generate_chunk` 注入 `ctx.spatial_state`
  - [x] 3.2.3 `src/components/VideoProjectPanel.tsx`: 解析分镜提取 `spatial_state`
  - 验证：分镜叙事文字包含方位参照

- [x] **Task 3.3：ShotContext 上一镜状态传递**
  - [x] 3.3a `agents/prompt_factory.py`: `build_shot_prompt` 精简 — 角色/场景只保留名称，去掉冗长外貌/环境描述
  - [x] 3.3b `server/routes/gen.py`: `generate_project_shot` — 读上一镜叙事文字注入 prompt 前缀
  - 验证：镜头N+1 的 prompt 开头有 "承接上一镜头：..."

## 阶段4：管线质控

- [x] **Task 4.1：ContinuityLog 连续性追踪器**
  - [x] 4.1.1 `core/continuity.py`: **新建** — extract_continuity + save/load/generate_injection
  - [x] 4.1.2 `server/async_orch.py`: 每集保存后提取 → 下一集生成前注入前情提要
  - 验证：第2集 prompt 包含第1集结尾的人物位置和持有物品

- [x] **Task 4.2：QC Gates 自动检查**
  - [x] 4.2.1 `core/qc_gates.py`: **新建** — check_g1~g5 + g7 共 6 个检查函数
  - [x] 4.2.2 `server/async_orch.py`: 12 个检查点，每阶段完成后调 QC → WebSocket 推送 qc_warnings
  - 验证：故意造无场景分镜 → G5 报警

## 阶段5：音频与合成

- [ ] **Task 5.1：TTS 配音 + 字幕（长期）**
  - [ ] 5.1.1 `core/tts.py`: **新建** — TTS 封装
  - [ ] 5.1.2 `server/routes/gen.py`: 新增 `/tts/generate` + `/tts/export-srt`
  - [ ] 5.1.3 前端视频预览叠加字幕
  - 验证：导出带字幕的视频文件

- [ ] **Task 5.2：BGM 情绪匹配（长期）**
  - [ ] 5.2.1 每集标注情绪曲线
  - [ ] 5.2.2 预置 BGM 分类
  - [ ] 5.2.3 前端叠加 BGM 轨道
  - 验证：播放时不同段落有不同背景音乐

# 依赖关系

```
2.2 ──┐
3.1 ──┤ (可并行)
3.2 ──┘
       │
4.1 ──┤ (可并行，均依赖 3.2)
4.2 ──┘
       │
3.3 ──┘ (依赖 4.1 的 ContinuityLog)
       │
5.1 ──┘ (独立，依赖 TTS 服务可用性)
5.2 ──┘ (依赖 5.1)
```
