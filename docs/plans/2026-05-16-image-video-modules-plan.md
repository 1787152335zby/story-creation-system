# AI 生图 + 图生视频 模块化架构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add image generation (module 2) and video generation (module 3) to the existing text pipeline (module 1), with both batch pipeline mode and single-thread mode.

**Architecture:** Three-module system sharing a common project directory. Module 1 extended to extract character/scene info (VisualBible). Module 2 uses pluggable ImageBackend abstraction (Seedream first). Module 3 uses pluggable VideoBackend abstraction (Seedance first) + ffmpeg concatenation.

**Tech Stack:** Python (FastAPI + asyncio), TypeScript (React), Seedream API (image gen), Seedance API (video gen), ffmpeg (concat), Pillow (image composition)

---

## File Structure

### New files:
| File | Responsibility |
|:-----|:---------------|
| `core/visual_bible.py` | Extract character/scene structured data from screenplay/storyboard via LLM |
| `tools/image_api.py` | Abstract base class for image generation backends |
| `tools/image_api_seedream.py` | Seedream backend implementation |
| `tools/image_composer.py` | Compose multiple scene angle images into a panorama |
| `tools/video_api.py` | Abstract base class for video generation backends |
| `tools/video_api_seedance.py` | Seedance backend implementation |
| `tools/video_concat.py` | ffmpeg-based video concatenation |
| `agents/image_artist.py` | Image generation agent (supports batch + single-thread) |
| `agents/visual_extractor.py` | Agent wrapping VisualBible extractor as a pipeline phase |
| `prompts/visual_extractor.txt` | Prompt template for character/scene extraction |
| `prompts/image_artist.txt` | Prompt template for image generation prompts |

### Modified files:
| File | Change |
|:-----|:-------|
| `workflow.yaml` | Add 3 new phases: visual_extractor, image_artist, video_producer |
| `core/project_manager.py:49-56` | Add 3 new phase names to default config |
| `core/style_config.py:66-71` | Add IMAGE_PLATFORMS alongside VIDEO_PLATFORMS |
| `server/async_orch.py:14-21` | Add `visual_extractor`, `image_artist`, `video_producer` to AGENT_TO_CONFIG |
| `server/routes/__init__.py` | Register new routes |
| `server/routes/projects.py` | Add media file listing/serving endpoints |
| `src/pages/Workspace.tsx` | Add sidebar entries for 06/07/08 phases, image/video display |
| `src/lib/api.ts` | Add API functions for image/video endpoints |

---

## Phase P0 — VisualBible & Pipeline Setup

### Task P0-1: Create VisualBible extractor

**Files:**
- Create: `core/visual_bible.py`

- [ ] **Step 1: Create `core/visual_bible.py`**

```python
import json
from pathlib import Path
from typing import Optional
from llm.client import LLMClient

CHARACTER_EXTRACT_PROMPT = """你是一位专业的剧本分析师。请从以下剧本内容中提取所有角色和场景的结构化信息。

输出格式为JSON：
{
  "characters": [
    {
      "name": "角色名",
      "appearance": "外貌特征综合描述（年龄、脸型、发型、五官特征、身高体型等）",
      "age": "年龄",
      "gender": "男/女",
      "clothing": "服装描述（颜色、材质、款式）",
      "key_features": ["标志性特征1", "标志性特征2"]
    }
  ],
  "scenes": [
    {
      "name": "场景名（第X场-地点）",
      "environment": "环境描述（空间布局、装修风格、关键物品位置）",
      "lighting": "光线描述",
      "color_tone": "色调描述",
      "props": ["关键道具1", "关键道具2"]
    }
  ]
}

只输出JSON，不要其他文字。
"""


class VisualBibleExtractor:
    @staticmethod
    def extract_all(project) -> dict:
        script_path = project.project_dir / "03_完整剧本" / "完整剧本.md"
        if not script_path.exists():
            script_path = project.project_dir / "03_完整剧本"
            files = sorted(script_path.glob("完整剧本_*.md"))
            script_content = "\n\n".join(f.read_text(encoding="utf-8") for f in files) if files else ""
        else:
            script_content = script_path.read_text(encoding="utf-8")

        if not script_content.strip():
            return {"characters": [], "scenes": []}

        client = LLMClient()
        result = client.chat(CHARACTER_EXTRACT_PROMPT, script_content[:8000], temperature=0.3)

        import re
        json_match = re.search(r"\{.*\}", result, re.DOTALL)
        data = json.loads(json_match.group()) if json_match else {"characters": [], "scenes": []}

        bible_dir = project.project_dir / "06_角色场景"
        chars_dir = bible_dir / "角色"
        scenes_dir = bible_dir / "场景"
        chars_dir.mkdir(parents=True, exist_ok=True)
        scenes_dir.mkdir(parents=True, exist_ok=True)

        for char in data.get("characters", []):
            char_file = chars_dir / f"{char['name']}.json"
            char_file.write_text(json.dumps(char, ensure_ascii=False, indent=2), encoding="utf-8")

        for scene in data.get("scenes", []):
            scene_file = scenes_dir / f"{scene['name']}.json"
            scene_file.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")

        report = bible_dir / "提取报告.md"
        report_lines = ["# 角色/场景提取报告\n"]
        report_lines.append(f"## 角色（{len(data.get('characters', []))}个）")
        for c in data.get("characters", []):
            report_lines.append(f"- **{c['name']}**（{c.get('gender','')}，{c.get('age','')}岁）")
        report_lines.append(f"\n## 场景（{len(data.get('scenes', []))}个）")
        for s in data.get("scenes", []):
            report_lines.append(f"- **{s['name']}** - {s.get('environment','')[:50]}...")
        report.write_text("\n".join(report_lines), encoding="utf-8")

        return data

    @staticmethod
    def list_characters(project) -> list[dict]:
        chars_dir = project.project_dir / "06_角色场景" / "角色"
        if not chars_dir.exists():
            return []
        result = []
        for f in sorted(chars_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        return result

    @staticmethod
    def list_scenes(project) -> list[dict]:
        scenes_dir = project.project_dir / "06_角色场景" / "场景"
        if not scenes_dir.exists():
            return []
        result = []
        for f in sorted(scenes_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        return result
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from core.visual_bible import VisualBibleExtractor; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add core/visual_bible.py
git commit -m "feat: add VisualBible extractor for character/scene info"
```

