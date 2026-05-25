import json
import subprocess
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from ..schemas import CreateProjectRequest, StyleConfigRequest

router = APIRouter()
PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent / "projects"
GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "generated"


def _cancel_orphan_task(name: str):
    try:
        from .creation import manager as ws_mgr
        ws_mgr.cancel_project_task(name)
    except Exception:
        pass


def _get_running_set() -> set:
    """返回当前有后台任务正在运行的项目名集合"""
    try:
        from .creation import manager as ws_mgr
        return {n for n, t in ws_mgr.running_tasks.items() if t and not t.done()}
    except Exception:
        return set()


def _build_project_list() -> list:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    running_set = _get_running_set()
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir():
            config_file = item / "project_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                config["total_phases"] = len(config.get("phases", []))
                config["pending_episode"] = config.get("pending_episode", False)
                config["running"] = config.get("name", "") in running_set
                projects.append(config)
    return sorted(projects, key=lambda p: p.get("updated_at", ""), reverse=True)


@router.get("/projects")
def list_projects():
    return _build_project_list()


@router.get("/projects/{name}")
def get_project(name: str):
    project_dir = PROJECTS_DIR / name
    config_file = project_dir / "project_config.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    config["running"] = name in _get_running_set()
    return config


@router.get("/projects/{name}/{phase:path}/content")
def get_phase_content(name: str, phase: str):
    project_dir = PROJECTS_DIR / name
    phase_path = project_dir / phase
    if not phase_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    if phase_path.is_dir():
        root_md = list(phase_path.glob("*.md"))
        sub_md = []
        for subdir in sorted(phase_path.iterdir()):
            if subdir.is_dir():
                sub_md.extend(subdir.glob("*.md"))
        md_files = root_md + sub_md
        md_files = [f for f in md_files if not f.name.startswith("分镜提示词")]
        stems_with_ji = {f.stem for f in md_files if f.stem.endswith('集')}
        md_files = [f for f in md_files if not (f.stem + '集' in stems_with_ji)]
        cn_num = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
        def sort_key(f):
            name = f.stem
            for cn, num in cn_num.items():
                if cn in name:
                    return (0, num)
            nums = re.findall(r'\d+', name)
            return (1, int(nums[0]) if nums else 0)
        md_files.sort(key=sort_key)
        if not md_files:
            raise HTTPException(status_code=404, detail="无内容")
        root_names = {f.name for f in root_md}
        has_sub = len(sub_md) > 0
        file_list = []
        for mf in md_files:
            if mf.parent != phase_path:
                rel = mf.relative_to(phase_path).as_posix()
                file_list.append(rel)
            else:
                if has_sub and mf.name in root_names:
                    root_stems = {s.stem for s in md_files if s.parent != phase_path}
                    if mf.stem in root_stems:
                        continue
                file_list.append(mf.name)
        if not file_list:
            file_list = [f.name for f in md_files]
        parts = [mf.read_text(encoding="utf-8") for mf in md_files]
        return {"content": "\n\n---\n\n".join(parts), "is_split": True, "file_list": file_list}
    return {"content": phase_path.read_text(encoding="utf-8"), "is_split": False, "file_list": [phase_path.name]}


@router.put("/projects/{name}/{phase:path}/content")
def save_phase_content(name: str, phase: str, body: dict):
    project_dir = PROJECTS_DIR / name
    phase_path = project_dir / phase
    if not phase_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    content = body.get("content", "")
    phase_path.write_text(content, encoding="utf-8")
    # 更新项目 updated_at，保持首页排序准确
    config_file = project_dir / "project_config.json"
    if config_file.exists():
        cfg = json.loads(config_file.read_text(encoding="utf-8"))
        from datetime import datetime
        cfg["updated_at"] = datetime.now().isoformat()
        config_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "path": phase, "size": len(content)}


