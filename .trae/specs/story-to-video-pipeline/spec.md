# 故事→视频完整管线 — 细化实施计划

## 当前进度

✅ 阶段1 数据基础 (4/4)   ✅ 阶段2 4/5 (缺 2.2)
⬜ 阶段3 视频一致性 (0/3)   ⬜ 阶段4 管线质控 (0/2)   ⬜ 阶段5 音频合成 (0/2)

---

## 阶段2 收尾

### Task 2.2 — 角色生图默认 4 张

**目标：** 选角色 + 点"生成模板"后自动出 4 张，用户选 1 张确认。

**现状：** count 默认 1。数量选择器已有（P6），但用户不会主动调到 4。

**精确实现：**

| 文件 | 行 | 修改 |
|------|-----|------|
| `src/pages/ImageGenPage.tsx` | L56 | `useState(1)` → `useState(4)` （projectCount 默认值从 1 改 4） |

**影响：** 项目模式点"生成模板"时 count=4，自由模式仍然 1。

**验证：** 选林深 → 点"生成模板" → 结果区出现 4 张图。

---

## 阶段3 视频一致性（核心）

### 现状分析

当前 `VideoProjectPanel.tsx` 的批量生成流程：
1. 加载分镜提示词 (`06_提示词/分镜提示词*.md`)
2. 用户勾选角色/场景 → 自动获取 confirmedImages
3. 逐镜调用 `POST /api/projects/{name}/video/shots/generate` (即 `generate_project_shot`)
4. `generate_project_shot` 做的是：从分镜提示词文件中搜索"镜头N"段落 → 取前 800 字符 → 收集角色/场景确认图作为 img2video 参考图 → 调 Seedance API

**当前缺失：**
- 不知道哪个镜头属于哪个场景 → 无法选对场景参考图
- 不知道角色在镜头中的位置 → 无法保持空间一致性
- 没有 ShotContext 传递 → 镜头间位置跳变

---

### Task 3.1 — 场景全景图自动作视频首帧

**目标：** 每个镜头视频的首帧与对应场景的全景图一致。

**现状：** `generate_project_shot` 在 L1099-L1134 随机取场景图，不匹配镜头归属。

**精确实现：**

**A. 分镜 prompt 加场景归属（后端无需改分镜 agent，改模板即可）**

文件 `prompts/storyboarder.txt`，在输出格式规范中（已有 `场景：场景名称` 字段，不需要改模板）。

**B. 前端 `VideoProjectPanel.tsx` — 解析分镜时提取场景名**

当前解析逻辑 (L107-L142) 已经解析出 `scene` 字段。需要确认这个字段对应的是场景名。

**C. 后端 `generate_project_shot` — 按场景名匹配合适的场景全景图**

当前逻辑在 L1099-L1134 遍历所有场景取图，改为只取该镜头对应场景的确认图：

```python
# 伪代码
shot_scene = req.scene_name  # 新参数，镜头归属的场景名
ref_images = []
if shot_scene:
    scene_dir = GENERATED_DIR / "projects" / project_name / "scenes" / shot_scene
    if scene_dir.exists():
        for f in scene_dir.iterdir():
            if f.is_file() and f.suffix in ('.png', '.jpg'):
                ref_images.append(str(f))
```

**D. 前端 `VideoProjectPanel.tsx` — 生成时传 `scene_name`**

在 L248-L265 批量循环中，从 `shot.scene` 提取场景名传给 API。

**改动清单：**

| 文件 | 改什么 |
|------|--------|
| `server/routes/gen.py` | `ProjectShotRequest` 加 `scene_name: str = ""` |
| `server/routes/gen.py` | `generate_project_shot` L1099-L1134 按 `scene_name` 筛选场景图 |
| `src/components/VideoProjectPanel.tsx` | L241-L273 循环传 `scene_name: shot.scene` |
| `src/lib/api.ts` | `generateProjectShot` 新增 `scene_name` 参数 |

---

### Task 3.2 — 分镜 prompt 注入空间约束

**目标：** 分镜生成时自动包含 180° 轴线 + 空间坐标约束。

