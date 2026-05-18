# 视频生成全面重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构视频生成功能，使自由创作参数真实生效，项目模式支持逐镜头预览/编辑/生成，解决镜头一致性

**Architecture:** 前端 VideoGenPage 增强 + 后端 video_producer 重构 + 新增 workspace 视频阶段镜头列表 UI。自由创作独立于项目，项目模式对接第6阶段分镜提示词。

**Tech Stack:** FastAPI (Python) + React (TypeScript) + WebSocket

---

### Task 1: 修复后端 freeVideoGen 支持文生视频和传参

**Files:**
- Modify: `server/routes/gen.py`

- [ ] **Step 1: 查看现有 freeVideoGen 路由代码**

Read `server/routes/gen.py`，找到 `freeVideoGen` 的相关路由，确认当前请求/响应格式。

- [ ] **Step 2: 修改 freeVideoGen 路由支持文生视频**

```python
@router.post("/video-gen/free")
async def free_video_gen(
    prompt: str = Form(...),
    files: list[UploadFile] = File(default=None),
    model: str = Form(default=""),
    resolution: str = Form(default="1280x720"),
    duration: int = Form(default=5),
    generate_audio: bool = Form(default=False),
):
    """自由创作视频生成，支持文生视频和图生视频"""
    from tools.video_api import create_video_backend
    backend = create_video_backend("seedance")

    image_paths = []
    if files:
        for f in files:
            path = TEMP_UPLOAD_DIR / f"{uuid.uuid4()}_{f.filename}"
            content = await f.read()
            path.write_bytes(content)
            image_paths.append(str(path))

    # 文生视频：无图片时调用 text_to_video
    if not image_paths:
        task_id = backend.text_to_video(prompt, resolution, duration, generate_audio)
    else:
        # 图生视频：传首张图片
        task_id = backend.image_to_video(image_paths[0], prompt, resolution, duration, generate_audio)

    video_url = backend.wait_for_result(task_id, timeout=600, poll_interval=10)

    # 清理临时文件
    for p in image_paths:
        try: os.remove(p)
        except: pass

    return {"video_url": video_url, "task_id": task_id}
```

- [ ] **Step 3: 给 SeedanceBackend 添加 text_to_video 方法**

Read `tools/video_api_seedance.py`。

- [ ] **Step 4: 扩展 SeedanceBackend**

```python
def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
    """文生视频"""
    import json
    payload = {
        "model": "doubao-seedance-2-0-260128",
        "prompt": prompt,
        "resolution": resolution,
        "duration": duration,
        "generate_audio": generate_audio,
    }
    headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(self.submit_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result.get("id", "")

def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
    """图生视频，支持参数传递"""
    file_name = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        files = {"image": (file_name, f, "image/png")}
        data = {
            "prompt": prompt,
            "resolution": resolution,
            "duration": str(duration),
            "generate_audio": str(generate_audio).lower(),
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.post(self.submit_url, headers=headers, data=data, files=files, timeout=60)
    resp.raise_for_status()
    result = resp.json()
    return result.get("id", "")
```

- [ ] **Step 5: 更新 VideoBackend 抽象类**

Read `tools/video_api.py`。

- [ ] **Step 6: 给 VideoBackend ABC 添加 text_to_video 抽象方法**

```python
class VideoBackend(ABC):
    @abstractmethod
    def image_to_video(self, image_path: str, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
        ...

    @abstractmethod
    def text_to_video(self, prompt: str, resolution: str = "1280x720", duration: int = 5, generate_audio: bool = False) -> str:
        """Submit text-to-video task, return task_id"""

    @abstractmethod
    def check_status(self, task_id: str) -> dict:
        ...

    @abstractmethod
    def wait_for_result(self, task_id: str, timeout: int = 300, poll_interval: int = 10) -> str:
        ...
```

- [ ] **Step 7: 编译验证**

Run: `python -m py_compile tools/video_api.py && python -m py_compile tools/video_api_seedance.py && python -m py_compile server/routes/gen.py`

### Task 2: 增强前端自由创作页（文生视频+项目图库）

**Files:**
- Modify: `src/pages/VideoGenPage.tsx`
- Modify: `src/lib/api.ts`

- [ ] **Step 1: 添加项目图库获取 API**

```typescript
// src/lib/api.ts 添加
export async function fetchProjectVisualAssets(projectName: string): Promise<{ characters: Record<string, string[]>; scenes: Record<string, string[]> }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(projectName)}/visual-assets`)
  if (!res.ok) return { characters: {}, scenes: {} }
  return res.json()
}

