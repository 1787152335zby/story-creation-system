import json
import subprocess
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from ..schemas import CreateProjectRequest, StyleConfigRequest

router = APIRouter()
PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent / "projects"


def _build_project_list() -> list:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for item in PROJECTS_DIR.iterdir():
        if item.is_dir():
            config_file = item / "project_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                config["total_phases"] = len(config.get("phases", []))
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
        return json.load(f)


@router.get("/projects/{name}/{phase:path}/content")
def get_phase_content(name: str, phase: str):
    project_dir = PROJECTS_DIR / name
    phase_path = project_dir / phase
    if not phase_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    if phase_path.is_dir():
        md_files = list(phase_path.glob("*.md"))
        cn_num = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
        def sort_key(f):
            name = f.stem
            for cn, num in cn_num.items():
                if cn in name:
                    return (0, num)
            import re
            nums = re.findall(r'\d+', name)
            return (1, int(nums[0]) if nums else 0)
        md_files.sort(key=sort_key)
        if not md_files:
            raise HTTPException(status_code=404, detail="无内容")
        file_list = [f.name for f in md_files]
        parts = [mf.read_text(encoding="utf-8") for mf in md_files]
        return {"content": "\n\n---\n\n".join(parts), "is_split": True, "file_list": file_list}
    return {"content": phase_path.read_text(encoding="utf-8"), "is_split": False, "file_list": [phase_path.name]}


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
    project.config["duration_mode"] = req.style.duration_mode
    project.config["episode_count"] = req.style.episode_count
    project.config["episode_duration"] = req.style.episode_duration
    project.config["custom_requirements"] = req.style.custom_requirements
    project.config["visual_reference"] = req.style.visual_reference
    project.config["action_reference"] = req.style.action_reference
    project.save_config()

    return {"name": req.name, "status": "created"}


@router.post("/projects/random-idea")
def random_story_idea(style: StyleConfigRequest):
    from core.style_config import STORY_TYPES, WRITING_STYLES, VISUAL_STYLES, RENDER_STYLES, SCRIPT_STYLES, SCREEN_ASPECTS

    story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
    genre_name = style.genre or "未知"
    writing_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "未知")
    visual_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "未知")
    render_name = RENDER_STYLES.get(style.art_style, {}).get("name", "未知")
    script_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "未知")
    aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "未知")

    prompt = f"""你是一位专业的故事策划师。请根据以下配置，创作一段50-100字的故事描述，用于AI视频故事的创作起点。

故事类型：{story_type_name}
题材风格：{genre_name}
文笔风格：{writing_name}
视觉/叙事风格：{visual_name}
渲染画风：{render_name}
剧本写作风格：{script_name}
画面比例：{aspect_name}

要求：
1. 故事描述必须包含：一个核心角色 + 一个明确的困境/冲突 + 一个独特的场景设定
2. 语言简洁有力，50-100字
3. 直接输出故事描述，不要任何额外说明
4. 这是随机生成，不要写得太俗套"""

    from llm.client import LLMClient
    client = LLMClient()
    idea = client.chat(prompt, "", temperature=0.9, max_tokens=300)
    idea = idea.strip().strip('"').strip("'").strip('"""').strip("'''")
    return {"idea": idea}


@router.post("/projects/{name}/open")
def open_project_folder(name: str):
    project_dir = PROJECTS_DIR / name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        subprocess.Popen(["explorer", str(project_dir)])
        return {"opened": True, "path": str(project_dir)}
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


@router.put("/projects/{name}/config")
def update_project_config(name: str, body: dict):
    from core.project_manager import ProjectManager
    project = ProjectManager(name)
    project.config.update(body)
    project.save_config()
    return {"updated": True}


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
        "duration_mode": config.get("duration_mode", "1"),
        "custom_requirements": "",
    }
    path = TEMPLATES_DIR / f"{tname}.json"
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "name": tname}


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
