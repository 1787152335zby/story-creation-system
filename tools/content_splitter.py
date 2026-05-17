import re
from typing import List, Tuple


def split_by_headings(content: str) -> List[Tuple[str, str]]:
    lines = content.split("\n")
    headings = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        act_match = re.match(r"^#{1,2}\s*(第[一二三四五六七八九十]+幕)", stripped)
        if act_match:
            headings.append((i, act_match.group(0).strip(), "act"))
            continue
        episode_match = re.match(r"^#\s*(第\d+集)", stripped)
        if episode_match:
            headings.append((i, episode_match.group(0).strip(), "episode"))
            continue
        chapter_match = re.match(r"^#\s*(第\d+章)", stripped)
        if chapter_match:
            headings.append((i, chapter_match.group(0).strip(), "chapter"))
            continue

    if len(headings) <= 1:
        return [("", content)]

    result = []
    first_heading_idx = headings[0][0]
    if first_heading_idx > 0:
        preamble = "\n".join(lines[:first_heading_idx]).strip()
        if preamble:
            result.append(("", preamble))

    for idx, (start, title, _) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        section_lines = lines[start:end]
        section_content = "\n".join(section_lines).strip()
        result.append((title, section_content))

    return result


def make_split_filename(base_path: str, heading: str, ext: str = ".md") -> str:
    base = base_path.replace(ext, "")
    safe = re.sub(r'[\\/*?:"<>|#\s]', "", heading)

    _CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    order = 99
    nums = re.findall(r'[一二三四五六七八九十\d]+', safe)
    if nums:
        raw = nums[0]
        if raw.isdigit():
            order = int(raw)
        else:
            total = 0
            for ch in raw:
                total = total * 10 + _CN.get(ch, 0)
            order = total if total > 0 else 99

    if not safe:
        return base_path

    return f"{base}_{order:02d}_{safe}{ext}"