// 修改 freeVideoGen 支持传参数
export async function freeVideoGen(
  prompt: string,
  files?: File[],
  model?: string,
  resolution?: string,
  duration?: number,
  generate_audio?: boolean,
): Promise<{ video_url: string; task_id: string; local?: string; error?: string }> {
  const form = new FormData()
  form.append('prompt', prompt)
  if (model) form.append('model', model)
  if (resolution) form.append('resolution', resolution)
  if (duration) form.append('duration', String(duration))
  if (generate_audio) form.append('generate_audio', 'true')
  if (files) for (const f of files) form.append('files', f)
  const res = await fetch(`${BASE}/video-gen/free`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    return { error: err.detail || '生成失败', task_id: '', video_url: '' }
  }
  return res.json()
}
```

- [ ] **Step 2: 修改 VideoGenPage 自由创作模式**

在 `src/pages/VideoGenPage.tsx` 中：
1. 移除 `const handleFreeGen` 中对 `freeFiles.length === 0` 的限制（允许文生视频）
2. `handleFreeGen` 调用时传入所有参数
3. 添加项目图库选择面板 UI

- [ ] **Step 3: 添加项目选择+图库引用 UI**

```tsx
// 在自由创作模式下，上传图片区域下方添加
const [projects, setProjects] = useState<any[]>([])
const [selectedRefProject, setSelectedRefProject] = useState('')
const [refProjectImages, setRefProjectImages] = useState<{ characters: Record<string, string[]>; scenes: Record<string, string[]> }>({ characters: {}, scenes: {} })

// useEffect 中获取项目列表
fetchProjects().then(setProjects)

// 选中项目后获取视觉素材
useEffect(() => {
  if (!selectedRefProject) return
  fetchProjectVisualAssets(selectedRefProject).then(setRefProjectImages)
}, [selectedRefProject])

