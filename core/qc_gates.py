"""QC Gates — 管线质控检查点"""

import json
import re
from pathlib import Path


def _get_visual_subdir(project_dir: Path, subpath: str = "") -> Path:
    path_04 = project_dir / "04_角色场景" / subpath
    path_05 = project_dir / "05_角色场景" / subpath
    if path_04.exists() and any(path_04.glob("*.json")):
        return path_04
    if path_05.exists() and any(path_05.glob("*.json")):
        return path_05
    return path_04


def check_g1_outline(project_dir: Path) -> list[str]:
    """G1: 故事大纲后 — 检查角色数、主线、冲突"""
    warnings = []
    chars_dir = _get_visual_subdir(project_dir, "角色")
    if not chars_dir.exists():
        warnings.append("G1: 缺少角色目录")
    else:
        chars = list(chars_dir.glob("*.json"))
        base_chars = [c for c in chars if "_" not in c.stem]
        if len(base_chars) < 2:
            warnings.append(f"G1: 仅有 {len(base_chars)} 个角色（建议 >= 2）")

    outline_file = project_dir / "01_故事大纲" / "故事大纲.md"
    if outline_file.exists():
        text = outline_file.read_text(encoding="utf-8")[:3000]
        if "冲突" not in text and "矛盾" not in text:
            warnings.append("G1: 大纲中未检测到冲突/矛盾元素")
    else:
        warnings.append("G1: 缺少故事大纲文件")

    return warnings


def check_g2_plot(project_dir: Path) -> list[str]:
    """G2: 剧情生成后 — 检查节拍、支线"""
    warnings = []
    plot_dir = project_dir / "02_完整剧情"
    if not plot_dir.exists():
        warnings.append("G2: 缺少剧情目录")
        return warnings

    files = sorted(plot_dir.glob("完整剧情*.md"))
    if not files:
        warnings.append("G2: 缺少剧情文件")
        return warnings

    for f in files:
        text = f.read_text(encoding="utf-8")
        beat_count = text.count("节拍") + text.count("场景")
        if beat_count < 3:
            warnings.append(f"G2: {f.name} 节拍数不足（{beat_count} < 3）")

    return warnings


def check_g3_script(project_dir: Path) -> list[str]:
    """G3: 剧本生成后 — 检查对白差异化"""
    warnings = []
    script_dir = project_dir / "03_完整剧本"
    if not script_dir.exists():
        warnings.append("G3: 缺少剧本目录")
        return warnings

    files = sorted(script_dir.glob("完整剧本*.md"))
    if not files:
        warnings.append("G3: 缺少剧本文件")
        return warnings

    for f in files:
        text = f.read_text(encoding="utf-8")
        dialog_count = text.count("：")
        action_count = text.count("（") + text.count("(")
        if dialog_count > 0 and action_count < dialog_count * 0.3:
            warnings.append(f"G3: {f.name} 动作描述偏少（对白 {dialog_count} 句，建议增加场景调度）")

    return warnings


def check_g4_visual(project_dir: Path) -> list[str]:
    """G4: 视觉提取后 — 检查角色/场景完整性"""
    warnings = []
    chars_dir = _get_visual_subdir(project_dir, "角色")
    if chars_dir.exists():
        for f in chars_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            if not data.get("appearance"):
                warnings.append(f"G4: {f.stem} 缺少外貌描述")
            if not data.get("clothing"):
                warnings.append(f"G4: {f.stem} 缺少服装描述")

    scenes_dir = _get_visual_subdir(project_dir, "场景")
    if scenes_dir.exists():
        for f in scenes_dir.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            if not data.get("environment"):
                warnings.append(f"G4: {f.stem} 缺少环境描述")

    return warnings


def check_g5_storyboard(project_dir: Path) -> list[str]:
    """G5: 分镜后 — 检查场景归属、时长"""
    warnings = []
    storyboard_dir = project_dir / "05_分镜脚本"
    if not storyboard_dir.exists():
        warnings.append("G5: 缺少分镜目录")
        return warnings

    files = sorted(storyboard_dir.glob("分镜脚本*.md"))
    if not files:
        warnings.append("G5: 缺少分镜文件")
        return warnings

    for f in files:
        text = f.read_text(encoding="utf-8")
        if "场景：" not in text and "场景:" not in text:
            warnings.append(f"G5: {f.name} 分镜未标注场景归属")

        long_shots = re.findall(r'\|\s*([5-9]\.\d+|[6-9]\d*\.?\d*)s?\s*\|', text)
        if long_shots:
            warnings.append(f"G5: {f.name} 有 {len(long_shots)} 个镜头时长超过 5 秒")

    return warnings


def check_g7_video(project_dir: Path) -> list[str]:
    warnings = []
    video_dir = project_dir / "07_生成素材" / "视频"
    if not video_dir.exists():
        warnings.append("G7: 缺少视频目录")
        return warnings

    videos = list(video_dir.rglob("*.mp4"))
    if not videos:
        warnings.append("G7: 未找到视频文件")

    return warnings


QC_CHECKS = {
    "outline_designer": check_g1_outline,
    "plot_expander": check_g2_plot,
    "screenplay_writer": check_g3_script,
    "visual_extractor": check_g4_visual,
    "storyboarder": check_g5_storyboard,
    "video_producer": check_g7_video,
}


def run_qc_check(agent_name: str, project_dir: Path) -> list[str]:
    """对指定阶段运行 QC 检查，返回警告列表"""
    check_fn = QC_CHECKS.get(agent_name)
    if check_fn:
        return check_fn(project_dir)
    return []
