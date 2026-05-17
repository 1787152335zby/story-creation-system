from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from pathlib import Path
import yaml


@dataclass
class CharacterEntry:
    name: str = ""
    status: str = "存活"
    cultivation: str = ""
    arc: str = ""
    relations: List[str] = field(default_factory=list)
    last_seen_chapter: int = 0
    last_seen_location: str = ""
    key_items: List[str] = field(default_factory=list)
    pending_hooks: List[str] = field(default_factory=list)


@dataclass
class FactionEntry:
    members: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    current_goal: str = ""
    influence_region: str = ""


@dataclass
class TimelineEvent:
    chapter: int = 0
    type: str = ""
    summary: str = ""


@dataclass
class HookEntry:
    description: str = ""
    planted_at: int = 0
    status: str = "未收"
    expected_resolve: str = ""


@dataclass
class NovelBible:
    characters: Dict[str, CharacterEntry] = field(default_factory=dict)
    factions: Dict[str, FactionEntry] = field(default_factory=dict)
    timeline: List[TimelineEvent] = field(default_factory=list)
    hooks: List[HookEntry] = field(default_factory=list)
    world_rules: List[str] = field(default_factory=list)
    chapter_summaries: Dict[int, str] = field(default_factory=dict)


class BibleSerializer:
    @staticmethod
    def to_dict(bible: NovelBible) -> dict:
        return {
            "characters": {k: asdict(v) for k, v in bible.characters.items()},
            "factions": {k: asdict(v) for k, v in bible.factions.items()},
            "timeline": [asdict(e) for e in bible.timeline],
            "hooks": [asdict(h) for h in bible.hooks],
            "world_rules": bible.world_rules,
            "chapter_summaries": {str(k): v for k, v in bible.chapter_summaries.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> NovelBible:
        bible = NovelBible()
        for k, v in data.get("characters", {}).items():
            bible.characters[k] = CharacterEntry(name=k, **{kk: vv for kk, vv in v.items() if kk != "name"})
        for k, v in data.get("factions", {}).items():
            bible.factions[k] = FactionEntry(**v)
        for e in data.get("timeline", []):
            bible.timeline.append(TimelineEvent(**e))
        for h in data.get("hooks", []):
            bible.hooks.append(HookEntry(**h))
        bible.world_rules = data.get("world_rules", [])
        bible.chapter_summaries = {int(k): v for k, v in data.get("chapter_summaries", {}).items()}
        return bible

    @staticmethod
    def to_yaml(bible: NovelBible) -> str:
        return yaml.dump(BibleSerializer.to_dict(bible), allow_unicode=True, default_flow_style=False, sort_keys=False)

    @staticmethod
    def from_yaml(text: str) -> NovelBible:
        data = yaml.safe_load(text)
        return BibleSerializer.from_dict(data) if data else NovelBible()


class BibleManager:
    BIBLE_FILENAME = "bible.yaml"

    @staticmethod
    def load(project_dir: Path) -> NovelBible:
        bible_path = project_dir / "04_novel_bible" / BibleManager.BIBLE_FILENAME
        if bible_path.exists():
            text = bible_path.read_text(encoding="utf-8")
            return BibleSerializer.from_yaml(text)
        return NovelBible()

    @staticmethod
    def save(bible: NovelBible, project_dir: Path):
        bible_dir = project_dir / "04_novel_bible"
        bible_dir.mkdir(parents=True, exist_ok=True)
        bible_path = bible_dir / BibleManager.BIBLE_FILENAME
        bible_path.write_text(BibleSerializer.to_yaml(bible), encoding="utf-8")


class BibleFormatter:
    @staticmethod
    def format_active_characters(bible: NovelBible, max_count: int = 10) -> str:
        lines = []
        sorted_chars = sorted(bible.characters.items(), key=lambda x: x[1].last_seen_chapter, reverse=True)
        for name, entry in sorted_chars[:max_count]:
            lines.append(f"- {name}: {entry.status}, {entry.cultivation}, 最后出场第{entry.last_seen_chapter}章")
            if entry.relations:
                lines.append(f"  关系: {'; '.join(entry.relations)}")
            if entry.pending_hooks:
                lines.append(f"  待收伏笔: {'; '.join(entry.pending_hooks)}")
        return "\n".join(lines)

    @staticmethod
    def format_active_hooks(bible: NovelBible, max_count: int = 5) -> str:
        lines = []
        for h in bible.hooks:
            if h.status == "未收":
                lines.append(f"- {h.description} (第{h.planted_at}章埋下)")
                if len(lines) >= max_count:
                    break
        return "\n".join(lines)

    @staticmethod
    def format_timeline(bible: NovelBible, recent_count: int = 10) -> str:
        lines = []
        sorted_events = sorted(bible.timeline, key=lambda e: e.chapter, reverse=True)
        for e in sorted_events[:recent_count]:
            lines.append(f"- 第{e.chapter}章 [{e.type}] {e.summary}")
        return "\n".join(lines)
