from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api/prompt-gen")

PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent / "projects"


class PromptGenRequest(BaseModel):
    project_name: str
    character_names: list[str] = []
    scene_names: list[str] = []
    storyboard_chunk: str = ""


@router.post("/combined")
def generate_combined_prompt(req: PromptGenRequest):
    from core.project_manager import ProjectManager
    from agents.prompt_factory import PromptBuilder
    project = ProjectManager(req.project_name)
    prompt = PromptBuilder.generate_prompt_for_selection(
        project, req.character_names, req.scene_names, req.storyboard_chunk
    )
    return {"prompt": prompt}


@router.post("/character")
def generate_character_prompt(project_name: str, character_name: str):
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    from agents.prompt_factory import PromptBuilder
    project = ProjectManager(project_name)
    chars = VisualBibleExtractor.list_characters(project)
    char = next((c for c in chars if c["name"] == character_name), None)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"prompt": PromptBuilder.generate_character_prompt(char)}


@router.post("/scene")
def generate_scene_prompt(project_name: str, scene_name: str, angle: str = "正视图"):
    from core.project_manager import ProjectManager
    from core.visual_bible import VisualBibleExtractor
    from agents.prompt_factory import PromptBuilder
    project = ProjectManager(project_name)
    scenes = VisualBibleExtractor.list_scenes(project)
    scene = next((s for s in scenes if s["name"] == scene_name), None)
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    return {"prompt": PromptBuilder.generate_scene_prompt(scene, angle)}
