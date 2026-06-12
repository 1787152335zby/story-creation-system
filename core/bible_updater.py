import yaml
from core.novel_bible import NovelBible, CharacterEntry, FactionEntry, TimelineEvent, HookEntry


class BibleUpdater:
    @staticmethod
    def build_diff_prompt(bible: NovelBible, chapter_num: int, content: str) -> str:
        existing_hooks = "\n".join(
            f"  - {h.description} (第{h.planted_at}章埋, 状态:{h.status})"
            for h in bible.hooks
        )
        existing_chars = "\n".join(
            f"  {name}: 状态={entry.status}, 最后出场第{entry.last_seen_chapter}章, 位置={entry.last_seen_location}"
            for name, entry in bible.characters.items()
        )
        return (
            f"以下是最新写的第{chapter_num}章内容。请分析变更并输出YAML格式的更新指令。\n\n"
            f"内容：\n{content[:4000]}\n\n"
            f"## 现有人物状态\n{existing_chars if existing_chars else '(无)'}\n\n"
            f"## 现有未收伏笔\n{existing_hooks if existing_hooks else '(无)'}\n\n"
            f"## 输出格式（只输出有变化的部分）\n"
            f"updates:\n"
            f"  characters:\n"
            f"    角色名:\n"
            f"      status: 变化后的状态 (存活/死亡/失踪/受伤)\n"
            f"      last_seen_chapter: {chapter_num}\n"
            f"      last_seen_location: 具体地点\n"
            f"      arc: 角色弧光当前状态的简短描述\n"
            f"      relations:\n"
            f"        - 与XXX的关系(关系性质及变化)\n"
            f"      key_items:\n"
            f"        - 新增或变化的关键物品\n"
            f"      pending_hooks:\n"
            f"        - 该角色身上新增的待收伏笔（每条15字内）\n"
            f"  factions:\n"
            f"    势力名:\n"
            f"      members:\n"
            f"        - 角色名（新增或移除）\n"
            f"      current_goal: 当前目标\n"
            f"      relations:\n"
            f"        - 与XXX的关系变化\n"
            f"  hooks:\n"
            f"    - description: 新伏笔描述（20字内）\n"
            f"      planted_at: {chapter_num}\n"
            f"      status: 未收\n"
            f"      expected_resolve: 预计在哪类场景回收（如\"身份揭晓时\"\"最终对决前\"）\n"
            f"  resolved_hooks:\n"
            f"    - description: 已收伏笔描述（必须与埋下时一致）\n"
            f"      resolved_in: {chapter_num}\n"
            f"  timeline:\n"
            f"    - chapter: {chapter_num}\n"
            f"      type: 转折|高潮|铺垫|日常|揭示|战斗\n"
            f"      summary: 本章关键事件一句话（25字内）\n"
            f"  chapter_summary: 本章25字以内摘要\n"
            f"  world_rules:\n"
            f"    - 新增或变化的世界规则描述"
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
