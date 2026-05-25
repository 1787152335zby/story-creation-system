# 角色提示词分层 & 风格系统 & 参考图标签化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 角色提示词拆分为 L1 定妆照 + L2 道具资产；自动适配画风选具体风格；参考图四标签页 UI 按类型分组处理。

**Architecture:** 后端新增 `prop-prompt` 和 `analyze-style-reference` 端点，改造 `generate_character_prompt` 支持 mode 参数，`style_config.py` 新增自动适配规则。前端 `ReferenceImageUploader` 改为四标签页，`ProjectImageGenForm` 新增道具区块。gen.py 按参考图类型分组注入 prompt 前缀。

**Tech Stack:** Python 3.12 (FastAPI), React + TypeScript, TailwindCSS

---

### Task 1: 类型定义 — ReferenceUrlsByType

**Files:**
- Modify: `src/lib/types.ts` (在 EntityImagesMap 之后追加)

- [ ] **Step 1: 添加 ReferenceUrlsByType 接口**

```typescript
export interface ReferenceUrlsByType {
  style: string[]
  character: string[]
  scene: string[]
  prop: string[]
}

export interface AnalyzeStyleResult {
  render_style: string
  tone: string
  material: string
  proportion: string
  raw_keywords: string
}
```

追加到 `src/lib/types.ts` 末尾（`AssetLibrary` 之后）。

- [ ] **Step 2: 构建验证**

Run: `$env:Path = "C:\Program Files\nodejs;$env:Path"; npm run build 2>&1 | select -Last 3`
Expected: `✓ built in ...`

- [ ] **Step 3: Commit**

```bash
git add src/lib/types.ts
git commit -m "feat: add ReferenceUrlsByType and AnalyzeStyleResult types"
```

---

### Task 2: API 层 — 新增两个调用函数

**Files:**
- Modify: `src/lib/api.ts` (在 fetchSceneConfirmedImages 之后追加)

- [ ] **Step 1: 添加 analyzeStyleReference 和 fetchPropPrompt**

```typescript
export async function analyzeStyleReference(projectName: string, file: File): Promise<import('./types').AnalyzeStyleResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(projectName)}/analyze-style-reference`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('风格分析失败')
  return res.json()
}

