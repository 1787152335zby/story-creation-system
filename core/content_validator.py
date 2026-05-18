"""内容量验证器：检查生成内容是否超出目标时长对应的体量"""

from pathlib import Path
from typing import Optional


SCENE_COUNTS = {
    0.5:  (3, 6),    # 30-60秒
    1:    (6, 12),   # 1-3分钟
    5:    (12, 20),  # 5-10分钟
    15:   (20, 40),  # 15-30分钟
    45:   (40, 60),  # 45-60分钟
    60:   (50, 80),  # 60-90分钟
}

WORD_COUNTS = {
    0.5:  (100, 300),
    1:    (300, 800),
    5:    (800, 2000),
    15:   (2000, 5000),
    45:   (5000, 10000),
    60:   (8000, 15000),
}


def _get_bucket(total_minutes: int) -> tuple[int, int]:
    """Find the right row in the constraint table"""
    thresholds = sorted(SCENE_COUNTS.keys(), reverse=True)
    for t in thresholds:
        if total_minutes >= t:
            return SCENE_COUNTS[t], WORD_COUNTS[t]
    return (3, 6), (100, 300)


def validate_content(content: str, total_minutes: int, stage: str = "") -> dict:
    """Validate content volume against target duration.

    Returns:
        {"passed": bool, "warnings": [str, ...], "stats": {...}}
    """
    if not total_minutes or total_minutes <= 0:
        return {"passed": True, "warnings": [], "stats": {}}

    scene_count = content.count("第") // 2 if "第" in content else 0
    word_count = len(content)
    line_count = content.count("\n") + 1

    (min_scenes, max_scenes), (min_words, max_words) = _get_bucket(total_minutes)

    warnings = []
    stats = {
        "scene_count": scene_count,
        "word_count": word_count,
        "line_count": line_count,
        "min_scenes": min_scenes,
        "max_scenes": max_scenes,
        "min_words": min_words,
        "max_words": max_words,
    }

    if scene_count > max_scenes:
        warnings.append(
            f"{stage}场次过多：约{scene_count}场（目标{total_minutes}分钟建议≤{max_scenes}场）"
        )
    if word_count > max_words:
        warnings.append(
            f"{stage}字数过多：约{word_count}字（目标{total_minutes}分钟建议≤{max_words}字）"
        )

    return {"passed": len(warnings) == 0, "warnings": warnings, "stats": stats}