---

### Task P0-2: Create visual_extractor agent

**Files:**
- Create: `agents/visual_extractor.py`
- Create: `prompts/visual_extractor.txt`

- [ ] **Step 1: Create `agents/visual_extractor.py`**

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor


class VisualExtractor(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        data = VisualBibleExtractor.extract_all(project)
        chars = data.get("characters", [])
        scenes = data.get("scenes", [])
        char_count = len(chars)
        scene_count = len(scenes)
        char_names = "、".join(c["name"] for c in chars[:5])
        scene_names = "、".join(s["name"] for s in scenes[:5])
        report = f"✅ 角色/场景提取完成\n\n角色（{char_count}个）：{char_names}\n场景（{scene_count}个）：{scene_names}"
        yield report
```

- [ ] **Step 2: Create empty prompt file `prompts/visual_extractor.txt`**

```
你负责提取剧本中的角色和场景信息。
```

- [ ] **Step 3: Commit**

```bash
git add agents/visual_extractor.py prompts/visual_extractor.txt
git commit -m "feat: add visual_extractor agent"
```

---

### Task P0-3: Update workflow, config, and async_orch

**Files:**
- Modify: `workflow.yaml`
- Modify: `core/project_manager.py:49-56`
- Modify: `server/async_orch.py:14-21`
- Modify: `core/style_config.py:66-71`

- [ ] **Step 1: Update `workflow.yaml`** — append after existing phases:

```yaml
  - name: 视觉提取
    agent: visual_extractor
    output: 06_角色场景/
    condition: true
    auto_skip: false
    split: false

  - name: 视觉素材
    agent: image_artist
    output: 07_视觉素材/
    condition: true
    auto_skip: false
    split: false

  - name: 视频生成
    agent: video_producer
    output: 08_视频/
    condition: true
    auto_skip: false
    split: true
```

- [ ] **Step 2: Update `core/project_manager.py`** — add 3 new phases to default config (around line 49-56):

```python
            "phases": [
                {"name": "story_outline", "done": False},
                {"name": "full_plot", "done": False},
                {"name": "full_script", "done": False},
                {"name": "storyboard", "done": False},
                {"name": "prompts", "done": False},
                {"name": "visual_extract", "done": False},
                {"name": "image_gen", "done": False},
                {"name": "video_gen", "done": False},
            ],
```

- [ ] **Step 3: Update `server/async_orch.py`** — add to AGENT_TO_CONFIG (around line 14-21):

```python
    AGENT_TO_CONFIG = {
        "outline_designer": "story_outline",
        "plot_expander": "full_plot",
        "screenplay_writer": "full_script",
        "storyboarder": "storyboard",
        "prompt_engineer": "prompts",
        "visual_extractor": "visual_extract",
        "image_artist": "image_gen",
        "video_producer": "video_gen",
    }
```

- [ ] **Step 4: Add `IMAGE_PLATFORMS` to `core/style_config.py`** (after VIDEO_PLATFORMS):

```python
IMAGE_PLATFORMS = {
    "1": {"name": "Seedream", "desc": "火山引擎文生图，与Seedance同生态"},
    "2": {"name": "DALL-E 3", "desc": "OpenAI 图像生成"},
    "3": {"name": "Midjourney", "desc": "高质量艺术风格"},
}
```

- [ ] **Step 5: Commit**

```bash
git add workflow.yaml core/project_manager.py server/async_orch.py core/style_config.py
git commit -m "feat: add visual_extract/image_gen/video_gen to pipeline"
```

---

## Phase P1 — Image Generation Module

### Task P1-1: Create image API abstraction + Seedream backend

**Files:**
- Create: `tools/image_api.py`
- Create: `tools/image_api_seedream.py`

- [ ] **Step 1: Create `tools/image_api.py`**

```python
from abc import ABC, abstractmethod
from typing import Optional


class ImageBackend(ABC):
    @abstractmethod
    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1) -> list[str]:
        """
        Text-to-image generation.
        Returns list of image URLs.
        """

    @abstractmethod
    def name(self) -> str:
        """Backend display name"""