@router.post("/projects")
def create_project(req: CreateProjectRequest):
    from core.project_manager import ProjectManager
    from core.style_config import STORY_TYPES, WRITING_STYLES, VISUAL_STYLES, RENDER_STYLES, SCREEN_ASPECTS, SCRIPT_STYLES

    project = ProjectManager(req.name)

    task_content = f"""# 创作任务

## 故事类型
{STORY_TYPES.get(req.style.story_type, {}).get('name', '')}

## 题材风格
{req.style.genre}

## 文笔风格
{WRITING_STYLES.get(req.style.writing_style, {}).get('name', '')}

## 视觉/叙事风格
{VISUAL_STYLES.get(req.style.visual_style, {}).get('name', '')}

## 渲染画风
{RENDER_STYLES.get(req.style.art_style, {}).get('name', '')}

## 剧本写作风格
{SCRIPT_STYLES.get(req.style.script_style, {}).get('name', '')}

## 画面比例
{SCREEN_ASPECTS.get(req.style.screen_aspect, {}).get('name', '')}

## 时长
{req.duration_line}

## 故事描述
{req.story_idea}

## 额外要求
{req.style.custom_requirements or '无'}
"""

    project.write_output("00_任务指令/任务指令.md", task_content)
    project.config["style_type"] = req.style.story_type
    project.config["genre"] = req.style.genre
    project.config["writing_style"] = req.style.writing_style
    project.config["visual_style"] = req.style.visual_style
    project.config["art_style"] = req.style.art_style
    project.config["screen_aspect"] = req.style.screen_aspect
    project.config["script_style"] = req.style.script_style
    project.config["script_format"] = req.style.script_format
    project.config["duration_mode"] = req.style.duration_mode
    project.config["episode_count"] = req.style.episode_count
    project.config["episode_duration"] = req.style.episode_duration
    project.config["custom_requirements"] = req.style.custom_requirements
    project.config["visual_reference"] = req.style.visual_reference
    project.config["action_reference"] = req.style.action_reference
    project.config["mood"] = req.style.mood
    project.config["selected_model"] = req.model
    project.save_config()

    if req.template_name:
        import shutil
        template_demand = TEMPLATES_DIR / f"{req.template_name}_demand"
        if template_demand.exists():
            dest = project_dir / "06_生图需求"
            shutil.copytree(str(template_demand), str(dest), dirs_exist_ok=True)

    return {"name": req.name, "status": "created"}


@router.post("/projects/random-idea")
def random_story_idea(style: StyleConfigRequest):
    from core.style_config import STORY_TYPES, WRITING_STYLES, VISUAL_STYLES, RENDER_STYLES, SCRIPT_STYLES, SCREEN_ASPECTS
    from concurrent.futures import ThreadPoolExecutor, TimeoutError

    story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
    genre_name = style.genre or "未知"
    writing_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "未知")
    visual_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "未知")
    render_name = RENDER_STYLES.get(style.art_style, {}).get("name", "未知")
    script_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "未知")
    aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "未知")
    mood_name = style.mood or ""

    prompt = f"""你是一位专业的故事策划师。请根据以下配置，创作一段50-100字的故事描述，作为{story_type_name}的创作起点。

【故事类型】：{story_type_name}
【题材风格】：{genre_name}
【文笔风格】：{writing_name}
【视觉/叙事风格】：{visual_name}
【渲染画风】：{render_name}
【剧本写作风格】：{script_name}
【画面比例】：{aspect_name}
【情绪氛围】：{mood_name or '无特殊要求'}

要求：
1. 故事描述必须紧密贴合【故事类型】，例如：
   - 如果是"短剧"，构思应适合多集短视频形式，每集留有钩子
   - 如果是"电影"，构思应有完整的三幕结构潜力
   - 如果是"电视剧"，构思应有长线叙事和多线发展的空间
   - 如果是"小说/网文"，构思应适合章节连载
   - 如果是"舞台剧/话剧"，构思应有强烈的剧场感和空间限定
   - 如果是"广播剧/有声书"，构思应侧重声音表现力和听觉想象
2. 故事构思必须体现【视觉/叙事风格】和【渲染画风】的审美取向，例如：
   - "竖屏短剧风"→ 构思应有强烈的反转和钩子
   - "好莱坞大片风"→ 构思应有高概念、大场面的潜质
   - "文艺/独立风"→ 构思应偏向内心冲突和情绪留白
   - "水墨/国风"→ 构思应适合中国传统美学呈现
   - "写实/真人"→ 构思应贴近现实生活质感
3. 故事的文字风格应体现【文笔风格】和【剧本写作风格】，例如：
   - 输出的描述文字本身应带有对应的笔触质感
   - 如果是对白驱动型，构思的矛盾应以人物对话为核心
   - 如果是画面感强，构思应着重视觉化的场景想象
4. 必须包含：一个核心角色 + 一个明确的困境/冲突 + 一个独特的场景设定
5. 语言简洁有力，50-100字
6. 直接输出故事描述，不要任何额外说明和标记
7. 每次生成都应该是全新的创意，避免套路化"""

    from llm.client import LLMClient
    def _call_llm():
        client = LLMClient()
        return client.chat(prompt, "", temperature=0.9, max_tokens=800)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_call_llm)
        result = future.result(timeout=8)
    idea = result.strip().strip('"').strip("'").strip('"""').strip("'''")
    if not idea or len(idea) < 10:
        raise HTTPException(status_code=500, detail="LLM返回内容过短，请重试")
    return {"idea": idea, "source": "ai"}


