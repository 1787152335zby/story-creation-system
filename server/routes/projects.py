import json
import subprocess
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File

def _natsort_key(path):
    name = path.name
    nums = re.findall(r'\d+', name)
    return (0, int(nums[0])) if nums else (1, name)
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
        for subdir in sorted(phase_path.iterdir(), key=_natsort_key):
            if subdir.is_dir():
                sub_md.extend(subdir.glob("*.md"))
        md_files = root_md + sub_md
        md_files = [f for f in md_files if not f.name.startswith("分镜提示词")]
        stems_with_ji = {f.stem for f in md_files if f.stem.endswith('集')}
        md_files = [f for f in md_files if not (f.stem + '集' in stems_with_ji)]
        cn_char = dict(zip('一二三四五六七八九十百千', [1,2,3,4,5,6,7,8,9,10,100,1000]))

        def _cn_to_num(s):
             s = s.replace('零', '')
             total = 0; base = 0
             for ch in s:
                 if ch in cn_char:
                     v = cn_char[ch]
                     if v >= 10:
                         if base == 0:
                             base = 1
                         total += base * v
                         base = 0
                     else:
                         base = v
             return total + base

        def sort_key(f):
            name = f.stem
            cn_match = re.search(r'[一二三四五六七八九十百千]+', name)
            if cn_match:
                return (0, _cn_to_num(cn_match.group()))
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


