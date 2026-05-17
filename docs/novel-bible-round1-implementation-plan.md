# 小说 Bible 系统（第一轮）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为超长篇小说（故事类型 4）实现逐章生成 + 故事 Bible 增量更新，解决长文本上下文丢失问题。

**Architecture:** 新增 `NovelBible` 数据类存储结构化故事索引，`BibleUpdater` 用 LLM 提取增量 diff，修改 `plot_expander` 在 story_type=4 时进入逐章生成模式。每章 prompt 大小恒定在 5000 字以内。

**Tech Stack:** Python 3.12, PyYAML

**设计文档:** `docs/novel-bible-architecture-design.md`

---

### Task 1: 创建 core/novel_bible.py

**文件:**
- Create: `core/novel_bible.py`

- [ ] **Step 1: 定义 NovelBible 数据类**

```python
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class CharacterEntry:
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
```

- [ ] **Step 2: 实现 YAML 序列化/反序列化**

```python
import yaml


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
            bible.characters[k] = CharacterEntry(**v)
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
```

- [ ] **Step 3: 实现 BibleManager（磁盘读写）**

```python
from pathlib import Path


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
```

- [ ] **Step 4: 实现 BibleFormatter（格式化用于 prompt）**

```python
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
```

- [ ] **Step 5: 运行测试验证**

Run: `python -c "from core.novel_bible import NovelBible, BibleSerializer, CharacterEntry, HookEntry; b=NovelBible(); b.characters['test']=CharacterEntry(status='存活',last_seen_chapter=1); b.hooks.append(HookEntry(description='test',planted_at=1)); y=BibleSerializer.to_yaml(b); b2=BibleSerializer.from_yaml(y); print('OK:', b2.characters['test'].status, b2.hooks[0].description)"`  
Expected: `OK: 存活 test`

---

### Task 2: 创建 core/bible_updater.py

**文件:**
- Create: `core/bible_updater.py`

- [ ] **Step 1: 实现 BibleUpdater 类**

```python
import re
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
        """从LLM输出中提取YAML增量"""
        import yaml
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
        """将diff合并到bible中"""
        # 更新角色
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

        # 更新势力
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

        # 新增伏笔
        for hook_data in diff.get("hooks", []):
            desc = hook_data.get("description", "")
            if desc and not any(h.description == desc for h in bible.hooks):
                bible.hooks.append(HookEntry(
                    description=desc,
                    planted_at=hook_data.get("planted_at", chapter_num),
                    status="未收",
                ))

        # 已收伏笔
        for hook_data in diff.get("resolved_hooks", []):
            desc = hook_data.get("description", "")
            for h in bible.hooks:
                if h.description == desc or desc in h.description or h.description in desc:
                    h.status = f"已收(第{chapter_num}章)"

        # 时间线
        for event_data in diff.get("timeline", []):
            bible.timeline.append(TimelineEvent(
                chapter=event_data.get("chapter", chapter_num),
                type=event_data.get("type", "日常"),
                summary=event_data.get("summary", ""),
            ))

        # 本章摘要
        summary = diff.get("chapter_summary", "")
        if summary:
            bible.chapter_summaries[chapter_num] = summary
```

- [ ] **Step 2: 为 CharacterEntry 添加 name 字段**

```python
@dataclass
class CharacterEntry:
    name: str = ""  # ← 新增
    status: str = "存活"
    ...
```

需要同步修改 `core/novel_bible.py` 中的 `CharacterEntry`。

- [ ] **Step 3: 编写 BibleUpdater 集成方法**

```python
    @staticmethod
    def update(bible: NovelBible, chapter_num: int, content: str, llm_stream_func) -> NovelBible:
        """完整更新流程：构建prompt → 调LLM → 解析diff → 合并"""
        prompt = BibleUpdater.build_diff_prompt(bible, chapter_num, content)
        raw_output = ""
        for chunk in llm_stream_func(prompt, "", temperature=0.3):
            raw_output += chunk
        diff = BibleUpdater.parse_diff(raw_output)
        BibleUpdater.merge_diff(bible, diff, chapter_num)
        return bible
```

- [ ] **Step 4: 运行测试验证**

Run: `python -c "from core.novel_bible import NovelBible, BibleSerializer; from core.bible_updater import BibleUpdater; b=NovelBible(); diff={'characters':{'林尘':{'status':'重伤','last_seen_location':'天剑宗'}},'chapter_summary':'林尘受伤回宗'}; BibleUpdater.merge_diff(b,diff,5); print('OK:', b.characters['林尘'].status, b.chapter_summaries[5])"`  
Expected: `OK: 重伤 林尘受伤回宗`