@router.post("/projects/{name}/open")
def open_project_folder(name: str, subfolder: str = ""):
    project_dir = PROJECTS_DIR / name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    target = project_dir / subfolder if subfolder else project_dir
    if subfolder and not target.exists():
        target.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.Popen(["explorer", str(target)])
        return {"opened": True, "path": str(target)}
    except Exception as e:
        return {"opened": False, "error": str(e)}


@router.delete("/projects/{name}")
def delete_project(name: str):
    import shutil
    project_dir = PROJECTS_DIR / name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    shutil.rmtree(project_dir)
    return {"deleted": True}


import mimetypes
from fastapi.responses import FileResponse


@router.get("/projects/{name}/image-demands")
def get_image_demands(name: str):
    project_dir = PROJECTS_DIR / name
    demand_file = project_dir / "06_生图需求" / "生图清单.json"
    if not demand_file.exists():
        demand_file = project_dir / "07_生图需求" / "生图清单.json"
    if demand_file.exists():
        data = json.loads(demand_file.read_text(encoding="utf-8"))
        confirmed_file = demand_file.parent / "_confirmed.json"
        if confirmed_file.exists():
            try:
                data["_confirmed"] = json.loads(confirmed_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return data
    return {"characters": [], "scenes": [], "key_props": [], "total_shots": 0, "episodes": [], "character_groups": [], "fallback": True}


@router.get("/projects/{name}/visual-assets")
def list_visual_assets(name: str):
    project_dir = PROJECTS_DIR / name
    assets = {"characters": [], "scenes": [], "props": []}

    chars_dir = project_dir / "07_视觉素材" / "角色"
    if chars_dir.exists():
        for f in sorted(chars_dir.glob("*.png")):
            assets["characters"].append({"name": f.stem, "file": f.name})

    scenes_dir = project_dir / "07_视觉素材" / "场景"
    if scenes_dir.exists():
        for f in sorted(scenes_dir.glob("*.png")):
            assets["scenes"].append({"name": f.stem, "file": f.name})

    props_dir = project_dir / "07_视觉素材" / "道具"
    if props_dir.exists():
        for f in sorted(props_dir.glob("*.png")):
            assets["props"].append({"name": f.stem, "file": f.name})

    asset_dir = project_dir / "07_生成素材"
    for entity_type, entity_label in [("characters", "角色"), ("scenes", "场景"), ("props", "道具")]:
        entities_dir = asset_dir / entity_label
        if entities_dir.exists():
            for folder in sorted(entities_dir.iterdir()):
                if not folder.is_dir():
                    continue
                seen = set()
                for f in sorted(folder.iterdir()):
                    if f.is_dir() and f.name.startswith("v"):
                        for img in sorted(f.iterdir()):
                            if img.is_file() and img.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                                if img.name not in seen:
                                    seen.add(img.name)
                                    file_path = f"projects/{name}/{entity_label}/{folder.name}/{f.name}/{img.name}"
                                    assets[entity_type].append({"name": folder.name, "file": file_path, "from_generated": True})
                    elif f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        if f.name not in seen:
                            seen.add(f.name)
                            file_path = f"projects/{name}/{entity_label}/{folder.name}/{f.name}"
                            assets[entity_type].append({"name": folder.name, "file": file_path, "from_generated": True})

    return assets


@router.get("/projects/{name}/characters")
def list_characters(name: str):
    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    return VisualBibleExtractor.list_characters(project)


@router.get("/projects/{name}/characters/{char_name}/variants")
def list_character_variants(name: str, char_name: str):
    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    return VisualBibleExtractor.list_variants(project, char_name)


@router.get("/projects/{name}/scenes/{scene_name}/variants")
def list_scene_variants(name: str, scene_name: str):
    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    return VisualBibleExtractor.list_scene_variants(project, scene_name)


@router.get("/projects/{name}/scenes")
def list_scenes(name: str):
    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    return VisualBibleExtractor.list_scenes(project)


@router.get("/projects/{name}/props")
def list_props(name: str):
    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    return VisualBibleExtractor.list_props(project)


@router.post("/projects/{name}/generate-prompt")
def generate_selection_prompt(name: str, body: dict):
    from core.project_manager import ProjectManager
    from agents.prompt_factory import PromptBuilder
    project = ProjectManager(name)
    char_names = body.get("character_names", [])
    scene_names = body.get("scene_names", [])
    prompt = PromptBuilder.generate_prompt_for_selection(project, char_names, scene_names)
    return {"prompt": prompt}


@router.get("/projects/{name}/prompts")
def get_project_prompts(name: str):
    """读取管线已生成的三类提示词文件"""
    project_dir = PROJECTS_DIR / name
    result = {"character_prompts": {}, "scene_prompts": {}, "storyboard_prompt": ""}

    char_file = project_dir / "06_提示词" / "角色提示词.md"
    if char_file.exists():
        text = char_file.read_text(encoding="utf-8")
        import re
        sections = re.split(r'^###\s+', text, flags=re.MULTILINE)
        for s in sections:
            s = s.strip()
            if not s:
                continue
            lines = s.split("\n", 1)
            name_key = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            result["character_prompts"][name_key] = content

    scene_file = project_dir / "06_提示词" / "场景提示词.md"
    if scene_file.exists():
        text = scene_file.read_text(encoding="utf-8")
        import re
        sections = re.split(r'^###\s+', text, flags=re.MULTILINE)
        for s in sections:
            s = s.strip()
            if not s:
                continue
            lines = s.split("\n", 1)
            name_key = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            result["scene_prompts"][name_key] = content

    sb_file = project_dir / "06_提示词" / "分镜提示词.md"
    if sb_file.exists():
        result["storyboard_prompt"] = sb_file.read_text(encoding="utf-8")

    return result


@router.post("/projects/{name}/prop-prompt")
def get_prop_prompt(name: str, body: dict):
    """根据道具 JSON 实时生成道具提示词"""
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    from agents.prompt_factory import PromptBuilder, _build_style_declaration
    from core.style_config import StyleConfig

    project = ProjectManager(name)
    char_name = body.get("character_name", "")
    prop_name = body.get("prop_name", "")
    props = VisualBibleExtractor.list_props(project)
    prop = next((p for p in props if p["name"] == prop_name), None)
    if not prop:
        raise HTTPException(status_code=404, detail="道具不存在")
    prompt = PromptBuilder.generate_prop_prompt(prop)
    style = StyleConfig.from_mapping(project.config)
    style_decl = _build_style_declaration(style)
    return {"prompt": prompt, "style_decl": style_decl, "prop_name": prop_name, "prop_class": prop.get("prop_class", "")}


@router.get("/projects/{name}/props-summary")
def get_props_summary(name: str):
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor

    project = ProjectManager(name)
    chars = VisualBibleExtractor.list_characters(project)
    prop_map: dict[str, set] = {}
    for c in chars:
        for acc in c.get("accessories", []):
            pname = acc.get("name", "")
            if not pname:
                continue
            if pname not in prop_map:
                prop_map[pname] = {"shared_by": [], "appearance": acc.get("appearance", ""), "style": acc.get("style", "")}
            prop_map[pname]["shared_by"].append(c["name"])
    result = []
    for pname, info in prop_map.items():
        result.append({"name": pname, "shared_by": info["shared_by"], "appearance": info["appearance"], "style": info["style"]})
    result.sort(key=lambda x: len(x["shared_by"]), reverse=True)
    return {"props": result}


@router.post("/projects/{name}/analyze-style-reference")
async def analyze_style_reference(name: str, file: UploadFile = File(...)):
    """用 Gemini 多模态分析上传的参考图，提取画风特征"""
    from core.project_manager import ProjectManager
    import base64 as b64

    project = ProjectManager(name)
    image_bytes = await file.read()
    image_b64 = b64.b64encode(image_bytes).decode()

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
        'raw_keywords: 完整的逗号分隔视觉关键词'
    )

    try:
        import requests
        base_url = agg.get('base_url', '').rstrip('/')
        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                {"type": "text", "text": analysis_prompt}
            ]
        }]
        resp = requests.post(
            f"{base_url}/v1/chat/completions",
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


@router.get("/projects/{name}/video-clips")
def list_video_clips(name: str):
    project_dir = PROJECTS_DIR / name
    clips = []
    video_base = project_dir / "07_生成素材" / "视频"
    if video_base.exists():
        for f in sorted(video_base.rglob("镜头*.mp4")):
            clips.append({"name": f.stem, "file": str(f.relative_to(project_dir))})

    output_file = video_base / "成片" / "全片.mp4"
    final_clip = None
    if output_file.exists():
        final_clip = {"name": "成片", "file": str(output_file.relative_to(project_dir))}

    return {"clips": clips, "final": final_clip}


@router.put("/projects/{name}/config")
def update_project_config(name: str, body: dict):
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    project.config.update(body)
    project.save_config()
    return {"updated": True}


@router.put("/projects/{name}/rename")
def rename_project(name: str, body: dict):
    new_name = body.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="新名称不能为空")
    if "/" in new_name or "\\" in new_name or ".." in new_name:
        raise HTTPException(status_code=400, detail="名称包含非法字符")
    old_dir = PROJECTS_DIR / name
    if not old_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    new_dir = PROJECTS_DIR / new_name
    if new_dir.exists():
        raise HTTPException(status_code=400, detail=f"项目「{new_name}」已存在")
    import shutil
    shutil.move(str(old_dir), str(new_dir))
    config_file = new_dir / "project_config.json"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        config["name"] = new_name
        config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"name": new_name, "renamed": True}


