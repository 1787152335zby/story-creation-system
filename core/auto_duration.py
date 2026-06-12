"""Auto Duration — 自动时长分析器
当用户选择"自动时长"时，根据行业默认单集时长 + LLM 分析大纲，建议集数。
"""
import json
import re
import logging

logger = logging.getLogger(__name__)

# Industry-standard per-episode durations per story type
TYPE_DEFAULTS = {
    "1": {"name": "短剧", "per_ep": "2分钟", "is_multi": True},
    "2": {"name": "电影", "per_ep": "90分钟", "is_multi": False},
    "3": {"name": "电视剧", "per_ep": "45分钟", "is_multi": True},
    "4": {"name": "小说", "per_ep": "3000字", "is_multi": True},
    "5": {"name": "舞台剧", "per_ep": "120分钟", "is_multi": False},
    "6": {"name": "广播剧", "per_ep": "30分钟", "is_multi": True},
}

_ANALYSIS_PROMPT = """你是故事结构分析师。根据大纲，判断这个故事应该分多少集。

## 故事类型：{type_name}
## 单集时长：{per_ep}（定死，不能改）
## 大纲：
{outline}

## 任务
分析大纲的情节密度和转折点数量，建议集数。每集需要围绕一个核心冲突或转折展开。

输出 JSON：
{{
  "count": 建议集数（整数）,
  "episodes": [
    "第1集：一句话摘要",
    "第2集：一句话摘要",
    ...
  ],
  "reasoning": "建议理由（一句话）"
}}

规则：
1. 根据大纲的情节转折点数量分配集数。每个转折点≈1集
2. 电影和舞台剧固定 count=1
3. 每个 episode 摘要 ≤ 15 字
4. 只输出 JSON，不要解释"""


def get_type_default(story_type_id: str) -> dict:
    return TYPE_DEFAULTS.get(story_type_id, TYPE_DEFAULTS["2"])


def analyze_duration(llm_stream, story_type_id: str, outline_text: str) -> dict | None:
    """分析大纲，输出建议集数和分集摘要。

    Returns:
        {"count": N, "episodes": [str, ...], "reasoning": str} 或 None
    """
    default = get_type_default(story_type_id)
    if not default["is_multi"]:
        return {
            "count": 1,
            "episodes": [f"{default['name']}全篇"],
            "reasoning": f"{default['name']}固定单集，时长 {default['per_ep']}",
        }

    try:
        prompt = _ANALYSIS_PROMPT.format(
            type_name=default["name"],
            per_ep=default["per_ep"],
            outline=outline_text[:6000],
        )
        result_text = ""
        for chunk in llm_stream(prompt, "", temperature=0.3):
            result_text += chunk

        json_start = result_text.find("{")
        json_end = result_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(result_text[json_start:json_end])

        count = int(result.get("count", 1))
        count = max(1, min(count, 200))

        return {
            "count": count,
            "episodes": result.get("episodes", [f"第{i+1}集" for i in range(count)]),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        logger.warning(f"自动时长分析失败: {e}")
        return {
            "count": 24,
            "episodes": [f"第{i+1}集" for i in range(24)],
            "reasoning": "分析失败，使用默认值24集",
        }