// JSX: 放在上传图片区域下面
{/* 项目素材引用 */}
<div className="glass-card rounded-xl p-4 mb-4">
  <label className="text-xs font-medium text-muted-foreground mb-2 block">📂 引用项目素材</label>
  <select value={selectedRefProject} onChange={e => setSelectedRefProject(e.target.value)}
    className="w-full bg-muted border border-border rounded-xl px-3 py-2 text-xs mb-3">
    <option value="">-- 不引用 --</option>
    {projects.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
  </select>
  {Object.keys(refProjectImages.characters).length > 0 && (
    <div className="mb-2">
      <p className="text-[10px] text-muted-foreground mb-1">角色</p>
      <div className="flex flex-wrap gap-2">
        {Object.entries(refProjectImages.characters).map(([name, urls]) =>
          urls.map((url, i) => (
            <img key={`${name}-${i}`} src={url} alt={name}
              className="w-12 h-12 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50"
              onClick={() => { /* 添加到参考图列表 */ }} title={name} />
          ))
        )}
      </div>
    </div>
  )}
  {Object.keys(refProjectImages.scenes).length > 0 && (
    <div>
      <p className="text-[10px] text-muted-foreground mb-1">场景</p>
      <div className="flex flex-wrap gap-2">
        {Object.entries(refProjectImages.scenes).map(([name, urls]) =>
          urls.map((url, i) => (
            <img key={`${name}-${i}`} src={url} alt={name}
              className="w-12 h-12 object-contain rounded-lg bg-muted border border-border cursor-pointer hover:ring-2 hover:ring-primary/50"
              onClick={() => { /* 添加到参考图列表 */ }} title={name} />
          ))
        )}
      </div>
    </div>
  )}
</div>
```

- [ ] **Step 4: 添加音频开关 UI**

```tsx
// 在时长选择器后面或旁边
const [generateAudio, setGenerateAudio] = useState(false)

{/* 在分辨率/时长那行添加 */}
<div className="flex items-center gap-2">
  <label className="relative inline-flex items-center cursor-pointer">
    <input type="checkbox" className="sr-only peer" checked={generateAudio} onChange={e => setGenerateAudio(e.target.checked)} />
    <div className="w-9 h-5 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
  </label>
  <span className="text-xs text-muted-foreground">生成音频</span>
</div>
```

- [ ] **Step 5: 编译验证**

Run: `npm run build`

### Task 3: 分镜脚本写入机位信息

**Files:**
- Modify: `agents/storyboarder.py`
- Modify: `prompts/storyboarder.txt`

- [ ] **Step 1: 修改 storyboarder prompt**

在 `prompts/storyboarder.txt` 中，每个镜头的输出格式增加「机位」字段：

```markdown
镜头编号 | 时长 | 景别变化 | 镜头焦段 | 运镜方式 | 机位
转场方式  ➜  下个镜头编号

（一段叙事文字…）

"完整对白。"

➜ 下个镜头
---
附注：[灯光/色彩/特殊说明]
```

在 prompt 描述中增加：

```markdown
【机位标注规则】
机位描述用自然语言标注摄像机在场景中的位置和视角：
- "人物正面，视线平齐" 
- "人物左侧45°，略俯拍"
- "人物正后方，过肩拍"
- "天花板俯角，垂直向下"
- "人物右侧，水平跟拍"

机位标注用于判断相邻镜头是否同机位：
- 同机位 + 同场景 → 可为首尾帧衔接（连续拍摄）
- 不同机位/切机位 → 不能用首尾帧（需多模态参考）
```

- [ ] **Step 2: 编译验证**

Run: `python -m py_compile agents/storyboarder.py`

### Task 4: 项目模式新界面 — 镜头列表面板

**Files:**
- Create: `src/components/ShotListView.tsx`
- Modify: `src/pages/Workspace.tsx`

- [ ] **Step 1: 创建 ShotListView 组件**

```tsx
// src/components/ShotListView.tsx
import { useState, useEffect } from 'react'
import { Play, Check, X, Loader2, Pencil, RefreshCw, Sparkles } from 'lucide-react'

export interface Shot {
  index: number
  act: string      // "第一幕" / "第1集"
  scene: string    // "第3场"
  prompt: string   // 完整的分镜提示词
  status: 'pending' | 'generating' | 'done' | 'failed'
  videoUrl?: string
  error?: string
}

interface Props {
  shots: Shot[]
  onGenerateAll: () => void
  onGenerateOne: (index: number) => void
  onRegenerate: (index: number) => void
  onEditPrompt: (index: number, newPrompt: string) => void
  onExport: (index: number) => void
  onConcat: () => void
}

export default function ShotListView({
  shots, onGenerateAll, onGenerateOne, onRegenerate,
  onEditPrompt, onExport, onConcat,
}: Props) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editText, setEditText] = useState('')

  // Group shots by act
  const groups: Record<string, Shot[]> = {}
  for (const s of shots) {
    if (!groups[s.act]) groups[s.act] = []
    groups[s.act].push(s)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <button onClick={onGenerateAll} className="btn-gradient flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium">
          <Sparkles className="w-4 h-4" /> 全部生成
        </button>
        <button onClick={onConcat} className="px-5 py-2.5 rounded-xl border border-border text-sm hover:bg-muted transition-colors">
          拼接成片
        </button>
        <span className="text-xs text-muted-foreground ml-2">
          已生成 {shots.filter(s => s.status === 'done').length}/{shots.length}
        </span>
      </div>

      {Object.entries(groups).map(([act, actShots]) => (
        <div key={act} className="glass-card rounded-2xl p-4">
          <h3 className="text-sm font-semibold mb-3">{act}</h3>
          <div className="space-y-2">
            {actShots.map(shot => (
              <div key={shot.index}
                className={`p-3 rounded-xl border transition-all ${getStatusBorder(shot.status)}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-muted-foreground">{shot.scene}</span>
                      <span className="text-xs text-muted-foreground">镜头{shot.index}</span>
                      {renderStatusBadge(shot.status)}
                    </div>
                    {editingIndex === shot.index ? (
                      <textarea className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-xs h-20 resize-none"
                        value={editText} onChange={e => setEditText(e.target.value)} autoFocus />
                    ) : (
                      <p className="text-xs text-muted-foreground line-clamp-2">{shot.prompt}</p>
                    )}
                    {shot.error && <p className="text-xs text-red-400 mt-1">❌ {shot.error}</p>}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {shot.videoUrl && (
                      <video src={shot.videoUrl} className="w-16 h-12 object-cover rounded-lg" />
                    )}
                    {editingIndex === shot.index ? (
                      <>
                        <button onClick={() => { onEditPrompt(shot.index, editText); setEditingIndex(null) }}
                          className="p-1.5 rounded-lg bg-primary/20 text-primary text-xs">保存</button>
                        <button onClick={() => setEditingIndex(null)}
                          className="p-1.5 rounded-lg border border-border text-xs">取消</button>
                      </>
                    ) : (
                      <>
                        {shot.status === 'pending' && (
                          <button onClick={() => onGenerateOne(shot.index)}
                            className="p-1.5 rounded-lg border border-border hover:bg-muted" title="生成">
                            <Play className="w-3 h-3" />
                          </button>
                        )}
                        {shot.status === 'done' && (
                          <button onClick={() => onRegenerate(shot.index)}
                            className="p-1.5 rounded-lg border border-border hover:bg-muted" title="重新生成">
                            <RefreshCw className="w-3 h-3" />
                          </button>
                        )}
                        {shot.status === 'failed' && (
                          <button onClick={() => onGenerateOne(shot.index)}
                            className="p-1.5 rounded-lg border border-red-400/30 text-red-400" title="重试">
                            <RefreshCw className="w-3 h-3" />
                          </button>
                        )}
                        <button onClick={() => { setEditingIndex(shot.index); setEditText(shot.prompt) }}
                          className="p-1.5 rounded-lg border border-border hover:bg-muted" title="编辑提示词">
                          <Pencil className="w-3 h-3" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function getStatusBorder(status: string): string {
  switch (status) {
    case 'done': return 'border-green-400/30 bg-green-400/5'
    case 'generating': return 'border-primary/30 bg-primary/5 animate-pulse'
    case 'failed': return 'border-red-400/30 bg-red-400/5'
    default: return 'border-border'
  }
}

function renderStatusBadge(status: string) {
  switch (status) {
    case 'done': return <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-400/10 text-green-400">✅ 已生成</span>
    case 'generating': return <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary"><Loader2 className="w-2.5 h-2.5 inline animate-spin" /> 生成中</span>
    case 'failed': return <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-400/10 text-red-400">❌ 失败</span>
    default: return <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">待生成</span>
  }
}
```

- [ ] **Step 2: 在 Workspace.tsx 中集成镜头列表**

在 Workspace.tsx 的 `selectedPhase === 7` 条件下渲染 `ShotListView`，替代现有的简单视频播放：

```tsx
// 在 Workspace.tsx 顶部引入
import ShotListView from '../components/ShotListView'
import type { Shot } from '../components/ShotListView'

// 添加状态
const [shots, setShots] = useState<Shot[]>([])

// 读取分镜提示词转为镜头列表
const loadShots = async () => {
  if (!name) return
  // 从 06_提示词 读取分镜提示词文件，拆分为镜头列表
  const prompts = await fetchPhaseContent(name, '06_提示词/分镜提示词.md')
  // 解析成 Shot[]
  // ...
}

useEffect(() => {
  if (selectedPhase === 7) loadShots()
}, [selectedPhase])
```

- [ ] **Step 3: 替换渲染**

```tsx
// 将原来的 selectedPhase === 7 渲染区替换
{selectedPhase === 7 ? (
  <ShotListView
    shots={shots}
    onGenerateAll={handleGenerateAll}
    onGenerateOne={handleGenerateShot}
    onRegenerate={handleRegenerateShot}
    onEditPrompt={handleEditShotPrompt}
    onExport={handleExportShot}
    onConcat={handleConcatShots}
  />
) : ...}
```

### Task 5: 后端视频生成管线 — 多模态参考+连续性判定

**Files:**
- Modify: `server/routes/workspace.py`
- Modify: `tools/video_api.py`
- Modify: `tools/video_api_seedance.py`

- [ ] **Step 1: 添加交互式镜头生成 API**

```python
# server/routes/workspace.py 添加
@router.post("/projects/{project_name}/video/shots/generate")
async def generate_shot(
    project_name: str,
    shot_index: int = Form(...),
    custom_prompt: str = Form(default=""),
):
    """生成指定镜头视频，带多模态参考"""
    from tools.video_api import create_video_backend
    backend = create_video_backend("seedance")

    project = ProjectManager(project_name)

    # 1. 读取分镜提示词
    prompt = custom_prompt or read_shot_prompt(project, shot_index)

    # 2. 读取视觉素材（角色+场景图）
    char_dir = project.project_dir / "07_视觉素材" / "角色"
    scene_dir = project.project_dir / "07_视觉素材" / "场景"
    
    # 3. 收集参考图（最多9张）
    ref_images = []
    if scene_dir.exists():
        for f in sorted(scene_dir.glob("*.png"))[:5]:
            ref_images.append(str(f))
    if char_dir.exists():
        for f in sorted(char_dir.glob("*.png"))[:4]:
            ref_images.append(str(f))

    # 4. 获取上一镜头的尾帧（如果有且同机位）
    last_shot_video = find_last_shot_video(project, shot_index)
    
    # 5. 提交生成
    if ref_images:
        task_id = backend.image_to_video(ref_images[0], prompt)
    else:
        task_id = backend.text_to_video(prompt)

    video_url = backend.wait_for_result(task_id, timeout=600)

    # 6. 保存视频
    shot_info = parse_shot_info(project, shot_index)
    save_path = project.project_dir / "08_视频" / "片段" / f"{shot_info['act']}_{shot_info['scene']}_镜头{shot_index:03d}.mp4"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    download_video(video_url, str(save_path))

    return {"shot_index": shot_index, "video_url": video_url, "local_path": str(save_path)}
```

- [ ] **Step 2: 添加批量生成和辅助函数**

```python
# server/routes/workspace.py 添加

def read_shot_prompt(project, shot_index: int) -> str:
    """从项目读取指定镜头的分镜提示词"""
    prompts_dir = project.project_dir / "06_提示词"
    files = sorted(prompts_dir.glob("分镜提示词*.md"))
    for f in files:
        content = f.read_text(encoding="utf-8")
        # 查找 ### 镜头N 或 镜头N 标记
        import re
        if shot_index <= 10:
            markers = [f"镜头{shot_index}", f"### 镜头{shot_index}"]
            for m in markers:
                idx = content.find(m)
                if idx >= 0:
                    return content[idx:idx+500]
    return ""

def find_last_shot_video(project, shot_index: int) -> str | None:
    """查找上一个镜头的视频文件"""
    clip_dir = project.project_dir / "08_视频" / "片段"
    if not clip_dir.exists():
        return None
    prev_index = shot_index - 1
    files = sorted(clip_dir.glob(f"*_镜头{prev_index:03d}.mp4"))
    return str(files[0]) if files else None

def download_video(url: str, save_path: str):
    import requests
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)

@router.post("/projects/{project_name}/video/shots/generate-all")
async def generate_all_shots(project_name: str):
    """批量生成所有未完成镜头"""
    project = ProjectManager(project_name)

    # 读取分镜提示词，统计镜头数
    prompts_dir = project.project_dir / "06_提示词"
    all_prompts = ""
    for f in sorted(prompts_dir.glob("分镜提示词*.md")):
        all_prompts += f.read_text(encoding="utf-8")
    shot_count = all_prompts.count("### 镜头") or all_prompts.count("---") // 2 or 1

    return {"shot_count": shot_count, "message": "请通过 WebSocket 逐个生成镜头"}
```

- [ ] **Step 3: 添加镜头状态查询 API**

```python
@router.get("/projects/{project_name}/video/shots/status")
async def get_shots_status(project_name: str):
    """返回每个镜头的生成状态"""
    status_path = ProjectManager(project_name).project_dir / "08_视频" / "状态.json"
    if status_path.exists():
        return json.loads(status_path.read_text(encoding="utf-8"))
    return {"shots": []}
```

### Task 6: 分镜提示词解析 + 镜头列表加载

**Files:**
- Modify: `src/pages/Workspace.tsx`
- Create: `src/lib/shot-parser.ts`

- [ ] **Step 1: 创建分镜提示词解析器**

```typescript
// src/lib/shot-parser.ts
import type { Shot } from '../components/ShotListView'
import { fetchPhaseContent } from './api'

export async function loadShotsFromPrompts(projectName: string): Promise<Shot[]> {
  const content = await fetchPhaseContent(projectName, '06_提示词/分镜提示词.md')
  if (!content) return []

  const shots: Shot[] = []
  // 解析格式：
  // # 第一幕 分镜提示词
  // ### 镜头1
  // ... prompt ...
  // ---
  // ### 镜头2
  // ... prompt ...

  let currentAct = ''
  let currentScene = ''
  const actRegex = /^#\s+(第[^场\n]+)/m
  const shotRegex = /^###\s+(镜头\d+|第\d+场.*)/m
  const divider = /\n---\n/

  // 按标题拆分
  const blocks = content.split(divider)
  for (const block of blocks) {
    const actMatch = block.match(actRegex)
    if (actMatch) currentAct = actMatch[1].trim()

    const shotMatch = block.match(shotRegex)
    if (shotMatch) {
      shots.push({
        index: shots.length + 1,
        act: currentAct,
        scene: shotMatch[1].trim(),
        prompt: block.trim(),
        status: 'pending',
      })
    }
  }

  // 如果没有解析出镜头，把整个内容当一条
  if (shots.length === 0 && content.trim()) {
    shots.push({
      index: 1,
      act: '全部',
      scene: '',
      prompt: content.trim(),
      status: 'pending',
    })
  }

  return shots
}
```

- [ ] **Step 2: 集成到 Workspace.tsx**

在 `Workspace.tsx` 中添加 `loadShots` 调用和 handle 函数。

### Task 7: 导出与拼接功能

**Files:**
- Modify: `src/pages/Workspace.tsx`
- Modify: `server/routes/workspace.py`

- [ ] **Step 1: 添加拼接 API**

```python
@router.post("/projects/{project_name}/video/concat")
async def concat_videos(project_name: str):
    """拼接所有已生成的镜头视频"""
    from tools.video_concat import VideoConcat
    import shutil
    project = ProjectManager(project_name)
    clips_dir = project.project_dir / "08_视频" / "片段"
    output_path = project.project_dir / "08_视频" / "成片.mp4"

    video_files = sorted(clips_dir.glob("*.mp4"))
    if not video_files:
        return {"error": "无视频片段"}

    if len(video_files) == 1:
        shutil.copy2(str(video_files[0]), str(output_path))
    else:
        VideoConcat.concat([str(f) for f in video_files], str(output_path))

    return {"output": str(output_path)}
```

- [ ] **Step 2: 添加下载单个镜头 API**

```python
@router.get("/projects/{project_name}/video/shots/{shot_index}/download")
async def download_shot(project_name: str, shot_index: int):
    """返回镜头视频文件"""
    project = ProjectManager(project_name)
    files = sorted((project.project_dir / "08_视频" / "片段").glob(f"*_镜头{shot_index:03d}.*"))
    if not files:
        raise HTTPException(404, "未找到镜头视频")
    return FileResponse(str(files[0]))
```

### Task 8: 音频参考管线

**Files:**
- Modify: `server/routes/workspace.py`
- Create: `tools/audio_extractor.py`

- [ ] **Step 1: 创建音频提取工具**

```python
# tools/audio_extractor.py
"""从角色对白中提取音频参考"""

def extract_first_dialogue(project, character_name: str) -> str | None:
    """提取角色第一句对白作为音频参考"""
    from core.visual_bible import VisualBibleExtractor
    script_dir = project.project_dir / "03_完整剧本"
    
    script_files = sorted(script_dir.glob("完整剧本*.md"))
    content = ""
    for f in script_files:
        content += f.read_text(encoding="utf-8")

    # 找到角色的第一句对白
    pattern = re.compile(rf'{re.escape(character_name)}\s*\n\s*（.*?）\s*\n\s*"([^"]+)"', re.MULTILINE)
    match = pattern.search(content)
    if match:
        return match.group(1)
    return None

def list_audio_references(project):
    """列出项目中可用的角色音频参考"""
    characters_dir = project.project_dir / "07_视觉素材" / "角色音频"
    if not characters_dir.exists():
        return []
    refs = []
    for f in sorted(characters_dir.glob("*.wav")) + sorted(characters_dir.glob("*.mp3")):
        refs.append({"file": str(f.name), "character": f.stem})
    return refs
```

- [ ] **Step 2: 在生成镜头时传递音频参考**

在 `generate_shot` API 中，如果角色有参考音频，连同角色定妆照一起传给后端。

### Task 9: 编译与集成验证

- [ ] **Step 1: 全量编译**

Run: `python -m py_compile server/routes/gen.py server/routes/workspace.py tools/video_api.py tools/video_api_seedance.py tools/audio_extractor.py agents/storyboarder.py`

Run: `npm run build`

- [ ] **Step 2: 验证自由创作模式**

1. 启动服务器
2. 进入 `/video-gen` 自由创作
3. 不传图片，只写 prompt → 文生视频应有返回
4. 传参（分辨率、时长、音频）应生效
5. 项目图库面板应可浏览

- [ ] **Step 3: 验证项目模式**

1. 进入已完成项目的工作区，第8阶段
2. 应显示镜头列表
3. 点击单个镜头生成
4. 查看进度和结果