---

### Task 3: 修改 core/chunk_strategy.py

**文件:**
- Modify: `core/chunk_strategy.py`

- [ ] **Step 1: 为 ChunkPlan 新增 bible_mode 字段**

```python
@dataclass
class ChunkPlan:
    chunk_count: int
    chunk_names: List[str]
    reverse_order: bool
    delimiter: str
    context_window: int
    summarize: bool
    bible_mode: bool = False  # ← 新增
```

- [ ] **Step 2: 修改 ChunkStrategy.get_plan 为小说类型启用 bible_mode**

```python
    @staticmethod
    def get_plan(story_type: str) -> ChunkPlan:
        plan_map = {
            "2": ChunkPlan(3, ["第一幕", "第二幕", "第三幕"], True,
                           r"^##\s*(第一幕|第二幕|第三幕)", 0, True),
            "5": ChunkPlan(3, ["第一幕", "第二幕", "第三幕"], True,
                           r"^##\s*(第一幕|第二幕|第三幕)", 0, True),
            "1": ChunkPlan(0, [], False, r"^#\s*第\d+集", 3, True),
            "3": ChunkPlan(0, [], False, r"^#\s*第\d+集", 2, True),
            "4": ChunkPlan(0, [], False, r"^#\s*第\d+章", 3, True, bible_mode=True),  # ← 修改
            "6": ChunkPlan(0, [], False, r"^#\s*第\d+集", 0, True),
        }
        return plan_map.get(story_type, ChunkPlan(1, ["全部"], False, "", 0, False))
```

- [ ] **Step 3: 运行验证**

Run: `python -c "from core.chunk_strategy import ChunkStrategy; p=ChunkStrategy.get_plan('4'); print('bible_mode:', p.bible_mode, 'context_window:', p.context_window)"`  
Expected: `bible_mode: True context_window: 3`

---

### Task 4: 修改 agents/plot_expander.py 支持逐章生成

**文件:**
- Modify: `agents/plot_expander.py`

- [ ] **Step 1: 在 run_stream 中新增小说模式分支**

在 `run_stream` 方法开头，检测 `plan.bible_mode` 时进入逐章生成：

```python
    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        template = self.load_prompt_template("plot_expander.txt")

        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            outline = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""
        else:
            outline = input_content

        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        screen_aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")

        plan = ChunkStrategy.get_plan(style.story_type)
        
        # === 小说模式（bible_mode）：逐章生成 ===
        if plan.bible_mode:
            yield from self._generate_novel_chapters(project, template, outline, style_context,
                                                       writing_style_name, screen_aspect_name,
                                                       story_type_name, style, feedback, plan)
            return

        # === 原有分块逻辑（电影/短剧等）===
        iterator = ChunkIter(plan, outline)
        if plan.chunk_count == 0:
            yield from self._resolve_auto_chunks(...)
            return
        for ctx in iterator:
            # ... 原有逻辑不变
```

- [ ] **Step 2: 实现 _generate_novel_chapters 方法**