@router.get("/projects/{name}/media/{subpath:path}")
def get_media_file(name: str, subpath: str):
    project_dir = PROJECTS_DIR / name
    file_path = project_dir / subpath
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(str(file_path), media_type=media_type)


TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


@router.post("/projects/{name}/re-extract-visual")
def re_extract_visual(name: str):
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    project = ProjectManager(name)
    data = VisualBibleExtractor.extract_all(project)
    return {"characters": len(data.get("characters", [])), "scenes": len(data.get("scenes", []))}


@router.post("/projects/{name}/re-analyze-demands")
def re_analyze_demands(name: str):
    from core.project_manager import ProjectManager
    from core.style_config import StyleConfig
    from agents.image_preparator import ImagePreparator
    project = ProjectManager(name)
    style = StyleConfig.from_mapping(project.config)
    preparator = ImagePreparator()
    result = preparator.prepare(project, style)
    return {"characters": len(result.get("characters", [])), "scenes": len(result.get("scenes", [])), "total_shots": result.get("total_shots", 0)}


@router.post("/projects/{name}/save-template")
def save_project_as_template(name: str, template_name: str = ""):
    project_dir = PROJECTS_DIR / name
    config_file = project_dir / "project_config.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    tname = template_name or name
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    template = {
        "name": tname,
        "story_type": config.get("style_type", ""),
        "genre": config.get("genre", ""),
        "writing_style": config.get("writing_style", ""),
        "visual_style": config.get("visual_style", ""),
        "art_style": config.get("art_style", ""),
        "screen_aspect": config.get("screen_aspect", ""),
        "script_style": config.get("script_style", ""),
        "script_format": config.get("script_format", ""),
        "duration_mode": config.get("duration_mode", "1"),
        "custom_requirements": "",
    }
    path = TEMPLATES_DIR / f"{tname}.json"
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    demand_dir = project_dir / "06_生图需求"
    if not demand_dir.exists():
        demand_dir = project_dir / "07_生图需求"
    if demand_dir.exists():
        import shutil
        template_demand = TEMPLATES_DIR / f"{tname}_demand"
        if template_demand.exists():
            shutil.rmtree(str(template_demand))
        shutil.copytree(str(demand_dir), str(template_demand), dirs_exist_ok=True)

    return {"saved": True, "name": tname}