def create_image_backend(backend_name: str = "seedream") -> ImageBackend:
    backends = {
        "seedream": "SeedreamBackend",
    }
    if backend_name not in backends:
        raise ValueError(f"Unknown image backend: {backend_name}")
    import importlib
    module = importlib.import_module(f"tools.image_api_{backend_name}")
    cls = getattr(module, backends[backend_name])
    return cls()
```

- [ ] **Step 2: Create `tools/image_api_seedream.py`**

```python
import os
import requests
import json
from .image_api import ImageBackend


class SeedreamBackend(ImageBackend):
    def __init__(self):
        self.api_key = os.getenv("SEEDANCE_API_KEY", "")
        self.base_url = "https://api.volcengine.com/ark/v1/images/generations"

    def text_to_image(self, prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1) -> list[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "seedream-v1",
            "prompt": prompt,
            "n": n,
            "size": size,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return [img["url"] for img in data.get("data", [])]

    def name(self) -> str:
        return "Seedream"
```

- [ ] **Step 3: Commit**

```bash
git add tools/image_api.py tools/image_api_seedream.py
git commit -m "feat: add image API abstraction + Seedream backend"
```

---

### Task P1-2: Create image composer for scene panorama

**Files:**
- Create: `tools/image_composer.py`

- [ ] **Step 1: Create `tools/image_composer.py`**

```python
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


class ImageComposer:
    @staticmethod
    def compose_scene_panorama(angle_images: dict[str, str], scene_name: str, output_path: str):
        """
        Compose 4 scene angle images (正视图, 左45度, 右45度, 鸟瞰图) into a 2x2 panorama.
        angle_images: {"正视图": "path/to/img1", "左45度": "path/to/img2", ...}
        """
        order = ["正视图", "左45度", "右45度", "鸟瞰图"]
        labels = ["正面", "左侧45°", "右侧45°", "俯视"]

        images = []
        for key in order:
            if key in angle_images:
                img = Image.open(angle_images[key]).convert("RGB")
                img = img.resize((1024, 1024))
                images.append(img)
            else:
                images.append(Image.new("RGB", (1024, 1024), (240, 240, 240)))

        canvas = Image.new("RGB", (2048, 2048), (255, 255, 255))
        positions = [(0, 0), (1024, 0), (0, 1024), (1024, 1024)]
        label_positions = [(10, 10), (1034, 10), (10, 1034), (1034, 1034)]

        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()

        for img, pos, label, lpos in zip(images, positions, labels, label_positions):
            canvas.paste(img, pos)
            draw.text(lpos, label, fill=(255, 255, 255), font=font)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, quality=95)

    @staticmethod
    def download_image(url: str, save_path: str):
        import requests
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(resp.content)
```

- [ ] **Step 2: Commit**

```bash
git add tools/image_composer.py
git commit -m "feat: add image composer for scene panorama"
```

---

### Task P1-3: Create ImageArtist agent

**Files:**
- Create: `agents/image_artist.py`
- Create: `prompts/image_artist.txt`

- [ ] **Step 1: Create `prompts/image_artist.txt`**

```
你是一位专业的AI生图提示词工程师。你的任务是基于角色JSON描述，生成适合文生图模型的提示词。

角色四视图提示词规范：
- 以角色名开头
- 描述外貌特征（脸型、发型、五官、肤色）
- 描述服装（颜色、材质、款式）
- 纯白背景（white background, no text）
- 画布分为4格2x2网格：左上脸部特写（胸部以上正脸）、右上全身正面、左下全身侧面（90°）、右下全身背面
- 人物居中
- 无文字遮挡

场景提示词规范：
- 以场景名开头
- 描述空间布局和关键道具位置
- 描述光线和色调
- 根据角度要求调整视角词（正视图/45度视角/鸟瞰图）
- 无文字

角色数据：{character_json}
场景数据：{scene_json}
角度要求：{angle_requirement}
```

- [ ] **Step 2: Create `agents/image_artist.py`**

```python
import json
import requests
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor
from tools.image_api import create_image_backend
from tools.image_composer import ImageComposer


