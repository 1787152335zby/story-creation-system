"""StoryBible — 全局故事圣经
跨集追踪角色状态、未回收伏笔、子线进度、关键物品/地点。
每 N 集更新一次，注入为下集生成的"全局故事状态"。
"""
import json
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BIBLE_UPDATE_INTERVAL = 5


def load_bible(project_dir: Path) -> dict | None:
    path = project_dir / "_story_bible.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_bible(project_dir: Path, bible: dict):
    path = project_dir / "_story_bible.json"
    path.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"StoryBible 已保存")


def should_update_bible(episode_index: int) -> bool:
    return episode_index > 0 and episode_index % BIBLE_UPDATE_INTERVAL == 0


def format_bible_injection(bible: dict) -> str:
    if not bible:
        return ""

    lines = ["## 全局故事状态（Story Bible）\n"]
    lines.append("以下是你必须遵守的全局状态。任何角色信息、伏笔进度、子线状态必须以这里为准。\n")

    chars = bible.get("characters", {})
    if chars:
        lines.append("### 角色状态")
        for name, info in chars.items():
            parts = []
            if info.get("status"):
                parts.append(info["status"])
            if info.get("current_location"):
                parts.append(f"位置：{info['current_location']}")
            if info.get("current_state"):
                parts.append(f"状态：{info['current_state']}")
            if info.get("key_relationships"):
                rels = "、".join(f"{k}:{v}" for k, v in info["key_relationships"].items())
                parts.append(f"关系：{rels}")
            if info.get("arc_progress"):
                parts.append(f"弧光进度：{info['arc_progress']}")
            lines.append(f"- **{name}**：{' / '.join(parts)}")

    threads = bible.get("active_threads", [])
    if threads:
        lines.append("\n### 活跃子线（必须推进或回收）")
        for t in threads:
            planted = t.get("planted_in", "?")
            lines.append(f"- 【{t.get('name', '未命名')}】埋于{planted}，状态：{t.get('status', 'open')} | {t.get('last_advance', '')}")

    foreshadows = bible.get("unresolved_foreshadowing", [])
    if foreshadows:
        lines.append("\n### 未回收伏笔（严禁遗忘）")
        for f in foreshadows:
            planted = f.get("planted_in", "?")
            payoff = f.get("expected_payoff", "待定")
            lines.append(f"- 埋于{planted}：{f.get('description', '')} → 预计回收：{payoff}")

    items = bible.get("key_items", {})
    if items:
        lines.append("\n### 关键物品")
        if isinstance(items, dict):
            for name, info in items.items():
                lines.append(f"- **{name}**：持有者 {info.get('held_by', '?')} / {info.get('status', '')} / 最后出现 {info.get('last_seen', '?')}")
        elif isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    lines.append(f"- **{item.get('name', '?')}**：持有者 {item.get('held_by', '?')} / {item.get('status', '')} / 最后出现 {item.get('last_seen', '?')}")

    timeline = bible.get("timeline_markers", [])
    if timeline:
        lines.append("\n### 故事时间线")
        for t in timeline[-10:]:
            lines.append(f"- {t.get('episode', '?')}：{t.get('day', '')} — {t.get('key_event', '')}")

    last_ep = bible.get("last_summary_episode", "?")
    lines.append(f"\n> 以上状态基于截至 {last_ep} 的剧情。本集必须与此衔接。\n")

    return "\n".join(lines)


_EXTRACTION_PROMPT = """你是一个故事连续性追踪器。根据最近的剧集内容，更新全局故事圣经。

## 现有圣经
{existing_bible}

## 最近剧集（需要合并进来）
{recent_episodes}

## 任务
请基于最近剧集更新故事圣经。输出一个 JSON 对象，结构如下：

```json
{{
  "characters": {{
    "角色名": {{
      "status": "alive/dead/missing",
      "current_location": "当前所在位置",
      "current_state": "情绪/身体状态的一句话描述",
      "key_relationships": {{"其他角色名": "关系状态"}},
      "arc_progress": "角色弧光当前进度",
      "last_update": "最近出现集数"
    }}
  }},
  "active_threads": [
    {{"name": "子线名称", "planted_in": "埋入集数", "status": "open/resolved", "last_advance": "最近推进的集数和简要描述"}}
  ],
  "unresolved_foreshadowing": [
    {{"description": "伏笔描述", "planted_in": "埋入集数", "expected_payoff": "预计回收时机"}}
  ],
  "key_items": {{
    "物品名": {{"held_by": "持有者", "status": "物品状态", "last_seen": "最后出现集数"}}
  }},
  "timeline_markers": [
    {{"episode": "集数", "day": "故事内时间", "key_event": "关键事件一句话"}}
  ],
  "last_summary_episode": "最新汇总到的集名"
}}
```

规则：
1. 如果某个角色、物品、子线在最近剧集中没有任何变化，保留现有圣经中的信息
2. 如果角色已死亡或子线已回收，更新 status 为 "dead"/"resolved"，标记 last_update
3. 每条信息尽量精简（一句话），但必须精确
4. 时间线只保留最近 10 条
5. 只输出 JSON 对象，不要额外解释"""