def _md_to_html(text: str) -> str:
    is_table = False
    lines_out = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            if is_table:
                lines_out.append("</table>")
                is_table = False
            lines_out.append("<br/>")
            continue
        if stripped.startswith("### "):
            if is_table:
                lines_out.append("</table>")
                is_table = False
            lines_out.append(f"<h3>{_inline_md(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            if is_table:
                lines_out.append("</table>")
                is_table = False
            lines_out.append(f"<h2>{_inline_md(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            if is_table:
                lines_out.append("</table>")
                is_table = False
            lines_out.append(f"<h1>{_inline_md(stripped[2:])}</h1>")
        elif stripped.startswith("|") and stripped.endswith("|"):
            if not is_table:
                lines_out.append('<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse">')
                is_table = True
            cells = stripped.split("|")[1:-1]
            tag = "th" if re.match(r'^[\s\-:|]+$', stripped) else "td"
            if tag == "th":
                continue
            row = "".join(f"<{tag}>{_inline_md(c.strip())}</{tag}>" for c in cells)
            lines_out.append(f"<tr>{row}</tr>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            lines_out.append(f"<li>{_inline_md(stripped[2:])}</li>")
        elif stripped == "---":
            lines_out.append("<hr/>")
        else:
            lines_out.append(f"<p>{_inline_md(stripped)}</p>")
    if is_table:
        lines_out.append("</table>")
    return "\n".join(lines_out)


def _inline_md(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    return text


def _is_dialogue_line(text: str) -> bool:
    return bool(text) and (text[0] == '"' or text[0] == '\u201c' or text[0] == '\u2018')


def _system_script_to_market(text: str) -> str:
    lines = text.split('\n')
    out = []
    ep_num = 0
    scene_num = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        m = re.match(r'^#{1,3}\s*第(\d+)集', stripped)
        if m:
            ep_num = int(m.group(1))
            scene_num = 0
            out.append(f'第{ep_num}集')
            out.append('')
            i += 1
            continue

        m = re.match(r'^###\s*第(\d+)场\s*[-—]\s*(.+)$', stripped)
        if m:
            scene_num = int(m.group(1))
            location_full = m.group(2).strip()
            parts = re.split(r'\s*[·•]\s*', location_full, maxsplit=1)
            location = parts[0]
            time_str = parts[1] if len(parts) > 1 else '白天'
            out.append(f'{ep_num}-{scene_num} {time_str} 内 {location}')
            out.append('')
            i += 1
            continue

        if stripped.startswith('出场角色：'):
            content = stripped[len('出场角色：'):]
            out.append(f'出场人物：{content}')
            out.append('')
            i += 1
            continue

        if stripped == '---':
            out.append('')
            i += 1
            continue

        if not stripped:
            out.append('')
            i += 1
            continue

        if stripped.startswith('#') or stripped.startswith('▶'):
            out.append(stripped)
            i += 1
            continue

        j, merged = _try_merge_dialogue(lines, i, stripped)
        if merged:
            out.append(merged)
            i = j
            continue

        if stripped.startswith('（'):
            j, merged = _try_merge_multiline_action(lines, i)
            if merged:
                out.append(merged)
                i = j
                continue
            if stripped.endswith('）'):
                action = stripped[1:-1]
                out.append(f'▶ {action}')
                i += 1
                continue

        out.append(stripped)
        i += 1

    return '\n'.join(out)


def _try_merge_dialogue(lines, i, stripped):
    inline_emotion = re.match(r'^(.+?)（(.+?)）$', stripped)
    if inline_emotion:
        char_name = inline_emotion.group(1)
        emotion1 = inline_emotion.group(2)
        j = i + 1
        emotion2 = ''
        if j < len(lines) and lines[j].strip().startswith('（') and lines[j].strip().endswith('）'):
            emotion2 = lines[j].strip()[1:-1]
            j += 1
        if j < len(lines) and _is_dialogue_line(lines[j].strip()):
            dialogue = lines[j].strip()
            j += 1
            full_emotion = f'{emotion1}，{emotion2}' if emotion2 else emotion1
            return j, f'{char_name}（{full_emotion}）：{dialogue}'
        return i, None

    j = i + 1
    emotion = ''
    if j < len(lines) and lines[j].strip().startswith('（') and lines[j].strip().endswith('）'):
        emotion = lines[j].strip()[1:-1]
        j += 1
    if j < len(lines) and _is_dialogue_line(lines[j].strip()):
        dialogue = lines[j].strip()
        j += 1
        if emotion:
            return j, f'{stripped}（{emotion}）：{dialogue}'
        else:
            return j, f'{stripped}：{dialogue}'

    return i, None


def _try_merge_multiline_action(lines, i):
    stripped = lines[i].strip()
    if not stripped.startswith('（'):
        return i, None
    if stripped.endswith('）'):
        return i, None
    j = i + 1
    while j < len(lines):
        ls = lines[j].strip()
        if not ls:
            j += 1
            continue
        if _is_dialogue_line(ls) or re.match(r'^#{1,3}\s', ls) or re.match(r'^出场角色：', ls) or ls == '---':
            return i, None
        if ls.endswith('）'):
            part = stripped[1:]
            for k in range(i + 1, j):
                if lines[k].strip():
                    part += lines[k].strip()
            part += ls[:-1]
            return j + 1, f'▶ {part}'
        j += 1
    return i, None


def _market_to_html(text: str) -> str:
    lines = text.split('\n')
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out_lines.append('<br/>')
            continue
        if re.match(r'^第\d+集$', stripped):
            out_lines.append(f'<h2>{stripped}</h2>')
            continue
        if re.match(r'^\d+-\d+\s+', stripped):
            out_lines.append(f'<h3>{stripped}</h3>')
            continue
        if stripped.startswith('出场人物：'):
            out_lines.append(f'<p><b>{stripped}</b></p>')
            continue
        out_lines.append(f'<p>{stripped}</p>')
    return '\n'.join(out_lines)


def _should_use_market_format(project_dir: Path, phase_or_path: str) -> bool:
    config_file = project_dir / "project_config.json"
    if not config_file.exists():
        return False
    try:
        cfg = json.loads(config_file.read_text(encoding="utf-8"))
    except Exception:
        return False
    if cfg.get("script_format", "1") != "2":
        return False
    path_lower = phase_or_path.lower().replace('\\', '/')
    is_script = '剧本' in path_lower or '03_' in path_lower or 'script' in path_lower
    return is_script


@router.get("/projects/{name}/{phase:path}/export-docx")
def export_phase_docx(name: str, phase: str):
    from fastapi.responses import Response
    project_dir = PROJECTS_DIR / name
    phase_path = project_dir / phase
    if not phase_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    if phase_path.is_dir():
        root_md = list(phase_path.glob("*.md"))
        sub_md = []
        for subdir in sorted(phase_path.iterdir(), key=_natsort_key):
            if subdir.is_dir():
                sub_md.extend(subdir.glob("*.md"))
        md_files = root_md + sub_md
        md_files = [f for f in md_files if not f.name.startswith("分镜提示词")]
        parts = [mf.read_text(encoding="utf-8") for mf in md_files]
        full_text = "\n\n---\n\n".join(parts)
    else:
        full_text = phase_path.read_text(encoding="utf-8")

    use_market = _should_use_market_format(project_dir, phase)
    if use_market:
        full_text = _system_script_to_market(full_text)
        html_body = _market_to_html(full_text)
    else:
        html_body = _md_to_html(full_text)
    display_name = phase.rstrip("/").replace("\\", "/").split("/")[-1]

    docx_html = f"""<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"/>
<style>
body {{ font-family: 'Microsoft YaHei', 'SimSun', sans-serif; font-size: 12pt; line-height: 1.8; color: #222; max-width: 210mm; margin: 0 auto; padding: 20px; }}
h1 {{ font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 6px; }}
h2 {{ font-size: 15pt; }}
h3 {{ font-size: 13pt; }}
table {{ width: 100%; }}
p {{ margin: 6pt 0; }}
hr {{ border: 0; border-top: 1px solid #ccc; margin: 20px 0; }}
li {{ margin-left: 20px; }}
</style></head>
<body>
{html_body}
</body></html>"""

    filename = f"{name}_{display_name}.doc"
    return Response(
        content=docx_html.encode("utf-8"),
        media_type="application/msword",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects/{name}/export-batch")
def export_project_batch(name: str, phases: str = ""):
    """批量导出项目的多个阶段为单个 Word 文件。phases 用逗号分隔阶段名，如 01_故事大纲,03_完整剧本"""
    from fastapi.responses import Response
    from urllib.parse import quote

    project_dir = PROJECTS_DIR / name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")

    phase_list = [p.strip() for p in phases.split(",") if p.strip()]
    if not phase_list:
        raise HTTPException(status_code=400, detail="请指定要导出的阶段")

    all_parts: list[str] = []

    for phase in phase_list:
        phase_path = project_dir / phase
        if not phase_path.exists():
            continue

        if phase_path.is_dir():
            root_md = list(phase_path.glob("*.md"))
            sub_md = []
            for subdir in sorted(phase_path.iterdir(), key=_natsort_key):
                if subdir.is_dir():
                    sub_md.extend(subdir.glob("*.md"))
            md_files = root_md + sub_md
            md_files = [f for f in md_files if not f.name.startswith("分镜提示词")]
            parts = [mf.read_text(encoding="utf-8") for mf in md_files]
            text = "\n\n---\n\n".join(parts)
        else:
            text = phase_path.read_text(encoding="utf-8")

        use_market = _should_use_market_format(project_dir, phase)
        if use_market:
            text = _system_script_to_market(text)
            phase_html = _market_to_html(text)
        else:
            phase_html = _md_to_html(text)

        import re as _re
        phase_label = _re.sub(r'^\d+_', '', phase)
        all_parts.append(f"<h1>{phase_label}</h1>\n{phase_html}")

    if not all_parts:
        raise HTTPException(status_code=404, detail="所选阶段没有内容")

    html_body = "\n<hr style='border:2px solid #333; margin:30px 0;'/>\n".join(all_parts)

    docx_html = f"""<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"/>
<style>
body {{ font-family: 'Microsoft YaHei', 'SimSun', sans-serif; font-size: 12pt; line-height: 1.8; color: #222; max-width: 210mm; margin: 0 auto; padding: 20px; }}
h1 {{ font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 6px; page-break-before: always; }}
h1:first-child {{ page-break-before: auto; }}
h2 {{ font-size: 15pt; }}
h3 {{ font-size: 13pt; }}
table {{ width: 100%; }}
p {{ margin: 6pt 0; }}
hr {{ border: 0; border-top: 1px solid #ccc; margin: 20px 0; }}
li {{ margin-left: 20px; }}
</style></head>
<body>
{html_body}
</body></html>"""

    filename = f"{name}_全集.doc"
    encoded_filename = quote(filename)
    return Response(
        content=docx_html.encode("utf-8"),
        media_type="application/msword",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


def _collect_project_phases(project_dir: Path) -> list[str]:
    """收集项目下所有存在内容的阶段目录名"""
    phases = []
    for d in sorted(project_dir.iterdir()):
        if d.is_dir() and (d / ".md").exists() if False else any(d.glob("*.md")):
            phases.append(d.name)
    if not phases:
        for d in sorted(project_dir.iterdir()):
            if d.is_dir():
                has_md = any(d.glob("*.md"))
                for sd in sorted(d.iterdir()):
                    if sd.is_dir() and any(sd.glob("*.md")):
                        has_md = True
                        break
                if has_md:
                    phases.append(d.name)
    return phases


@router.get("/projects/{name}/phases")
def list_project_phases(name: str):
    """返回项目下所有有内容的阶段目录，含阶段标签和每阶段内的文件列表"""
    project_dir = PROJECTS_DIR / name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="项目不存在")

    phase_labels = {
        "01_故事大纲": "故事大纲",
        "02_完整剧情": "完整剧情",
        "03_完整剧本": "完整剧本",
        "04_角色场景": "角色场景",
        "05_分镜脚本": "分镜脚本",
        "06_生图需求": "生图需求",
        "07_生成素材": "生成素材",
    }

    phases = []
    for d in sorted(project_dir.iterdir()):
        if d.is_dir() and d.name[0].isdigit():
            md_files = list(d.rglob("*.md"))
            content_count = len(md_files)
            if content_count == 0 and not any(True for _ in d.rglob("*.png")):
                continue
            phase_files = []
            for mf in sorted(md_files):
                if mf.name.startswith("分镜提示词"):
                    continue
                rel = mf.relative_to(d).as_posix()
                parent_dir = mf.parent.relative_to(d).as_posix()
                if parent_dir and parent_dir != ".":
                    label = f"{parent_dir} — {mf.stem}"
                else:
                    label = mf.stem
                phase_files.append({"name": rel, "label": label})
            phases.append({
                "dir": d.name,
                "label": phase_labels.get(d.name, d.name),
                "has_content": content_count > 0,
                "files": phase_files,
            })

    return {"phases": phases}


@router.get("/projects/{name}/export-single")
def export_single_file(name: str, phase: str = "", file: str = ""):
    """导出项目内单个 MD 文件为 Word"""
    from fastapi.responses import Response
    from urllib.parse import quote

    project_dir = PROJECTS_DIR / name
    phase_path = project_dir / phase
    file_path = phase_path / file if phase else project_dir / file

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    text = file_path.read_text(encoding="utf-8")
    use_market = _should_use_market_format(project_dir, phase)
    if use_market:
        text = _system_script_to_market(text)
        html_body = _market_to_html(text)
    else:
        html_body = _md_to_html(text)

    docx_html = f"""<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"/>
<style>
body {{ font-family: 'Microsoft YaHei', 'SimSun', sans-serif; font-size: 12pt; line-height: 1.8; color: #222; max-width: 210mm; margin: 0 auto; padding: 20px; }}
h1 {{ font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 6px; }}
h2 {{ font-size: 15pt; }}
h3 {{ font-size: 13pt; }}
table {{ width: 100%; }}
p {{ margin: 6pt 0; }}
hr {{ border: 0; border-top: 1px solid #ccc; margin: 20px 0; }}
li {{ margin-left: 20px; }}
</style></head>
<body>
{html_body}
</body></html>"""
    stem = file_path.stem
    fn = f"{name}_{stem}.doc"
    return Response(
        content=docx_html.encode("utf-8"),
        media_type="application/msword",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"},
    )


@router.get("/projects/{name}/export-phase")
def export_phase_all(name: str, phase: str = ""):
    """导出某个阶段的所有文件合并为一个 Word，每集之间用分页隔开"""
    from fastapi.responses import Response
    from urllib.parse import quote

    project_dir = PROJECTS_DIR / name
    phase_path = project_dir / phase
    if not phase_path.exists():
        raise HTTPException(status_code=404, detail="阶段不存在")

    md_files = list(phase_path.rglob("*.md"))
    md_files = [f for f in md_files if not f.name.startswith("分镜提示词")]
    if not md_files:
        raise HTTPException(status_code=404, detail="该阶段无内容")

    all_html: list[str] = []
    use_market = _should_use_market_format(project_dir, phase)
    for mf in sorted(md_files):
        rel = mf.relative_to(phase_path).as_posix()
        text = mf.read_text(encoding="utf-8")
        if use_market:
            text = _system_script_to_market(text)
            all_html.append(f"<h2>{rel}</h2>\n{_market_to_html(text)}")
        else:
            all_html.append(f"<h2>{rel}</h2>\n{_md_to_html(text)}")

    html_body = "\n<hr style='border:2px solid #333; margin:30px 0; page-break-after: always;'/>\n".join(all_html)

    phase_labels = {
        "01_故事大纲": "故事大纲", "02_完整剧情": "完整剧情", "03_完整剧本": "完整剧本",
        "04_角色场景": "角色场景", "05_分镜脚本": "分镜脚本", "06_生图需求": "生图需求",
    }
    phase_label = phase_labels.get(phase, phase)
    docx_html = f"""<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"/>
<style>
body {{ font-family: 'Microsoft YaHei', 'SimSun', sans-serif; font-size: 12pt; line-height: 1.8; color: #222; max-width: 210mm; margin: 0 auto; padding: 20px; }}
h1 {{ font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 6px; page-break-before: always; }}
h1:first-child {{ page-break-before: auto; }}
h2 {{ font-size: 15pt; border-bottom: 1px solid #ccc; padding-bottom: 4px; page-break-before: always; }}
h2:first-child {{ page-break-before: auto; }}
h3 {{ font-size: 13pt; }}
table {{ width: 100%; }}
p {{ margin: 6pt 0; }}
hr {{ border: 0; border-top: 1px solid #ccc; margin: 20px 0; }}
li {{ margin-left: 20px; }}
</style></head>
<body>
<h1>{phase_label}</h1>
{html_body}
</body></html>"""

    fn = f"{name}_{phase_label}.doc"
    return Response(
        content=docx_html.encode("utf-8"),
        media_type="application/msword",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"},
    )


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
            if not isinstance(acc, dict):
                continue
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


@router.get("/projects/{name}/video/shot-status")
def get_video_shot_status(name: str):
    project_dir = PROJECTS_DIR / name
    video_base = project_dir / "07_生成素材" / "视频"
    shot_statuses: dict[int, str] = {}
    shot_urls: dict[int, str] = {}
    if video_base.exists():
        for f in sorted(video_base.rglob("镜头*.mp4")):
            m = re.match(r"镜头(\d+)", f.stem)
            if m:
                idx = int(m.group(1))
                shot_statuses[idx] = "done"
                shot_urls[idx] = f"/api/projects/{name}/media/{f.relative_to(project_dir).as_posix()}"
    return {"shotStatuses": shot_statuses, "shotVideoUrls": shot_urls}


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

    # 如果是变体，返回 base_character 和 cross_ref
    base_character = None
    cross_ref = None
    if not char.get("is_base", True):
        base_character = char.get("character_base") or char.get("based_on")
    try:
        demand_file = project.project_dir / "06_生图需求" / "生图清单.json"
        if demand_file.exists():
            demands = json.loads(demand_file.read_text(encoding="utf-8"))
            for dc in demands.get("characters", []):
                if dc.get("name") == char_name:
                    base_character = base_character or dc.get("character_base")
                    cross_ref = dc.get("_cross_ref")
                    break
    except Exception:
        pass

    return {"prompt": prompt, "style_decl": style_decl, "base_character": base_character, "cross_ref": cross_ref}


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