class ImageArtist(AgentBase):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.image_backend = create_image_backend("seedream")

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        yield from self._run_batch(project)

    def _run_batch(self, project: ProjectManager):
        """流水线模式：遍历全部角色和场景"""
        chars = VisualBibleExtractor.list_characters(project)
        scenes = VisualBibleExtractor.list_scenes(project)

        yield f"📋 检测到 {len(chars)} 个角色，{len(scenes)} 个场景\n"

        for char in chars:
            yield f"🎨 生成角色定妆照：{char['name']}...\n"
            yield from self._generate_character(project, char)
            yield f"✅ {char['name']} 完成\n"

        for scene in scenes:
            yield f"🌆 生成场景概念图：{scene['name']}...\n"
            yield from self._generate_scene(project, scene)
            yield f"✅ {scene['name']} 完成\n"

        yield "🎉 全部视觉素材生成完成\n"

    def generate_character(self, project: ProjectManager, character_name: str):
        """单线程模式：只生成指定角色"""
        chars = VisualBibleExtractor.list_characters(project)
        char = next((c for c in chars if c["name"] == character_name), None)
        if not char:
            return
        yield from self._generate_character(project, char)

    def _generate_character(self, project: ProjectManager, char: dict):
        prompt = self._build_character_prompt(char)
        try:
            urls = self.image_backend.text_to_image(prompt, size="1024x1024", n=1)
            if urls:
                save_dir = project.project_dir / "07_视觉素材" / "角色"
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = str(save_dir / f"{char['name']}_四视图.png")
                ImageComposer.download_image(urls[0], save_path)
                yield f"  ✅ 已保存: {save_path}\n"
        except Exception as e:
            yield f"  ❌ 生成失败: {e}\n"

    def _build_character_prompt(self, char: dict) -> str:
        appearance = char.get("appearance", "")
        clothing = char.get("clothing", "")
        features = "、".join(char.get("key_features", []))
        return (
            f"'{char['name']}' 的定妆照，纯白背景。"
            f"角色特征：{appearance}。服装：{clothing}。"
            f"标志性特征：{features}。"
            f"画布分为4格2x2网格：左上脸部特写（胸部以上，正脸）、"
            f"右上全身正面、左下全身侧面（90°侧身）、右下全身背面。"
            f"每格人物居中。纯白背景，无文字遮挡。"
        )

    def generate_scene(self, project: ProjectManager, scene_name: str, angles: list[str] | None = None):
        """单线程模式：只生成指定场景（可选角度）"""
        scenes = VisualBibleExtractor.list_scenes(project)
        scene = next((s for s in scenes if s["name"] == scene_name), None)
        if not scene:
            return
        yield from self._generate_scene(project, scene, angles)

    def _generate_scene(self, project: ProjectManager, scene: dict, angles: list[str] | None = None):
        if angles is None:
            angles = ["正视图", "左45度", "右45度", "鸟瞰图"]

        save_dir = project.project_dir / "07_视觉素材" / "场景"
        save_dir.mkdir(parents=True, exist_ok=True)
        angle_images = {}

        for angle in angles:
            prompt = self._build_scene_prompt(scene, angle)
            try:
                urls = self.image_backend.text_to_image(prompt, size="1024x1024", n=1)
                if urls:
                    angle_name = angle.replace(" ", "")
                    save_path = str(save_dir / f"{scene['name']}_{angle_name}.png")
                    ImageComposer.download_image(urls[0], save_path)
                    angle_images[angle_name] = save_path
                    yield f"  ✅ {angle} 已保存\n"
            except Exception as e:
                yield f"  ❌ {angle} 生成失败: {e}\n"

        if len(angle_images) >= 2:
            panorama_path = str(save_dir / f"{scene['name']}_全景总览.png")
            ImageComposer.compose_scene_panorama(angle_images, scene["name"], panorama_path)
            yield f"  ✅ 全景总览已合成\n"

    def _build_scene_prompt(self, scene: dict, angle: str) -> str:
        env = scene.get("environment", "")
        lighting = scene.get("lighting", "自然光")
        color_tone = scene.get("color_tone", "自然色调")
        props = "、".join(scene.get("props", []))

        angle_map = {
            "正视图": "正面视角，从正前方观看",
            "左45度": "左侧45度视角，展示空间深度",
            "右45度": "右侧45度视角，展示空间纵深感",
            "鸟瞰图": "从正上方俯瞰的鸟瞰视角，完整展示空间布局",
        }
        view_desc = angle_map.get(angle, angle)

        return (
            f"'{scene['name']}' 场景概念图，{view_desc}。"
            f"环境描述：{env}。光线：{lighting}。色调：{color_tone}。"
            f"关键道具：{props}。无文字，写实风格。"
            f"blank white background around the scene for compositing. no text or watermark."
        )
```

- [ ] **Step 3: Commit**

```bash
git add agents/image_artist.py prompts/image_artist.txt
git commit -m "feat: add ImageArtist agent with batch and single-thread modes"
```

---

## Phase P2 — Frontend: Visual Assets Display

### Task P2-1: Add media API endpoints to backend

**Files:**
- Modify: `server/routes/projects.py`

- [ ] **Step 1: Add media listing/serving endpoints to `server/routes/projects.py`**

```python
from fastapi.responses import FileResponse
import mimetypes