```python
    def _generate_novel_chapters(self, project, template, outline, style_context,
                                   writing_style_name, screen_aspect_name,
                                   story_type_name, style, feedback, plan):
        from core.novel_bible import BibleManager, BibleFormatter
        from core.bible_updater import BibleUpdater
        import re
        
        # 1. 确定总章数
        count_prompt = (
            f"以下是一个故事大纲。请判断这个故事应该分为多少章。"
            f"考虑故事的长度和复杂度。只输出一个整数，不要其他文字。\n\n"
            f"{outline[:3000]}"
        )
        count_text = ""
        for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
            count_text += token
        nums = re.findall(r'\d+', count_text)
        chapter_count = int(nums[0]) if nums else 10
        chapter_count = max(1, min(chapter_count, 1000))
        
        # 2. 加载 Bible
        bible = BibleManager.load(project.project_dir)
        
        # 3. 逐章生成
        for chapter_num in range(1, chapter_count + 1):
            recent_summaries = []
            for i in range(max(1, chapter_num - plan.context_window), chapter_num):
                if i in bible.chapter_summaries:
                    recent_summaries.append(f"第{i}章: {bible.chapter_summaries[i]}")
            
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            prompt = prompt.replace("{duration_mode}", style.duration_mode or "自动")
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chapter_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{story_type}", story_type_name)
            
            # 附加 Bible 上下文
            active_chars = BibleFormatter.format_active_characters(bible)
            if active_chars:
                prompt += f"\n\n## 当前角色状态\n{active_chars}"
            active_hooks = BibleFormatter.format_active_hooks(bible)
            if active_hooks:
                prompt += f"\n\n## 活跃伏笔\n{active_hooks}"
            timeline = BibleFormatter.format_timeline(bible)
            if timeline:
                prompt += f"\n\n## 重要事件回顾\n{timeline}"
            if recent_summaries:
                prompt += f"\n\n## 近期章节回顾\n" + "\n".join(recent_summaries)
            
            prompt += f"\n\n请写第{chapter_num}章的内容。这是小说的第{chapter_num}章，共{chapter_count}章。写完后在末尾加上结束标记：**（全文完）**"
            
            if feedback:
                prompt += f"\n\n## 修改意见\n{feedback}"
            
            chapter_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chapter_output += token
                yield token
            
            # 保存当前章
            if chapter_output.strip():
                chapter_file = f"02_完整剧情/第{chapter_num:03d}章.md"
                project.write_output(chapter_file, chapter_output)
                
                # 更新 Bible
                try:
                    bible = BibleUpdater.update(bible, chapter_num, chapter_output, self.call_llm_stream)
                    BibleManager.save(bible, project.project_dir)
                except Exception:
                    pass  # Bible 更新失败不影响正文生成
```

- [ ] **Step 3: 运行语法检查**

Run: `python -c "import ast; ast.parse(open('agents/plot_expander.py').read()); print('✅')"`  
Expected: `✅`

---

### Task 5: 修改 server/async_orch.py 适配 Bible 模式

**文件:**
- Modify: `server/async_orch.py`

注意：当前 `async_orch.py` 的 `run()` 和 `continue_run()` 中，调用 `agent.run_stream()` 后保存输出。在 Bible 模式下，分章保存已经由 Agent 内部完成，所以不再需要额外保存。需要做两个调整：

- [ ] **Step 1: 在 run() 中跳过 Bible 模式的额外保存**

找到 `run()` 方法中保存输出的部分（`if phase.split: ... else: project.write_output(...)`），在其前面增加判断：

```python
                # Bible 模式：Agent 内部已逐章保存，不需要额外保存
                if hasattr(agent, '_bible_mode') and agent._bible_mode:
                    pass
                elif phase.split:
                    if hasattr(agent, '_chunks') and agent._chunks:
                        self._save_chunked_output(project, output_path, agent._chunks)
                    else:
                        self._save_split_output(project, output_path, full_output)
                else:
                    project.write_output(output_path, full_output)
```

需要在 `plot_expander.py` 的 `_generate_novel_chapters` 中设置 `self._bible_mode = True`。

- [ ] **Step 2: 运行语法检查**

Run: `python -c "import ast; ast.parse(open('server/async_orch.py').read()); print('✅')"`  
Expected: `✅`

---

### Task 6: 修改 workflow.yaml（可选）

**文件:**
- Modify: `workflow.yaml`

- [ ] **Step 1: 为小说类型添加 bible_keeper 阶段**

注意：第一轮中 Bible 更新由 `plot_expander` 内部完成，`bible_keeper` 作为独立 Agent 在第二轮实现。第一轮只需确认 `workflow.yaml` 中完整剧情阶段对小说类型也启用。

当前 `workflow.yaml` 中完整剧情的 `condition: true`，已覆盖所有类型，无需修改。

---

### Task 7: 端到端验证

- [ ] **Step 1: 验证所有文件语法**

Run: `python -c "import ast; [ast.parse(open(f).read()) for f in ['core/novel_bible.py','core/bible_updater.py','core/chunk_strategy.py','agents/plot_expander.py','server/async_orch.py']]; print('✅ All OK')"`  
Expected: `✅ All OK`

- [ ] **Step 2: 重启后端**

```bash
taskkill /f /im python.exe
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 3: 创建小说类型项目并验证逐章生成**

通过 API 创建 story_type=4 的项目，检查是否进入逐章模式。验证 `02_完整剧情/` 目录下生成 `第001章.md` 等文件。

- [ ] **Step 4: 验证 Bible 文件**

在生成几章后，检查 `04_novel_bible/bible.yaml` 是否正确包含了角色状态、伏笔等信息。

- [ ] **Step 5: 构建前端**

Run: `npm run build`  
Expected: Build 成功