export async function fetchPropPrompt(projectName: string, characterName: string, propName: string): Promise<{ prompt: string; character_name: string }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(projectName)}/prop-prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_name: characterName, prop_name: propName }),
  })
  if (!res.ok) return { prompt: '', character_name: characterName }
  return res.json()
}
```

插入到 `fetchSceneConfirmedImages` 函数后面（[api.ts#L579](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/src/lib/api.ts#L579) 附近）。

- [ ] **Step 2: 更新 freeImageGen 支持 reference_urls_by_type**

找到 `freeImageGen`（[api.ts#L224](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/src/lib/api.ts#L224-L228)）并修改 body：

```typescript
export async function freeImageGen(prompt: string, negativePrompt: string = '', size: string = '1024x1024', n: number = 1, model: string = '', referenceUrls: string[] = [], referenceUrlsByType?: import('./types').ReferenceUrlsByType, extraParams: Record<string, unknown> = {}): Promise<FreeImageResult> {
  const body: Record<string, unknown> = { prompt, negative_prompt: negativePrompt, size, n, model, reference_urls: referenceUrls, extra_params: extraParams }
  if (referenceUrlsByType) {
    body.reference_urls_by_type = referenceUrlsByType
  }
  const res = await fetch(`${BASE}/image-gen/free`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  // ... rest unchanged
```

- [ ] **Step 3: 更新 projectImageGen 支持 reference_urls_by_type**

找到 `projectImageGen` 调用处，同样在 `api.ts` 里添加 `reference_urls_by_type` 参数。

- [ ] **Step 4: 构建验证**

Run: `npm run build`

- [ ] **Step 5: Commit**

```bash
git add src/lib/api.ts
git commit -m "feat: add analyzeStyleReference, fetchPropPrompt API calls"
```

---

### Task 3: PromptBuilder — L1/L2 分层

**Files:**
- Modify: `agents/prompt_factory.py` (第 85-120 行)

- [ ] **Step 1: 改造 generate_character_prompt 支持 mode 参数**

替换 [prompt_factory.py#L85-L120](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/agents/prompt_factory.py#L85-L120)：

```python
@staticmethod
def generate_character_prompt(char: dict, style_decl: str = "", mode: str = "all") -> str:
    """mode: 'base' = L1定妆照, 'prop' = L2道具(需prop_name), 'all' = 旧版全合一"""
    type_tag = "主要角色" if char.get("type") == "main" else "次要角色"
    is_variant = not char.get("is_base", True)
    char_name = char.get("character_base", char["name"])
    variant_name = char.get("variant_name", "基础形象")

    if is_variant:
        parts = [f"'{char_name}' 的变体形象「{variant_name}」，{type_tag}。"]
        if char.get("based_on"):
            parts.append(f"基于{char['based_on']}，在以下基础上发生了变化：")
        if char.get("appearance_change"):
            parts.append(f"外貌变化：{char['appearance_change']}。")
        if char.get("clothing_change"):
            parts.append(f"服装变化：{char['clothing_change']}。")
        if char.get("trigger_event"):
            parts.append(f"变化原因：{char['trigger_event']}。")
        parts.append("动态场景中展示该变化，非定妆照。")
    elif mode == "base":
        parts = [f"'{char_name}' 的定妆照，{type_tag}。"]
        if char.get("appearance"):
            parts.append(f"外貌特征：{char['appearance']}。")
        if char.get("clothing"):
            parts.append(f"服装：{char['clothing']}。")
        if char.get("age"):
            parts.append(f"年龄：{char['age']}。")
        if char.get("gender"):
            parts.append(f"性别：{char['gender']}。")
        if char.get("key_features"):
            parts.append(f"标志性特征：{'、'.join(char['key_features'])}。")
        parts.append("纯白背景，角色居中，全身照，自然站立姿态，无动作，无手持物品。")
    elif mode == "prop":
        prop_name = char.get("_prop_name", "")
        parts = [f"'{prop_name}' — {char_name}的配饰道具。"]
        parts.append("白色背景，产品展示角度，高清细节。")
    else:
        parts = [f"'{char_name}' 的定妆照，{type_tag}。"]
        if char.get("appearance"):
            parts.append(f"外貌特征：{char['appearance']}。")
        if char.get("clothing"):
            parts.append(f"服装：{char['clothing']}。")
        if char.get("expression"):
            parts.append(f"表情/神态：{char['expression']}。")
        if char.get("pose"):
            parts.append(f"姿态：{char['pose']}。")
        if char.get("accessories"):
            parts.append(f"配饰：{'、'.join(char['accessories'])}。")
        if char.get("key_features"):
            parts.append(f"标志性特征：{'、'.join(char['key_features'])}。")
        parts.append("纯白背景，角色居中，全身照。")
    return " ".join(parts)
```

- [ ] **Step 2: Python 语法验证**

Run: `python -c "import py_compile; py_compile.compile('agents/prompt_factory.py', doraise=True); print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add agents/prompt_factory.py
git commit -m "feat: add mode param to generate_character_prompt for L1 base / L2 prop"
```

---

### Task 4: auto_style 自动适配规则

**Files:**
- Modify: `core/style_config.py` (在 `RENDER_STYLES` 定义之后)

- [ ] **Step 1: 添加 resolve_art_style 方法**

在 [style_config.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/core/style_config.py#L173) 的 `from_mapping` 之后追加：

```python
    def resolve_art_style(self) -> str:
        """当 art_style=='7' (自动适配) 时，根据 genre 匹配具体画风。"""
        if self.art_style != "7":
            return self.art_style
        rules = {
            ("科幻",): "3",
            ("奇幻",): "3",
            ("悬疑",): "1",
            ("剧情",): "1",
            ("动作",): "1",
            ("日韩生活",): "2",
            ("治愈",): "2",
            ("日常",): "2",
            ("古装",): "5",
            ("仙侠",): "5",
            ("国风",): "5",
            ("爱情",): "1",
            ("喜剧",): "4",
        }
        keywords = [k.strip() for k in self.genre.replace("，", ",").split(",") if k.strip()]
        for rule_tags, style_id in rules.items():
            for kw in keywords:
                if kw in rule_tags:
                    return style_id
        return "1"

    def resolve_render_style_name(self) -> str:
        """返回 resolved 的画风名称（用于 UI）。"""
        resolved = self.resolve_art_style()
        return RENDER_STYLES.get(resolved, {}).get("name", "写实/真人")
```

- [ ] **Step 2: 修改 prompt_factory.py 的 _build_style_declaration**

修改 `_build_style_declaration`（[prompt_factory.py](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/agents/prompt_factory.py) 大约 L11-28），使其调用 `resolve_render_style_name`：

```python
def _build_style_declaration(style: StyleConfig) -> str:
    visual_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "自动适配")
    aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
    render_name = style.resolve_render_style_name()  # 改为自动解析
    auto_suffix = ""
    if style.art_style == "7":
        story_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
        auto_suffix = f"（由「自动适配」根据故事类型「{style.genre}」自动选择）"

    decl = f"""【整体视觉风格声明】
此风格声明适用于以下所有角色、场景和镜头的提示词生成：
- 故事类型：{STORY_TYPES.get(style.story_type, {}).get("name", "未知")}
- 视觉风格：{visual_name}
- 画面比例：{aspect_name}
- 渲染风格：{render_name}{auto_suffix}
"""
    if style.custom_requirements:
        decl += f"- 自定义要求：{style.custom_requirements[:200]}\n"
    return decl
```

- [ ] **Step 3: Python 验证**

Run: `python -c "import py_compile; py_compile.compile('core/style_config.py', doraise=True); py_compile.compile('agents/prompt_factory.py', doraise=True); print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add core/style_config.py agents/prompt_factory.py
git commit -m "feat: add auto art style resolution by genre rules"
```

---

### Task 5: 后端新建两个端点（prop-prompt + analyze-style-reference）

**Files:**
- Modify: `server/routes/projects.py` (末尾追加)

- [ ] **Step 1: 添加 prop-prompt 端点**

在 `projects.py` 末尾追加（`get_scene_confirmed_images` 之后）：

```python
@router.post("/projects/{name}/prop-prompt")
def get_prop_prompt(name: str, body: dict):
    """为指定角色的指定配饰生成道具提示词"""
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    from agents.prompt_factory import PromptBuilder

    project = ProjectManager(name)
    char_name = body.get("character_name", "")
    prop_name = body.get("prop_name", "")
    chars = VisualBibleExtractor.list_characters(project)
    char = next((c for c in chars if c["name"] == char_name), None)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    char["_prop_name"] = prop_name
    prompt = PromptBuilder.generate_character_prompt(char, mode="prop")
    return {"prompt": prompt, "character_name": char_name}
```

- [ ] **Step 2: 添加 analyze-style-reference 端点**

继续追加：

```python
@router.post("/projects/{name}/analyze-style-reference")
async def analyze_style_reference(name: str, file: UploadFile = File(...)):
    """用 Gemini 多模态分析上传的参考图，提取画风特征"""
    from core.project_manager import ProjectManager
    import base64 as b64

    project = ProjectManager(name)
    image_bytes = await file.read()
    image_b64 = b64.b64encode(image_bytes).decode()

    # 复用聚合平台配置
    from .gen import _get_active_agg_config
    agg = _get_active_agg_config("image")
    if not agg or not agg.get("api_key"):
        raise HTTPException(status_code=400, detail="未配置图片 API Key")

    analysis_prompt = (
        "分析这张图片的视觉风格特征。请按以下 JSON 格式返回（只返回 JSON，不要其他内容）：\n"
        '{"render_style":"编号","tone":"色调描述","material":"材质描述","proportion":"角色比例","raw_keywords":"关键词"}\n\n'
        'render_style 编号：1=写实/真人, 2=2D动画, 3=3D CG, 4=卡通/风格化, 5=水墨/国风, 6=像素/复古\n'
        'tone: 颜色体系和光影风格\n'
        'material: 材质质感描述\n'
        'proportion: 如果有角色，描述头部比例、身体比例特征；如果没有角色，填"不适用"\n'
        'raw_keywords: 完整的英文逗号分隔视觉关键词'
    )

    try:
        import requests
        messages = [
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                {"type": "text", "text": analysis_prompt}
            ]}
        ]
        resp = requests.post(
            f"{agg.get('base_url','').rstrip('/')}/v1/chat/completions",
            headers={"Authorization": f"Bearer {agg['api_key']}", "Content-Type": "application/json"},
            json={"model": agg.get("model", "gemini-2.0-flash-exp"), "messages": messages, "max_tokens": 500},
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        import json as _json
        result = _json.loads(content)
    except Exception:
        result = {
            "render_style": "1",
            "tone": "",
            "material": "",
            "proportion": "",
            "raw_keywords": ""
        }

    project.config["analyzed_style"] = result
    project.save_config()
    return result
```

需要确认文件头部有 `from fastapi import UploadFile, File` 和 `from fastapi import HTTPException`。

- [ ] **Step 3: Python 验证**

Run: `python -c "import py_compile; py_compile.compile('server/routes/projects.py', doraise=True); print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add server/routes/projects.py
git commit -m "feat: add prop-prompt and analyze-style-reference endpoints"
```

---

### Task 6: gen.py — 参考图按类型分组处理 + 风格注入

**Files:**
- Modify: `server/routes/gen.py` (FreeImageRequest 模型、_call_image_api)

- [ ] **Step 1: 扩展 FreeImageRequest 支持 reference_urls_by_type**

在 [gen.py#L88-L96](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/routes/gen.py#L88-L96) 后追加：

```python
class FreeImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    size: str = "1024x1024"
    n: int = 1
    model: str = ""
    reference_url: str = ""
    reference_urls: list[str] = []
    reference_urls_by_type: dict = {}
    extra_params: dict = {}
```

- [ ] **Step 2: 在 _call_image_api 中按类型分组处理参考图**

修改 [gen.py#L262-L265](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/routes/gen.py#L262-L265)：

```python
    reference_url = getattr(req, "reference_url", "") or ""
    reference_urls = getattr(req, "reference_urls", []) or []
    reference_urls_by_type = getattr(req, "reference_urls_by_type", {}) or {}
    if reference_url and not reference_urls:
        reference_urls = [reference_url]

    # 向后兼容：reference_urls 降级为 character 类型
    if reference_urls and not reference_urls_by_type:
        reference_urls_by_type = {"character": list(reference_urls)}
    # 合并 reference_urls_by_type 的所有 URL
    if reference_urls_by_type:
        all_typed = []
        for k in ("character", "scene", "prop"):
            all_typed.extend(reference_urls_by_type.get(k, []))
        reference_urls = all_typed
```

在 Gemini 路径（[gen.py#L304-L325](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/routes/gen.py#L304-L325)），给用户文本加类型前缀。找到 `user_text = per_prompt`（约 L336-L339），改为：

```python
                if reference_content_parts:
                    messages.append({"role": "user", "content": reference_content_parts})
                    prefix = ""
                    if reference_urls_by_type.get("character"):
                        prefix += "【人物参考图】请保持以上人物外貌、服装和角色比例特征。\n"
                    if reference_urls_by_type.get("scene"):
                        prefix += "【场景参考图】请保持以上场景空间结构和光影风格。\n"
                    if reference_urls_by_type.get("prop"):
                        prefix += "【道具参考图】请参考以上道具造型和材质。\n"
                    user_text = (prefix + per_prompt) if prefix else per_prompt
                    if negative:
                        user_text = f"{user_text}\n\n避免：{negative}"
                    messages.append({"role": "user", "content": user_text})
```

- [ ] **Step 3: 风格关键词注入**

在 `_call_image_api` 中、`prompt = req.prompt` 之后（[gen.py#L258](file:///e:/AI/Trae%20CN/book/story-creation-system1.2/server/routes/gen.py#L258)），注入 analyzed_style：

```python
    prompt = req.prompt
    # 注入已分析的风格关键词（来自画风参考图或自动适配）
    project_name = getattr(req, "project_name", "") or ""
    analyzed_style = extra_params.get("analyzed_style") or {}
    if analyzed_style:
        tone = analyzed_style.get("tone", "")
        material = analyzed_style.get("material", "")
        proportion = analyzed_style.get("proportion", "")
        inj_parts = []
        if tone:
            inj_parts.append(f"色调：{tone}")
        if material:
            inj_parts.append(f"材质：{material}")
        if proportion and "不适用" not in str(proportion):
            inj_parts.append(f"角色比例：{proportion}")
        if inj_parts:
            prompt = f"{prompt}\n\n风格约束（来自画风参考）：{'，'.join(inj_parts)}。"
```

- [ ] **Step 4: Python 验证**

Run: `python -c "import py_compile; py_compile.compile('server/routes/gen.py', doraise=True); print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add server/routes/gen.py
git commit -m "feat: group reference urls by type in image gen + style injection"
```

---

### Task 7: ReferenceImageUploader — 四标签页改造

**Files:**
- Modify: `src/components/ReferenceImageUploader.tsx`

- [ ] **Step 1: 重写 props 和组件**

用以下完整代码替换整个文件：

```tsx
import { useRef, useState, useCallback } from 'react'
import { Loader2, ImagePlus, X, Link, History, Image as ImageIcon } from 'lucide-react'
import { uploadReferenceImage, fetchGenerationHistory } from '../lib/api'
import type { ReferenceUrlsByType } from '../lib/types'

type RefTab = 'character' | 'scene' | 'prop' | 'style'

interface ReferenceImageUploaderProps {
  urls: ReferenceUrlsByType
  onChange: (urls: ReferenceUrlsByType) => void
}

const TAB_LABELS: Record<RefTab, string> = { style: '🎨 画风', character: '👤 人物', scene: '🏠 场景', prop: '🔧 道具' }

export default function ReferenceImageUploader({ urls, onChange }: ReferenceImageUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [activeTab, setActiveTab] = useState<RefTab>('character')
  const [urlInput, setUrlInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [historyImages, setHistoryImages] = useState<{ name: string; url: string }[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  const currentUrls = urls[activeTab]

  const openHistory = useCallback(async () => {
    setShowHistory(true)
    setLoadingHistory(true)
    try {
      const h = await fetchGenerationHistory()
      const all = [...(h.images_free || []), ...(h.images_project || [])]
      setHistoryImages(all)
    } catch {
    } finally {
      setLoadingHistory(false)
    }
  }, [])

  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setUploading(true)
    try {
      const uploadedUrls: string[] = []
      for (let i = 0; i < files.length; i++) {
        const url = await uploadReferenceImage(files[i])
        uploadedUrls.push(url)
      }
      onChange({ ...urls, [activeTab]: [...currentUrls, ...uploadedUrls] })
    } catch {
    } finally {
      setUploading(false)
    }
  }, [urls, activeTab, currentUrls, onChange])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFileSelect(e.dataTransfer.files)
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }, [])

  const handleUrlAdd = useCallback(() => {
    const trimmed = urlInput.trim()
    if (!trimmed) return
    if (currentUrls.includes(trimmed)) return
    onChange({ ...urls, [activeTab]: [...currentUrls, trimmed] })
    setUrlInput('')
  }, [urlInput, urls, activeTab, currentUrls, onChange])

  const handleUrlKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') { e.preventDefault(); handleUrlAdd() }
  }, [handleUrlAdd])

  const handleRemoveUrl = useCallback((url: string) => {
    onChange({ ...urls, [activeTab]: currentUrls.filter(u => u !== url) })
  }, [urls, activeTab, currentUrls, onChange])

  return (
    <div className="border border-dashed rounded-xl p-3 transition-colors">
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <ImagePlus className="w-3.5 h-3.5" />
        参考图片
      </label>

      <div className="flex gap-1 mb-2 flex-wrap">
        {(Object.keys(TAB_LABELS) as RefTab[]).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all ${
              activeTab === tab ? 'bg-primary/20 text-primary border border-primary/30' : 'text-muted-foreground hover:bg-muted border border-transparent'
            }`}>
            {TAB_LABELS[tab]}
            {urls[tab].length > 0 && <span className="ml-1 text-[9px] opacity-50">({urls[tab].length})</span>}
          </button>
        ))}
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`relative border border-dashed rounded-xl p-3 transition-colors ${dragOver ? 'border-primary bg-primary/5' : 'border-border/50'}`}
      >
        {currentUrls.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {currentUrls.map((url, i) => (
              <div key={i} className="relative group w-16 h-16">
                <img src={url} alt="" className="w-full h-full rounded object-cover bg-muted"
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
                <button onClick={() => handleRemoveUrl(url)}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  title="移除">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2">
          <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
            className="w-16 h-16 rounded-lg border border-dashed border-border/50 flex items-center justify-center text-muted-foreground hover:text-foreground hover:border-border transition-colors flex-shrink-0">
            {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ImagePlus className="w-5 h-5" />}
          </button>
          <div className="flex-1 flex items-center gap-2">
            <Link className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <input value={urlInput} onChange={e => setUrlInput(e.target.value)} onKeyDown={handleUrlKeyDown}
              placeholder="粘贴图片 URL 按回车添加..."
              className="flex-1 bg-transparent border-b border-border/40 pb-1 text-xs text-foreground outline-none focus:border-border transition-colors" />
            <button onClick={handleUrlAdd} disabled={!urlInput.trim()}
              className="text-xs text-primary hover:underline disabled:opacity-30 flex-shrink-0">添加</button>
          </div>
        </div>
      </div>

      <button onClick={openHistory} type="button"
        className="mt-2 flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-primary transition-colors">
        <History className="w-3 h-3" />
        从历史作品选择
      </button>

      <input ref={fileInputRef} type="file" accept="image/*" multiple
        className="hidden" onChange={e => handleFileSelect(e.target.files)} />

      {showHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowHistory(false)}>
          <div className="bg-background border border-border rounded-2xl p-5 max-w-lg w-full mx-4 max-h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm flex items-center gap-1.5">
                <ImageIcon className="w-4 h-4" />
                选择历史作品 → {TAB_LABELS[activeTab]}
              </h3>
              <button onClick={() => setShowHistory(false)} className="text-muted-foreground hover:text-foreground text-xs">✕</button>
            </div>
            {loadingHistory ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : historyImages.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-10">暂无历史作品</p>
            ) : (
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 overflow-y-auto max-h-64">
                {historyImages.map((img, i) => (
                  <div key={img.url} className="group relative cursor-pointer rounded-lg overflow-hidden border border-border/30 hover:border-primary/50 transition-colors"
                    onClick={() => {
                      if (!currentUrls.includes(img.url)) {
                        onChange({ ...urls, [activeTab]: [...currentUrls, img.url] })
                      }
                      setShowHistory(false)
                    }}>
                    <img src={img.url} alt="" className="w-full h-20 object-cover bg-muted" />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-primary/20 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <span className="text-[10px] text-white bg-black/60 px-2 py-0.5 rounded-full">选择</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {dragOver && (
        <div className="absolute inset-0 rounded-xl bg-primary/10 border-2 border-primary border-dashed flex items-center justify-center pointer-events-none z-10">
          <span className="text-sm font-medium text-primary">释放以上传图片到 {TAB_LABELS[activeTab]}</span>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 构建验证**

Run: `npm run build`

- [ ] **Step 3: Commit**

```bash
git add src/components/ReferenceImageUploader.tsx
git commit -m "feat: four-tab reference image uploader (style/character/scene/prop)"
```

---

### Task 8: FreeImageGenForm — 适配新接口

**Files:**
- Modify: `src/components/FreeImageGenForm.tsx`

- [ ] **Step 1: 改 props 和类型**

修改文件头部的 import 和 props：

```typescript
import type { ReferenceUrlsByType } from '../lib/types'
```

在 `FreeImageGenFormProps` 接口中改：
```typescript
  referenceUrls: string[]  // 保留向后兼容
  referenceUrlsByType: ReferenceUrlsByType
  onReferenceUrlsChange: (urls: string[]) => void
  onReferenceUrlsByTypeChange?: (urls: ReferenceUrlsByType) => void
```

- [ ] **Step 2: 更新 ReferenceImageUploader 调用**

```tsx
        <ReferenceImageUploader urls={referenceUrlsByType} onChange={(v) => {
          onReferenceUrlsByTypeChange?.(v)
          // 同步旧版扁平数组
          onReferenceUrlsChange([...v.character, ...v.scene, ...v.prop])
        }} />
```

- [ ] **Step 3: 更新"参考"按钮（生图结果悬停）保持 character 类型**

```tsx
                    <button onClick={(e) => { e.stopPropagation(); if (!referenceUrlsByType.character.includes(src)) onReferenceUrlsByTypeChange?.({ ...referenceUrlsByType, character: [...referenceUrlsByType.character, src] }) }}
```

- [ ] **Step 4: 构建验证 + Commit**

Run: `npm run build`

---

### Task 9: ProjectImageGenForm — 道具区块

**Files:**
- Modify: `src/components/ProjectImageGenForm.tsx`

- [ ] **Step 1: 添加自动适配类型引用**

文件顶部 import 加：
```typescript
import type { ReferenceUrlsByType } from '../lib/types'
```

- [ ] **Step 2: 新增 props 字段**

在 `ProjectImageGenFormProps` 接口里加：
```typescript
  autoRefUrlsByType: ReferenceUrlsByType
  manualRefUrlsByType: ReferenceUrlsByType
  onManualRefUrlsByTypeChange: (v: ReferenceUrlsByType) => void
  selectedProp: string | null
  onPropSelect: (characterName: string, propName: string) => void
```

- [ ] **Step 3: 在场景区块后新增道具区块**

在 `CollapsibleSection`（场景区块的闭标签后面）添加：

```tsx
            <CollapsibleSection title={`🔧 道具`}>
              {characters.length === 0 ? (
                <p className="text-[10px] text-muted-foreground">暂无道具数据</p>
              ) : (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {characters.filter(c => (c.accessories || []).length > 0).map(c =>
                    (c.accessories || []).map(prop => {
                      const propKey = `${c.name}/${prop}`
                      const isSel = selectedProp === propKey
                      return (
                        <button key={propKey} onClick={() => { onPropSelect?.(c.name, prop) }}
                          className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[11px] text-left transition-all ${
                            isSel ? 'bg-primary/15 text-primary font-medium' : 'hover:bg-muted text-muted-foreground'
                          }`}>
                          <span className="truncate">{c.name} / {prop}</span>
                        </button>
                      )
                    })
                  )}
                </div>
              )}
            </CollapsibleSection>
```

- [ ] **Step 4: 更新 handleGen 合并参考图逻辑**

```typescript
    const allRefUrls = [...autoRefUrls, ...manualRefUrls]
    const allRefUrlsByType: ReferenceUrlsByType = {
      style: [...(autoRefUrlsByType?.style || []), ...(manualRefUrlsByType?.style || [])],
      character: [...(autoRefUrlsByType?.character || []), ...(manualRefUrlsByType?.character || [])],
      scene: [...(autoRefUrlsByType?.scene || []), ...(manualRefUrlsByType?.scene || [])],
      prop: [...(autoRefUrlsByType?.prop || []), ...(manualRefUrlsByType?.prop || [])],
    }
```

生成调用时传 `reference_urls_by_type: allRefUrlsByType`。

- [ ] **Step 5: 构建验证 + Commit**

---

### Task 10: ImageGenPage — state 和连线

**Files:**
- Modify: `src/pages/ImageGenPage.tsx`

- [ ] **Step 1: 新增 state**

```typescript
  const [autoRefUrlsByType, setAutoRefUrlsByType] = useState<ReferenceUrlsByType>({ style: [], character: [], scene: [], prop: [] })
  const [manualRefUrlsByType, setManualRefUrlsByType] = useState<ReferenceUrlsByType>({ style: [], character: [], scene: [], prop: [] })
  const [selectedProp, setSelectedProp] = useState<string | null>(null)
```

- [ ] **Step 2: handleCharSelect 中设置 character 自动参考图**

```typescript
        setAutoRefUrlsByType(prev => ({ ...prev, character: baseImages.images.map(img => img.url) }))
```

- [ ] **Step 3: 新增 handlePropSelect**

```typescript
  const handlePropSelect = async (charName: string, propName: string) => {
    const propKey = `${charName}/${propName}`
    if (propKey === selectedProp) { setSelectedProp(null); setProjectPrompt(''); return }
    setSelectedProp(propKey)
    setSelectedChar(null)
    setSelectedScene(null)
    try {
      const result = await fetchPropPrompt(selectedProject, charName, propName)
      setProjectPrompt(result.prompt || '')
    } catch {
      setProjectPrompt('')
    }
  }
```

- [ ] **Step 4: 更新 ProjectImageGenForm 的 props 传递**

在 JSX 中添加新 props 的传递：
```tsx
            autoRefUrlsByType={autoRefUrlsByType}
            manualRefUrlsByType={manualRefUrlsByType}
            onManualRefUrlsByTypeChange={setManualRefUrlsByType}
            selectedProp={selectedProp}
            onPropSelect={handlePropSelect}
```

- [ ] **Step 5: 构建验证 + Commit**

---

### Task 11: 最终集成验证

- [ ] **Step 1: 前端构建**

Run: `npm run build`

- [ ] **Step 2: 后端语法验证**

Run: `python -c "import py_compile; [py_compile.compile(f, doraise=True) for f in ['server/routes/gen.py','server/routes/projects.py','agents/prompt_factory.py','core/style_config.py']]; print('OK')"`

- [ ] **Step 3: 重启服务器测试**

```bash
python run_web.py
```

访问 http://localhost:8000 验证：
1. 自由生图 — 四标签页参考图上传
2. 项目生图 — 角色/场景/道具区块显示和提示词
3. 选择角色 — L1 基础形象提示词不含动作和配饰
4. 选择道具 — L2 道具提示词
5. style_decl — 自动适配显示具体画风名

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: complete character prompt L1/L2, auto art style, four-tab reference UI"
```