@router.get("/projects/{name}/visual-assets")
def list_visual_assets(name: str):
    project_dir = PROJECTS_DIR / name
    assets = {"characters": [], "scenes": []}

    chars_dir = project_dir / "07_视觉素材" / "角色"
    if chars_dir.exists():
        for f in sorted(chars_dir.glob("*.png")):
            assets["characters"].append({"name": f.stem, "file": f.name})

    scenes_dir = project_dir / "07_视觉素材" / "场景"
    if scenes_dir.exists():
        for f in sorted(scenes_dir.glob("*.png")):
            assets["scenes"].append({"name": f.stem, "file": f.name})

    return assets


@router.get("/projects/{name}/characters")
def list_characters(name: str):
    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    return VisualBibleExtractor.list_characters(project)


@router.get("/projects/{name}/scenes")
def list_scenes(name: str):
    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    return VisualBibleExtractor.list_scenes(project)


@router.get("/projects/{name}/media/{subpath:path}")
def get_media_file(name: str, subpath: str):
    project_dir = PROJECTS_DIR / name
    file_path = project_dir / subpath
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(str(file_path), media_type=media_type)
```

- [ ] **Step 2: Register settings router in `server/routes/__init__.py`** (if not already):

No change needed — the main app.py already imports from routes.

- [ ] **Step 3: Commit**

```bash
git add server/routes/projects.py
git commit -m "feat: add media listing/serving endpoints for visual assets"
```

---

### Task P2-2: Add frontend API functions

**Files:**
- Modify: `src/lib/api.ts`

- [ ] **Step 1: Add to `src/lib/api.ts`**

```typescript
export async function fetchVisualAssets(name: string): Promise<{ characters: { name: string; file: string }[]; scenes: { name: string; file: string }[] }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/visual-assets`)
  if (!res.ok) return { characters: [], scenes: [] }
  return res.json()
}

export async function fetchCharacters(name: string): Promise<any[]> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/characters`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchScenes(name: string): Promise<any[]> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/scenes`)
  if (!res.ok) return []
  return res.json()
}

export function getMediaUrl(name: string, subpath: string): string {
  return `${BASE}/projects/${encodeURIComponent(name)}/media/${encodeURIComponent(subpath)}`
}
```

- [ ] **Step 2: Commit**

```bash
git add src/lib/api.ts
git commit -m "feat: add visual assets API functions"
```

---

### Task P2-3: Add sidebar entries to Workspace

**Files:**
- Modify: `src/pages/Workspace.tsx`

- [ ] **Step 1: Add new phase constants and update sidebar rendering**

Add to the phase constants section (search for `PHASE_NAMES` and `PHASE_ICONS`):

```typescript
// Update existing or add if separate
const PHASE_NAMES = ['故事大纲', '完整剧情', '完整剧本', '分镜脚本', '提示词', '视觉提取', '视觉素材', '视频生成']
const PHASE_ICONS = ['📋', '📖', '🎬', '🎨', '✨', '🔍', '🖼️', '🎥']
```

Find the sidebar rendering code and add expandable items for 06/07/08 phases. The sidebar already renders `PHASE_NAMES` as chips. We want phases 05+(visual_extract, image_gen, video_gen) to show as expandable.

Look for the sidebar section that renders `PHASE_NAMES.map(...)` and ensure all 8 phases appear. The existing code uses `PHASE_NAMES.length` or iterates over `p.phases` from project config, so updating the constants should make them appear automatically.

```typescript
// Find the section that defines phase-related constants and update them
// The sidebar rendering should already loop over PHASE_NAMES
```

- [ ] **Step 2: Add image grid display in workspace**

Find the `viewContent` rendering section and add image gallery support. After the `viewContent` markdown render section, add:

```typescript
{/* Image gallery for visual assets phase */}
{selectedPhase === 6 && !editingContent && (
  <VisualAssetGallery projectName={name || ''} />
)}
```

- [ ] **Step 3: Create VisualAssetGallery component**

This can be inline in Workspace.tsx. The component fetches and displays a grid of thumbnails. Add before the component closes:

```typescript
function VisualAssetGallery({ projectName }: { projectName: string }) {
  const [assets, setAssets] = useState<{ characters: any[]; scenes: any[] }>({ characters: [], scenes: [] })
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  useEffect(() => {
    if (projectName) {
      import('../lib/api').then(api => api.fetchVisualAssets(projectName).then(setAssets))
    }
  }, [projectName])

  return (
    <div>
      {assets.characters.length > 0 && (
        <div className="mb-8">
          <h4 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">🧑 角色定妆照</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {assets.characters.map((c: any) => (
              <div key={c.file} className="glass-card rounded-xl overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
                onClick={() => setSelectedImage(getMediaUrl(projectName, `07_视觉素材/角色/${c.file}`))}>
                <img src={getMediaUrl(projectName, `07_视觉素材/角色/${c.file}`)} alt={c.name} className="w-full h-64 object-contain bg-white" />
                <p className="text-xs text-center py-2 text-muted-foreground">{c.name.replace('_四视图', '')}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {assets.scenes.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">🌆 场景概念图</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {assets.scenes.map((s: any) => (
              <div key={s.file} className="glass-card rounded-xl overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary/50 transition-all"
                onClick={() => setSelectedImage(getMediaUrl(projectName, `07_视觉素材/场景/${s.file}`))}>
                <img src={getMediaUrl(projectName, `07_视觉素材/场景/${s.file}`)} alt={s.name} className="w-full h-64 object-cover" />
                <p className="text-xs text-center py-2 text-muted-foreground">{s.name}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {selectedImage && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8" onClick={() => setSelectedImage(null)}>
          <img src={selectedImage} className="max-w-full max-h-full object-contain" />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/Workspace.tsx
git commit -m "feat: add visual asset gallery to workspace sidebar"
```