@router.get("/projects/{name}/export-novel")
def export_novel(name: str):
    project_dir = PROJECTS_DIR / name
    config_file = project_dir / "project_config.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="项目不存在")

    parts = []
    dirs = [
        ("01_故事大纲", "故事大纲.md"),
        ("02_完整剧情", "完整剧情.md"),
        ("03_完整剧本", "完整剧本.md"),
    ]

    title = name
    try:
        cfg = json.loads(config_file.read_text(encoding="utf-8"))
        title = cfg.get("name", name)
    except:
        pass

    parts.append(f"# {title}\n\n")

    for dir_name, file_name in dirs:
        dir_path = project_dir / dir_name
        if not dir_path.exists():
            continue
        main_file = dir_path / file_name
        if main_file.exists():
            content = main_file.read_text(encoding="utf-8")
            parts.append(content)
            parts.append("\n\n")
        else:
            for md in sorted(dir_path.glob("*.md")):
                parts.append(md.read_text(encoding="utf-8"))
                parts.append("\n\n")

    full_text = "".join(parts)

    from fastapi.responses import Response
    safe_name = "".join(c for c in title if c.isalnum() or c in "._- ") or "novel"
    return Response(
        content=full_text.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={safe_name}.md"},
    )


@router.post("/projects/{name}/visual-extract")
def run_visual_extract(name: str):
    """分段提取角色/场景"""
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    project = ProjectManager(name)
    data = VisualBibleExtractor.extract_all(project)
    return {"characters": len(data.get("characters", [])), "scenes": len(data.get("scenes", []))}


