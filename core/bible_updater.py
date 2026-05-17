import yaml
from core.novel_bible import NovelBible, CharacterEntry, FactionEntry, TimelineEvent, HookEntry


class BibleUpdater:
    @staticmethod
    def build_diff_prompt(bible: NovelBible, chapter_num: int, content: str) -> str:
        return (
            f"以下是最新写的第{chapter_num}章内容。请分析变更并输出YAML格式的更新指令。\n\n"
            f"内容：\n{content[:3000]}\n\n"
            f"只输出有变化的部分，没有变化的部分不要输出。\n\n"
            f"## 格式\n"
            f"updates:\n"
            f"  characters:\n"
            f"    角色名:\n"
            f"      status: 变化后的状态\n"
            f"      cultivation: 修为变化\n"
            f"      last_seen_chapter: {chapter_num}\n"
            f"      last_seen_location: 地点\n"
            f"      relations:\n"
            f"        - 与XXX(关系描述)\n"
            f"      pending_hooks:\n"
            f"        - 新埋伏笔描述\n"
            f"  factions:\n"
            f"    势力名:\n"
            f"      current_goal: 新目标\n"
            f"      relations:\n"
            f"        - 与XXX(关系变化)\n"
            f"  hooks:\n"
            f"    - description: 新伏笔描述\n"
            f"      planted_at: {chapter_num}\n"
            f"      status: 未收\n"
            f"  resolved_hooks:\n"
            f"    - description: 已收伏笔描述（必须与之前埋下的完全一致）\n"
            f"      resolved_in: {chapter_num}\n"
            f"  timeline:\n"
            f"    - chapter: {chapter_num}\n"
            f"      type: 转折|高潮|铺垫|日常\n"
            f"      summary: 一句话描述（20字以内）\n"
            f"  chapter_summary: 本章20字以内摘要"
        )

    @staticmethod
    def parse_diff(text: str) -> dict:
        lines = text.split("\n")
        yaml_lines = []
        in_yaml = False
        for line in lines:
            if line.strip().startswith("updates:"):
                in_yaml = True
            if in_yaml:
                yaml_lines.append(line)
        yaml_text = "\n".join(yaml_lines)
        if not yaml_text.strip():
            return {}
        try:
            parsed = yaml.safe_load(yaml_text)
            return parsed.get("updates", {}) if isinstance(parsed, dict) else {}
        except yaml.YAMLError:
            return {}

    @staticmethod
    def merge_diff(bible: NovelBible, diff: dict, chapter_num: int):
        for name, updates in diff.get("characters", {}).items():
            if name not in bible.characters:
                bible.characters[name] = CharacterEntry(name=name)
            entry = bible.characters[name]
            for key, value in updates.items():
                if key == "relations" and isinstance(value, list):
                    for rel in value:
                        if rel not in entry.relations:
                            entry.relations.append(rel)
                elif key == "pending_hooks" and isinstance(value, list):
                    for h in value:
                        if h not in entry.pending_hooks:
                            entry.pending_hooks.append(h)
                elif hasattr(entry, key):
                    setattr(entry, key, value)
            entry.last_seen_chapter = chapter_num

        for name, updates in diff.get("factions", {}).items():
            if name not in bible.factions:
                bible.factions[name] = FactionEntry()
            entry = bible.factions[name]
            for key, value in updates.items():
                if key == "relations" and isinstance(value, list):
                    for rel in value:
                        if rel not in entry.relations:
                            entry.relations.append(rel)
                elif key == "members" and isinstance(value, list):
                    for m in value:
                        if m not in entry.members:
                            entry.members.append(m)
                elif hasattr(entry, key):
                    setattr(entry, key, value)

        for hook_data in diff.get("hooks", []):
            desc = hook_data.get("description", "")
            if desc and not any(h.description == desc for h in bible.hooks):
                bible.hooks.append(HookEntry(
                    description=desc,
                    planted_at=hook_data.get("planted_at", chapter_num),
                    status="未收",
                ))

        for hook_data in diff.get("resolved_hooks", []):
            desc = hook_data.get("description", "")
            for h in bible.hooks:
                if h.description == desc or desc in h.description or h.description in desc:
                    h.status = f"已收(第{chapter_num}章)"

        for event_data in diff.get("timeline", []):
            bible.timeline.append(TimelineEvent(
                chapter=event_data.get("chapter", chapter_num),
                type=event_data.get("type", "日常"),
                summary=event_data.get("summary", ""),
            ))

        summary = diff.get("chapter_summary", "")
        if summary:
            bible.chapter_summaries[chapter_num] = summary

    @staticmethod
    def update(bible: NovelBible, chapter_num: int, content: str, llm_stream_func) -> NovelBible:
        prompt = BibleUpdater.build_diff_prompt(bible, chapter_num, content)
        raw_output = ""
        for chunk in llm_stream_func(prompt, "", temperature=0.3):
            raw_output += chunk
        diff = BibleUpdater.parse_diff(raw_output)
        BibleUpdater.merge_diff(bible, diff, chapter_num)
        return bible