---

## Phase P3 — Video Generation Module

### Task P3-1: Create video API abstraction + Seedance backend

**Files:**
- Create: `tools/video_api.py`
- Create: `tools/video_api_seedance.py`

- [ ] **Step 1: Create `tools/video_api.py`**

```python
from abc import ABC, abstractmethod
from typing import Optional


class VideoBackend(ABC):
    @abstractmethod
    def image_to_video(self, image_path: str, prompt: str) -> str:
        """Submit image-to-video task, return task_id"""

    @abstractmethod
    def check_status(self, task_id: str) -> dict:
        """Return {'status': 'running'|'completed'|'failed', 'video_url': '...' or 'error': '...'}"""

    @abstractmethod
    def wait_for_result(self, task_id: str, timeout: int = 300, poll_interval: int = 10) -> str:
        """Poll until complete, return video URL"""

    @abstractmethod
    def name(self) -> str:
        """Backend display name"""


def create_video_backend(backend_name: str = "seedance") -> VideoBackend:
    backends = {
        "seedance": "SeedanceBackend",
    }
    if backend_name not in backends:
        raise ValueError(f"Unknown video backend: {backend_name}")
    import importlib
    module = importlib.import_module(f"tools.video_api_{backend_name}")
    cls = getattr(module, backends[backend_name])
    return cls()
```

- [ ] **Step 2: Create `tools/video_api_seedance.py`**

```python
import os
import time
import requests
import json
from .video_api import VideoBackend


class SeedanceBackend(VideoBackend):
    def __init__(self):
        self.api_key = os.getenv("SEEDANCE_API_KEY", "")
        self.submit_url = "https://api.volcengine.com/ark/v1/video/generate"
        self.query_url = "https://api.volcengine.com/ark/v1/video/status"

    def image_to_video(self, image_path: str, prompt: str) -> str:
        file_name = os.path.basename(image_path)
        with open(image_path, "rb") as f:
            files = {"image": (file_name, f, "image/png")}
            data = {"prompt": prompt}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.post(
                self.submit_url,
                headers=headers,
                data={**data},
                files=files,
                timeout=60,
            )
        resp.raise_for_status()
        result = resp.json()
        return result.get("id", "")

    def check_status(self, task_id: str) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.get(f"{self.query_url}/{task_id}", headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "running")
        if status == "succeeded":
            return {"status": "completed", "video_url": result.get("video_url", "")}
        elif status == "failed":
            return {"status": "failed", "error": result.get("error", "Unknown error")}
        return {"status": "running"}

    def wait_for_result(self, task_id: str, timeout: int = 300, poll_interval: int = 10) -> str:
        start = time.time()
        while time.time() - start < timeout:
            result = self.check_status(task_id)
            if result["status"] == "completed":
                return result["video_url"]
            elif result["status"] == "failed":
                raise RuntimeError(f"Video generation failed: {result.get('error', 'Unknown')}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Video generation timed out after {timeout}s")

    def name(self) -> str:
        return "Seedance"
```

- [ ] **Step 3: Commit**

```bash
git add tools/video_api.py tools/video_api_seedance.py
git commit -m "feat: add video API abstraction + Seedance backend"
```

---

### Task P3-2: Create video concat tool

**Files:**
- Create: `tools/video_concat.py`

- [ ] **Step 1: Create `tools/video_concat.py`**

```python
import subprocess
import os
from pathlib import Path


class VideoConcat:
    @staticmethod
    def is_ffmpeg_available() -> bool:
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def concat(video_paths: list[str], output_path: str) -> str:
        if not video_paths:
            raise ValueError("No video paths provided")
        if len(video_paths) == 1:
            import shutil
            shutil.copy2(video_paths[0], output_path)
            return output_path

        file_list_path = Path(output_path).parent / "_concat_list.txt"
        file_list_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_list_path, "w", encoding="utf-8") as f:
            for vp in video_paths:
                abs_path = os.path.abspath(vp)
                escaped = abs_path.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        result = subprocess.run(
            ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(file_list_path),
             "-c", "copy", str(output_path), "-y"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")

        file_list_path.unlink(missing_ok=True)
        return output_path

    @staticmethod
    def get_duration(video_path: str) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip()) if result.stdout.strip() else 0.0
```

- [ ] **Step 2: Commit**