**现状：** `prompts/storyboarder.txt` 没有任何空间约束规则。`storyboarder.py` 的 `generate_chunk` 方法只做变量替换。

**精确实现：**

**A. 场景 JSON 增加 `spatial_map` 和 `camera_style` 字段**

不修改视觉提取流程（太复杂），改为在 `server/routes/projects.py` 新增端点让用户编辑场景时可选填，或在前端 scene-prompt 端点返回时附带默认值。

简化做法：在 `prompts/storyboarder.txt` 模板末尾追加一段**硬编码空间约束规则**：

```
## 摄影轴线与空间约束（必须遵守）

1. 每个场景建立一个虚拟摄影平面（180°轴线），所有镜头必须在此平面的同一侧
2. 严禁越轴——同一个对话场景中，所有镜头必须在轴线的同侧
3. 正反打时：
   - A看B的镜头 = 摄影机在A身后略侧，过A肩拍B，背景是该方向的场景画面
   - B看A的镜头 = 摄影机在B身后略侧，过B肩拍A，背景是反方向的场景画面
   - 两个镜头的背景必须不同（因为是相反方向），但必须属于同一场景
4. 镜头中的角色位置必须在叙事文字中说明相对于场景固定参照物的方位
5. 角色移动时，下一镜必须延续上一镜结束时的位置
```

**B. `storyboarder.py` `generate_chunk` 注入空间状态**

在 L225-L269 中，`prompt += f"\n\n请只写「{ctx.name}」的分镜内容..."` 这一行之后，追加：

```python
# 注入空间约束（如果存在上一镜状态）
if getattr(ctx, 'spatial_state', None):
    prompt += f"\n\n**上一镜空间状态（必须延续）：**\n{ctx.spatial_state}"
```

**C. 前端 `VideoProjectPanel.tsx` — 从分镜输出提取空间状态**

在解析分镜后，从叙事文字中提取位置信息（简单正则：`在.{0,30}(门前|窗边|控制台旁|大厅中央|走廊|墙边)`），存储到 `shot.spatial_state`。

**改动清单：**

| 文件 | 改什么 |
|------|--------|
| `prompts/storyboarder.txt` | 末尾追加"摄影轴线与空间约束"段落 |
| `agents/storyboarder.py` | `generate_chunk` 注入 `ctx.spatial_state` |
| `src/components/VideoProjectPanel.tsx` | 解析分镜后提取 `spatial_state` |

---

### Task 3.3 — ShotContext 上一镜状态传递

**目标：** 第2镜知道第1镜结束时角色在哪。

**现状：** 分镜逐集生成（`_run_chunked_generation`），但集内是连续生成的，镜头间没有状态传递。

**精确实现：**

**A. `storyboarder.py` `generate_chunk` — 维护镜头间状态**

在 `generate_chunk` 方法的循环中（`_run_chunked_generation` L1190-L1330），每生成一镜后提取该镜的"终态"（角色位置、持有物品、情绪），注入下一镜的 prompt：

```python
# 在 async_orch.py 的 _run_chunked_generation 中
shot_context = {}
for i in range(chunk_count):
    # 注入上一镜状态
    ctx = chunk_contexts[i]
    if shot_context:
        ctx.spatial_state = f"上一镜结束时空状态：{json.dumps(shot_context, ensure_ascii=False)}"
    # 生成分镜...
    # 生成完成后提取终态
    shot_context = _extract_end_state(output_text)  # 简单正则提取
```

**B. `_extract_end_state` 辅助函数**

在 `async_orch.py` 新增：

```python
def _extract_end_state(text: str) -> dict:
    """从分镜文本提取镜头结束时的空间状态"""
    import re
    result = {"positions": {}, "props": {}, "mood": ""}
    # 匹配 "XX站在YY" 
    for m in re.finditer(r'(\S{1,4})(?:站|坐|靠|躺|蹲|走)在(\S{1,10})', text[-500:]):
        result["positions"][m.group(1)] = m.group(2)
    return result
```

**改动清单：**

| 文件 | 改什么 |
|------|--------|
| `server/async_orch.py` | `_run_chunked_generation` 注入 `spatial_state` + 新增 `_extract_end_state` |