@router.post("/projects/{name}/visual-extract/confirm")
def confirm_visual_extract(name: str):
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    project = ProjectManager(name)
    VisualBibleExtractor.confirm_all(project)
    return {"confirmed": True}


@router.post("/projects/{name}/visual-extract/characters")
def add_visual_character(name: str, character_name: str):
    """增量补全单个角色"""
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    project = ProjectManager(name)
    data = VisualBibleExtractor.extract_character(project, character_name)
    if data:
        return {"character": data}
    raise HTTPException(status_code=400, detail="提取失败")


@router.put("/projects/{name}/visual-extract/characters/{char_name}")
def update_visual_character(name: str, char_name: str, body: dict):
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    project = ProjectManager(name)
    data = VisualBibleExtractor.update_character(project, char_name, body)
    if data:
        return {"character": data}
    raise HTTPException(status_code=404, detail="角色不存在")


@router.delete("/projects/{name}/visual-extract/characters/{char_name}")
def delete_visual_character(name: str, char_name: str):
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    project = ProjectManager(name)
    VisualBibleExtractor.delete_character(project, char_name)
    return {"deleted": True}


@router.get("/templates")
def list_templates():
    if not TEMPLATES_DIR.exists():
        return []
    result = []
    for f in sorted(TEMPLATES_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        data = json.loads(f.read_text(encoding="utf-8"))
        result.append(data)
    return result


@router.delete("/templates/{template_name}")
def delete_template(template_name: str):
    path = TEMPLATES_DIR / f"{template_name}.json"
    if path.exists():
        path.unlink()
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="模板不存在")


@router.post("/projects/{name}/character-prompt")
def get_character_prompt(name: str, body: dict):
    """根据角色 JSON 实时拼装提示词，替代从 06_提示词/角色提示词.md 读取"""
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    from agents.prompt_factory import PromptBuilder, _build_style_declaration
    from core.style_config import StyleConfig

    project = ProjectManager(name)
    char_name = body.get("character_name", "")
    if not char_name:
        raise HTTPException(status_code=400, detail="character_name is required")

    # 读取角色 JSON
    chars = VisualBibleExtractor.list_characters(project)
    char = next((c for c in chars if c["name"] == char_name), None)
    if not char:
        raise HTTPException(status_code=404, detail=f"角色 '{char_name}' 未找到")

    # 读取风格配置
    style = StyleConfig.from_mapping(project.config)
    style_decl = _build_style_declaration(style)

    # 拼装提示词
    prompt = PromptBuilder.generate_character_prompt(char, style_decl, mode="base")

    # 如果是变体，返回 base_character
    base_character = None
    if not char.get("is_base", True):
        base_character = char.get("character_base") or char.get("based_on")

    return {"prompt": prompt, "style_decl": style_decl, "base_character": base_character}


