import re
from pathlib import Path


def extract_first_dialogue(project, character_name: str) -> str | None:
    """从剧本中提取角色的第一句对白"""
    script_dir = project.project_dir / "03_完整剧本"
    if not script_dir.exists():
        return None

    script_files = sorted(script_dir.glob("完整剧本*.md"))
    content = ""
    for f in script_files:
        content += f.read_text(encoding="utf-8")

    pattern = re.compile(
        rf'{re.escape(character_name)}\s*\n\s*（(?:.*?)）\s*\n\s*"([^"]+)"',
        re.MULTILINE,
    )
    match = pattern.search(content)
    if match:
        return match.group(1)

    simple_pattern = re.compile(
        rf'{re.escape(character_name)}\s*\n\s*"([^"]+)"',
        re.MULTILINE,
    )
    match = simple_pattern.search(content)
    if match:
        return match.group(1)

    return None


def list_audio_references(project):
    """列出项目中可用的角色音频参考文件"""
    audio_dir = project.project_dir / "07_视觉素材" / "角色音频"
    if not audio_dir.exists():
        return []
    refs = []
    for f in sorted(audio_dir.glob("*.wav")) + sorted(audio_dir.glob("*.mp3")):
        refs.append({"file": f.name, "character": f.stem})
    return refs