def _extract_json_field(text: str, key: str) -> str | None:
    idx = text.find(f'"{key}"')
    if idx < 0:
        return None
    colon = text.find(":", idx)
    if colon < 0:
        return None
    rest = text[colon + 1:].lstrip()
    if not rest:
        return None
    if rest[0] == "{":
        depth = 0
        end = 0
        for i, ch in enumerate(rest):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return rest[:end] if end > 0 else None
    elif rest[0] == "[":
        depth = 0
        end = 0
        for i, ch in enumerate(rest):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        return rest[:end] if end > 0 else None
    elif rest[0] == '"':
        end = rest.find('"', 1)
        if end > 0:
            while end > 0 and rest[end - 1] == '\\':
                end = rest.find('"', end + 1)
            return rest[:end + 1] if end > 0 else None
        return None
    else:
        match = re.match(r'([^,}\]]+)', rest)
        return match.group(1).strip() if match else None


def _repair_and_parse_json(text: str) -> dict | None:
    text = text.strip()
    if not text.startswith("{"):
        start = text.find("{")
        if start >= 0:
            text = text[start:]
    end = text.rfind("}")
    if end >= 0:
        text = text[:end + 1]

    text = re.sub(r",(\s*[}\]])", r"\1", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    result = {}
    for key in ["characters", "active_threads", "unresolved_foreshadowing",
                 "key_items", "timeline_markers", "last_summary_episode"]:
        field = _extract_json_field(text, key)
        if field:
            try:
                result[key] = json.loads(field)
            except Exception:
                continue
    if result:
        return result
    return None


def build_bible_update(llm_client, project_dir: Path, recent_episodes: list[tuple[str, str]], existing_bible: dict | None) -> dict | None:
    """调用 LLM 合并最近的剧集到圣经中

    Args:
        llm_client: LLMClient 实例
        project_dir: 项目目录
        recent_episodes: [(display_name, full_text), ...] 最近几集
        existing_bible: 现有圣经数据

    Returns:
        更新后的圣经 dict，失败返回 None
    """
    try:
        existing_str = json.dumps(existing_bible or {}, ensure_ascii=False, indent=2)
        recent_texts = "\n---\n".join(
            f"## {name}\n{text[-3000:]}" for name, text in recent_episodes
        )

        prompt = _EXTRACTION_PROMPT.format(
            existing_bible=existing_str,
            recent_episodes=recent_texts,
        )

        result_text = ""
        for chunk in llm_client.backend.chat_stream(prompt, "", temperature=0.3):
            result_text += chunk

        json_start = result_text.find("{")
        json_end = result_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result_text = result_text[json_start:json_end]

        result = _repair_and_parse_json(result_text)

        if not isinstance(result, dict):
            return None

        if existing_bible:
            merged = _merge_bibles(existing_bible, result)
        else:
            merged = result

        return merged

    except Exception as e:
        logger.warning(f"StoryBible 更新失败: {e}")
        return existing_bible


def _merge_bibles(old: dict, new: dict) -> dict:
    """深度合并两个圣经，新的覆盖旧的"""
    merged = dict(old)

    for key in ["characters", "key_items"]:
        if key in new:
            if key not in merged:
                merged[key] = {}
            merged[key] = {**merged[key], **new[key]}

    for key in ["active_threads", "unresolved_foreshadowing"]:
        if key in new:
            existing_names = {t.get("name", "") for t in merged.get(key, [])}
            merged[key] = list(merged.get(key, []))
            for item in new[key]:
                if item.get("name", "") not in existing_names:
                    merged[key].append(item)
                else:
                    for i, ex in enumerate(merged[key]):
                        if ex.get("name") == item.get("name"):
                            merged[key][i] = {**ex, **item}
                            break

    for key in ["timeline_markers"]:
        if key in new:
            merged[key] = (merged.get(key, []) + new[key])[-10:]

    if "last_summary_episode" in new:
        merged["last_summary_episode"] = new["last_summary_episode"]

    return merged