@router.get("/projects/{name}/character-confirmed-images/{characterName}")
def get_character_confirmed_images(name: str, characterName: str):
    char_dir = PROJECTS_DIR / name / "07_生成素材" / "角色" / characterName
    if not char_dir.exists():
        return {"images": []}

    # 先检查实体根目录 _confirmed（来自 confirm_version）
    root_confirmed = char_dir / "_confirmed"
    if root_confirmed.exists():
        target_version = root_confirmed.read_text().strip().lstrip("v")
        for d in char_dir.iterdir():
            if d.is_dir() and d.name == f"v{target_version}":
                (d / "_confirmed").touch(exist_ok=True)
        # 找对应版本目录
        version_dir = char_dir / f"v{target_version}"
        if version_dir.exists() and version_dir.is_dir():
            images = []
            for f in sorted(version_dir.glob("*.png")):
                url = f"/api/gen-files/projects/{name}/角色/{characterName}/v{target_version}/{f.name}"
                images.append({"url": url, "name": f.name, "version": f"v{target_version}"})
            return {"images": images, "version": f"v{target_version}"}

    # 再检查版本子目录内的 _confirmed（来自自动确认或手动 touch）
    confirmed_version = None
    for d in char_dir.iterdir():
        if d.is_dir() and (d / "_confirmed").exists():
            confirmed_version = d.name
            break

    if not confirmed_version:
        versions = sorted([d for d in char_dir.iterdir() if d.is_dir() and d.name.startswith("v")],
                          key=lambda d: d.stat().st_mtime, reverse=True)
        if not versions:
            return {"images": []}
        target_version = versions[0].name
    else:
        target_version = confirmed_version

    version_dir = char_dir / target_version
    images = []
    for f in sorted(version_dir.glob("*.png")):
        url = f"/api/gen-files/projects/{name}/角色/{characterName}/{target_version}/{f.name}"
        images.append({"url": url, "name": f.name, "version": target_version})

    return {"images": images, "version": target_version}


@router.post("/projects/{name}/scene-prompt")
def get_scene_prompt(name: str, body: dict):
    """根据场景 JSON 实时拼装提示词，替代从 06_提示词/场景提示词.md 读取"""
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    from agents.prompt_factory import PromptBuilder, _build_style_declaration
    from core.style_config import StyleConfig

    project = ProjectManager(name)
    scene_name = body.get("scene_name", "")
    if not scene_name:
        raise HTTPException(status_code=400, detail="scene_name is required")

    scenes = VisualBibleExtractor.list_scenes(project)
    scene = next((s for s in scenes if s["name"] == scene_name), None)
    if not scene:
        raise HTTPException(status_code=404, detail=f"场景 '{scene_name}' 未找到")

    style = StyleConfig.from_mapping(project.config)
    style_decl = _build_style_declaration(style)

    prompt = PromptBuilder.generate_scene_prompt(scene, angle=body.get("view_direction", "正视图"))

    base_scene = None
    if not scene.get("is_base", True):
        base_scene = scene.get("scene_base") or scene.get("based_on")

    return {"prompt": prompt, "style_decl": style_decl, "base_scene": base_scene}


@router.get("/projects/{name}/scene-confirmed-images/{sceneName}")
def get_scene_confirmed_images(name: str, sceneName: str):
    scene_dir = PROJECTS_DIR / name / "07_生成素材" / "场景" / sceneName
    if not scene_dir.exists():
        return {"images": []}

    confirmed_version = None
    for d in scene_dir.iterdir():
        if d.is_dir() and (d / "_confirmed").exists():
            confirmed_version = d.name
            break

    if not confirmed_version:
        versions = sorted([d for d in scene_dir.iterdir() if d.is_dir() and d.name.startswith("v")],
                          key=lambda d: d.stat().st_mtime, reverse=True)
        if not versions:
            return {"images": []}
        target_version = versions[0].name
    else:
        target_version = confirmed_version

    version_dir = scene_dir / target_version
    images = []
    for f in sorted(version_dir.glob("*.png")):
        url = f"/api/gen-files/projects/{name}/场景/{sceneName}/{target_version}/{f.name}"
        images.append({"url": url, "name": f.name, "version": target_version})

    return {"images": images, "version": target_version}