```bash
git add tools/video_concat.py
git commit -m "feat: add ffmpeg video concatenation tool"
```

---

### Task P3-3: Rewrite VideoProducer agent

**Files:**
- Create: `prompts/video_producer.txt`
- Modify: `agents/video_producer.py` (rewrite stub)

- [ ] **Step 1: Create `prompts/video_producer.txt`**

```
你是一位AI视频提示词工程师。基于以下分镜信息，生成适合图生视频模型的提示词。

输出要求：
- 描述画面中的动作和动态变化
- 保持角色外貌和场景环境一致性
- 指定镜头运动方式（推/拉/摇/移/固定）
- 指定情绪氛围
- 不超过200字

分镜信息：{storyboard_content}
角色参考：{character_ref}
场景参考：{scene_ref}
```

- [ ] **Step 2: Rewrite `agents/video_producer.py`**

```python
import json
import re
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from tools.video_api import create_video_backend
from tools.video_concat import VideoConcat


class VideoProducer(AgentBase):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.video_backend = create_video_backend("seedance")

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        yield from self._run_batch(project)

    def _run_batch(self, project: ProjectManager):
        """流水线模式：遍历提示词分段 → 生视频 → 拼接"""
        segments = self._parse_prompt_segments(project)
        if not segments:
            yield "⚠️ 未找到提示词分段\n"
            return

        yield f"📋 检测到 {len(segments)} 个视频片段\n"

        project_dir = project.project_dir
        clips_dir = project_dir / "08_视频" / "片段"
        clips_dir.mkdir(parents=True, exist_ok=True)

        video_paths = []
        for i, seg in enumerate(segments):
            yield f"🎬 生成片段 {i+1}/{len(segments)}：{seg['name']}...\n"
            try:
                video_url = yield from self._generate_clip(project, seg)
                clip_path = str(clips_dir / f"片段_{i+1:03d}.mp4")
                self._download_video(video_url, clip_path)
                video_paths.append(clip_path)
                yield f"  ✅ 已保存\n"
            except Exception as e:
                yield f"  ❌ 生成失败: {e}\n"

        if len(video_paths) >= 2 and VideoConcat.is_ffmpeg_available():
            yield "🔗 拼接视频片段...\n"
            try:
                output_path = str(project_dir / "08_视频" / "成片.mp4")
                VideoConcat.concat(video_paths, output_path)
                yield f"✅ 成片已保存: {output_path}\n"
            except Exception as e:
                yield f"⚠️ 拼接失败 (可手动拼接): {e}\n"
        elif video_paths:
            import shutil
            output_path = str(project_dir / "08_视频" / "成片.mp4")
            shutil.copy2(video_paths[0], output_path)
            yield f"✅ 已保存单片段成片\n"

    def generate_clip(self, project: ProjectManager, segment_index: int):
        """单线程模式：只生成指定索引的片段"""
        segments = self._parse_prompt_segments(project)
        if segment_index < 0 or segment_index >= len(segments):
            yield f"❌ 无效片段索引: {segment_index}\n"
            return
        seg = segments[segment_index]
        yield f"🎬 生成片段 {segment_index+1}/{len(segments)}：{seg['name']}...\n"
        try:
            video_url = yield from self._generate_clip(project, seg)
            clips_dir = project.project_dir / "08_视频" / "片段"
            clips_dir.mkdir(parents=True, exist_ok=True)
            clip_path = str(clips_dir / f"片段_{segment_index+1:03d}.mp4")
            self._download_video(video_url, clip_path)
            yield f"  ✅ 已保存: {clip_path}\n"
        except Exception as e:
            yield f"  ❌ 生成失败: {e}\n"

    def _generate_clip(self, project: ProjectManager, segment: dict):
        prompt = segment.get("prompt", "")
        image_path = self._find_matching_image(project, segment)
        if not image_path:
            raise FileNotFoundError(f"未找到匹配的参考图: {segment['name']}")
        task_id = self.video_backend.image_to_video(image_path, prompt[:500])
        video_url = self.video_backend.wait_for_result(task_id, timeout=300, poll_interval=10)
        return video_url

    def _find_matching_image(self, project: ProjectManager, segment: dict) -> str | None:
        scene_dir = project.project_dir / "07_视觉素材" / "场景"
        if scene_dir.exists():
            panorama_files = sorted(scene_dir.glob("*_全景总览.png"))
            if panorama_files:
                return str(panorama_files[0])

        char_dir = project.project_dir / "07_视觉素材" / "角色"
        if char_dir.exists():
            char_files = sorted(char_dir.glob("*.png"))
            if char_files:
                return str(char_files[0])
        return None

    def _parse_prompt_segments(self, project: ProjectManager) -> list[dict]:
        prompts_path = project.project_dir / "05_提示词" / "提示词.md"
        if not prompts_path.exists():
            alt_files = sorted((project.project_dir / "05_提示词").glob("提示词_*.md"))
            if alt_files:
                content = "\n\n".join(f.read_text(encoding="utf-8") for f in alt_files)
            else:
                return []
        else:
            content = prompts_path.read_text(encoding="utf-8")

        segments = []
        pattern = re.compile(r"#{1,4}\s*(第\d+[场集]|镜头\d+)", re.MULTILINE)
        parts = pattern.split(content)
        for i in range(1, len(parts), 2):
            name = parts[i].strip()
            text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            segments.append({"name": name, "content": text, "prompt": text[:300]})
        if not segments and content.strip():
            segments.append({"name": "全部", "content": content, "prompt": content[:300]})
        return segments

    def _download_video(self, url: str, save_path: str):
        import requests
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
```