**这是一个"深度改动"，依赖阶段4的 ContinuityLog 才能完美运作。当前版本建议用硬编码规则（Task 3.2）作为简化版。**

---

## 阶段4 管线质控

### Task 4.1 — ContinuityLog 连续性追踪器

**目标：** 每集剧情/剧本生成后自动提取状态，下一集注入。

**精确实现：**

**A. 状态提取 prompt**

在 `core/` 下新增 `continuity.py`：

```python
def extract_continuity(episode_text: str, prev_log: dict) -> dict:
    """用 LLM 从本集文本中提取连续性状态"""
    # prompt: 请从以下剧本文本中提取关键状态...
    # 返回: {positions: {角色: 位置}, props: {角色: [道具]}, relationships: {...}, unresolved: [...]}
```

**B. async_orch.py 集成**

在 `_run_chunked_generation` 中：
- 每集生成完 → 调 `extract_continuity` → 写 `_continuity.json`
- 下一集生成前 → 读 `_continuity.json` → 拼入 prompt 前情提要

**改动清单：**

| 文件 | 改什么 |
|------|--------|
| `core/continuity.py` | **新建** — 状态提取逻辑 |
| `server/async_orch.py` | `_run_chunked_generation` 注入 continuity |

---

### Task 4.2 — QC Gates 自动检查

**目标：** 每阶段完后自动检查规则，不通过时 UI 警告。

**精确实现：**

**A. 检查函数**

```python
# core/qc_gates.py
def check_g1_outline(project) -> list[str]:  # 角色≥2、主线清晰、有冲突
def check_g2_plot(project) -> list[str]:     # 每集≥3节拍、支线追踪
def check_g3_script(project) -> list[str]:   # 对白差异化、语癖匹配
def check_g5_storyboard(project) -> list[str]: # 场景归属、无越轴
```

每个函数返回问题列表（空列表=通过）。

**B. async_orch.py 集成**

每个阶段 `phase_complete` 消息发送前，跑对应的 QC check。如果有问题，追加 `qc_warnings` 到消息中。

**C. 前端 Workspace.tsx**

收到 `qc_warnings` 后，在阶段卡片上显示黄色警告图标 + 点击查看详情。

**改动清单：**

| 文件 | 改什么 |
|------|--------|
| `core/qc_gates.py` | **新建** — 规则检查 |
| `server/async_orch.py` | 每个阶段完成后调 QC |
| `src/pages/Workspace.tsx` | 显示 qc_warnings UI |

---

## 阶段5 音频与合成

### Task 5.1 — TTS 配音

**目标：** 对白文本 → 语音文件 → SRT 字幕。

**现状：** 系统无 TTS 集成。Seedance 的 `generate_audio` 只能生成环境音，不支持口型。

**实现路径：**

1. 接入火山引擎 TTS 或 Edge TTS（免费）
2. 在剧本阶段提取所有对白 → 逐句合成 WAV
3. 按时间轴生成 SRT
4. 前端视频预览时叠加字幕

**改动清单：**

| 文件 | 改什么 |
|------|--------|
| `server/routes/gen.py` | 新增 `/tts/generate` 端点 |
| `server/routes/gen.py` | 新增 `/tts/export-srt` 端点 |
| `core/tts.py` | **新建** — TTS 封装 |

---

### Task 5.2 — BGM 情绪匹配

**目标：** 根据剧情情绪自动配乐。

**实现路径：**

1. 每集剧情标注情绪值（已有 `mood` 字段可扩展）
2. 预置 BGM 分类（紧张/平静/激昂/悲伤/悬疑）
3. 前端全片预览时叠加 BGM 轨道

**这是长期规划，依赖 Task 5.1 完成后才有意义。**

---

## 推荐执行顺序

```
2.2 → 3.1 → 3.2 → 4.1 → 4.2 → 3.3 → 5.1 → 5.2
 ↑     ↑     ↑     ↑     ↑     ↑     ↑     ↑
 简单  简单  中等  中等  简单  困难  中等  长期
```

**现在可并行：** 2.2 + 3.1 + 3.2（互不依赖）
**下一批：** 4.1 + 4.2（依赖 3.2 完成）
**最后：** 3.3 + 5.1 + 5.2