@router.post("/projects/{name}/characters/retro-split")
def retroactively_split_characters(name: str):
    """扫描所有现有角色 JSON，将 clothing/pose 中有跨场次变化的角色自动拆分为变体 JSON 文件"""
    import json
    import re

    from core.visual_bible import VisualBibleExtractor
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    chars_dir = VisualBibleExtractor._get_visual_dir(project, "角色")
    if not chars_dir.exists():
        return {"status": "skipped", "reason": "角色目录不存在"}

    # 从磁盘直接读取原始 JSON
    created = []
    for f in sorted(chars_dir.glob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        if not raw.get("is_base", True):
            continue  # 跳过已存在的变体
        name = raw["name"]
        clothing = raw.get("clothing", "")
        pose = raw.get("pose", "")
        appearance = raw.get("appearance", "")
        has_variant = False

        # 检查 clothing 是否有跨场次变化
        cm = re.search(r'(?:第一场|前期|白天|平时)[^，。]*?穿(.*?)(?:[，。].*?(?:第二场|后期|夜晚|战斗)[^，。]*?穿(.*))', clothing)
        if cm and cm.group(2):
            base_clothing = cm.group(1).strip()
            variant_clothing = cm.group(2).strip()
            raw["clothing"] = base_clothing

            v = dict(raw)
            vname = f"{name}_{variant_clothing[:4]}"
            v["name"] = vname
            v["is_base"] = False
            v["character_base"] = name
            v["variant_name"] = variant_clothing[:10]
            v["clothing_change"] = f"换穿{variant_clothing}"
            v["trigger_event"] = "场景切换"
            v.pop("variants", None)
            v.pop("_file", None)
            (chars_dir / f"{vname}.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
            created.append(vname)
            has_variant = True

        # 检查 pose 是否有跨场次变化
        pm = re.search(r'(?:第一场|前期|白天|平时)[^，。]*?([\u4e00-\u9fff].*?)(?:[，。].*?(?:第二场|后期|夜晚|战斗)[^，。]*?([\u4e00-\u9fff].*))', pose)
        if pm and pm.group(2):
            base_pose = pm.group(1).strip()
            variant_pose = pm.group(2).strip()
            raw["pose"] = base_pose

            if has_variant:
                # 补充到已有变体
                vname = f"{name}_{variant_clothing[:4]}"
                vpath = chars_dir / f"{vname}.json"
                if vpath.exists():
                    vdata = json.loads(vpath.read_text(encoding="utf-8"))
                    vdata["pose_change"] = variant_pose
                    vpath.write_text(json.dumps(vdata, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                v = dict(raw)
                vname = f"{name}_第二场"
                v["name"] = vname
                v["is_base"] = False
                v["character_base"] = name
                v["variant_name"] = variant_pose[:10]
                v["pose_change"] = variant_pose
                v["trigger_event"] = "场景切换"
                v.pop("variants", None)
                v.pop("_file", None)
                (chars_dir / f"{vname}.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
                created.append(vname)

        if has_variant or (pm and pm.group(2)):
            # 写回修改后的基础角色
            raw.pop("_file", None)
            f.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"status": "ok", "created_variants": created}


@router.get("/projects/{name}/asset-library")
def get_project_asset_library(name: str):
    base_dir = PROJECTS_DIR / name / "07_生成素材"
    result = {"characters": {}, "scenes": {}, "props": {}}

    for entity_type, entity_label in [("characters", "角色"), ("scenes", "场景"), ("props", "道具")]:
        type_dir = base_dir / entity_label
        if not type_dir.exists():
            continue
        for entity_dir in sorted(type_dir.iterdir()):
            if not entity_dir.is_dir():
                continue
            entity_name = entity_dir.name
            confirmed_versions = []
            all_versions = []

            for vdir in sorted(entity_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
                if not vdir.is_dir() or not vdir.name.startswith("v"):
                    continue
                version_info = {
                    "version": vdir.name,
                    "confirmed": (vdir / "_confirmed").exists(),
                    "images": []
                }
                for f in sorted(vdir.glob("*.png")):
                    url = f"/api/gen-files/projects/{name}/{entity_label}/{entity_name}/{vdir.name}/{f.name}"
                    version_info["images"].append({"url": url, "name": f.name})
                all_versions.append(version_info)
                if version_info["confirmed"]:
                    confirmed_versions.append(version_info)

            if all_versions:
                result[entity_type][entity_name] = {
                    "confirmed_versions": confirmed_versions,
                    "all_versions": all_versions,
                    "latest_confirmed": confirmed_versions[0] if confirmed_versions else (all_versions[0] if all_versions else None),
                }

    return result