- [ ] **Step 3: Commit**

```bash
git add agents/video_producer.py prompts/video_producer.txt
git commit -m "feat: rewrite VideoProducer agent with batch and single-thread modes"
```

---

## Phase P4 — Frontend: Video Display

### Task P4-1: Add video listing API endpoints

**Files:**
- Modify: `server/routes/projects.py`

- [ ] **Step 1: Add to `server/routes/projects.py`**

```python
@router.get("/projects/{name}/video-clips")
def list_video_clips(name: str):
    project_dir = PROJECTS_DIR / name
    clips = []
    clips_dir = project_dir / "08_视频" / "片段"
    if clips_dir.exists():
        for f in sorted(clips_dir.glob("*.mp4")):
            clips.append({"name": f.stem, "file": str(f.relative_to(project_dir))})

    output_file = project_dir / "08_视频" / "成片.mp4"
    final_clip = None
    if output_file.exists():
        final_clip = {"name": "成片", "file": str(output_file.relative_to(project_dir))}

    return {"clips": clips, "final": final_clip}
```

- [ ] **Step 2: Commit**

```bash
git add server/routes/projects.py
git commit -m "feat: add video clips listing endpoint"
```

---

### Task P4-2: Add video display to frontend

**Files:**
- Modify: `src/lib/api.ts`
- Modify: `src/pages/Workspace.tsx`

- [ ] **Step 1: Add to `src/lib/api.ts`**

```typescript
export async function fetchVideoClips(name: string): Promise<{ clips: { name: string; file: string }[]; final: { name: string; file: string } | null }> {
  const res = await fetch(`${BASE}/projects/${encodeURIComponent(name)}/video-clips`)
  if (!res.ok) return { clips: [], final: null }
  return res.json()
}
```

- [ ] **Step 2: Add VideoPlayer component to Workspace.tsx**

Add after the VisualAssetGallery component:

```typescript
function VideoPlayer({ projectName }: { projectName: string }) {
  const [clips, setClips] = useState<{ name: string; file: string }[]>([])
  const [finalClip, setFinalClip] = useState<{ name: string; file: string } | null>(null)
  const [playing, setPlaying] = useState<string | null>(null)

  useEffect(() => {
    if (projectName) {
      import('../lib/api').then(api => api.fetchVideoClips(projectName).then(data => {
        setClips(data.clips)
        setFinalClip(data.final)
      }))
    }
  }, [projectName])

  return (
    <div>
      {finalClip && (
        <div className="mb-8">
          <h4 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">▶️ 成片</h4>
          <video
            src={getMediaUrl(projectName, finalClip.file)}
            controls className="w-full max-w-2xl rounded-xl"
            style={{ maxHeight: '500px' }}
          />
        </div>
      )}
      {clips.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">🎬 视频片段</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {clips.map((clip) => (
              <div key={clip.file} className="glass-card rounded-xl overflow-hidden">
                <video
                  src={getMediaUrl(projectName, clip.file)}
                  controls className="w-full"
                  style={{ maxHeight: '300px' }}
                  preload="metadata"
                />
                <p className="text-xs text-center py-2 text-muted-foreground">{clip.name}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

And in the main Workspace render, add video player for phase 7:

```typescript
{selectedPhase === 7 && !editingContent && (
  <VideoPlayer projectName={name || ''} />
)}
```

- [ ] **Step 3: Commit**

```bash
git add src/lib/api.ts src/pages/Workspace.tsx
git commit -m "feat: add video player and clips list to workspace"
```

---

## Summary Checklist

| Phase | Task | Status |
|:------|:-----|:-------|
| P0-1 | VisualBible extractor | ⬜ |
| P0-2 | VisualExtractor agent | ⬜ |
| P0-3 | Workflow/config/async_orch updates | ⬜ |
| P1-1 | Image API abstraction + Seedream | ⬜ |
| P1-2 | Image composer | ⬜ |
| P1-3 | ImageArtist agent | ⬜ |
| P2-1 | Media API endpoints | ⬜ |
| P2-2 | Frontend API functions | ⬜ |
| P2-3 | Workspace visual asset gallery | ⬜ |
| P3-1 | Video API abstraction + Seedance | ⬜ |
| P3-2 | Video concat tool | ⬜ |
| P3-3 | Rewrite VideoProducer agent | ⬜ |
| P4-1 | Video listing API | ⬜ |
| P4-2 | Frontend video player | ⬜ |
