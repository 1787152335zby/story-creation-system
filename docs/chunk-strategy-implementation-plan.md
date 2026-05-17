# 按故事类型适配的分块生成策略 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为不同类型的故事（电影/短剧/小说等）分别实现分块生成策略，替代一次性长文本生成，提升输出质量。

**Architecture:** 在 Agent 层和 workflow 层之间插入 `ChunkStrategy` + `SummaryExtractor` 两个新模块。Agent 的 `run_stream` 方法根据 `story_type` 选择分块策略，逐块生成并提取摘要，用摘要链桥接块间上下文。

**Tech Stack:** Python 3.12, asyncio, websockets

**设计文档:** `docs/story-type-chunk-strategy-design.md`

---

### Task 1: 创建 core/chunk_strategy.py

**文件:**
- Create: `core/chunk_strategy.py`

- [ ] **Step 1: 定义 ChunkPlan 数据类**

```python
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChunkPlan:
    chunk_count: int  # 分块数量，电影=3, auto类型在解析后填充
    chunk_names: List[str]  # 块名称列表，如["第一幕","第二幕","第三幕"]
    reverse_order: bool  # 是否逆向生成（先写最后一块）
    delimiter: str  # 用于从大纲提取分块边界的正则
    context_window: int  # 桥接时传入前几块全文（0=全部）
    summarize: bool  # 是否提取摘要
```

- [ ] **Step 2: 定义 ChunkContext 数据类**

```python
@dataclass
class ChunkContext:
    index: int  # 在 blocks 中的索引
    name: str  # "第一幕"
    outline_section: str  # 从大纲中提取的对应章节内容
    previous_full_texts: List[str] = field(default_factory=list)  # 之前块的全文（按D方案）
    summaries: List[str] = field(default_factory=list)  # 之前块的摘要链
```

- [ ] **Step 3: 实现 ChunkStrategy.get_plan**

```python
import re


class ChunkStrategy:
    @staticmethod
    def get_plan(story_type: str) -> ChunkPlan:
        plan_map = {
            "2": ChunkPlan(3, ["第一幕", "第二幕", "第三幕"], True,
                           r"^##\s*(第一幕|第二幕|第三幕)", 0, True),
            "5": ChunkPlan(3, ["第一幕", "第二幕", "第三幕"], True,
                           r"^##\s*(第一幕|第二幕|第三幕)", 0, True),
            "1": ChunkPlan(0, [], False, r"^#\s*第\d+集", 3, True),
            "3": ChunkPlan(0, [], False, r"^#\s*第\d+集", 2, True),
            "4": ChunkPlan(0, [], False, r"^#\s*第\d+章", 3, True),
            "6": ChunkPlan(0, [], False, r"^#\s*第\d+集", 0, True),
        }
        return plan_map.get(story_type, ChunkPlan(1, ["全部"], False, "", 0, False))
```

- [ ] **Step 4: 实现 ChunkIter 迭代器**

```python
class ChunkIter:
    def __init__(self, plan: ChunkPlan, outline: str):
        self.plan = plan
        if plan.chunk_count > 0:
            # 固定分块：按 delimiter 从大纲提取
            self.blocks = self._parse_fixed(outline, plan)
        else:
            # auto 分块：需要 LLM 先判断数量
            self.blocks = []

    @staticmethod
    def _parse_fixed(outline: str, plan: ChunkPlan) -> List[dict]:
        """按 delimiter 正则从大纲中提取各个块的对应内容"""
        pattern = re.compile(plan.delimiter, re.MULTILINE)
        sections = pattern.split(outline)
        blocks = []
        # pattern.split 返回交替的 [标题, 内容, 标题, 内容, ...]
        labels = [s.strip() for s in sections[1::2]]
        contents = [s.strip() for s in sections[2::2]]
        for i, (label, content) in enumerate(zip(labels, contents)):
            blocks.append({"index": i, "name": label, "content": content})
        # 如果解析不到任何块，则按 plan.chunk_count 等分
        if not blocks and plan.chunk_count > 0:
            per_chunk = len(outline) // plan.chunk_count
            for i in range(plan.chunk_count):
                start = i * per_chunk
                end = (i + 1) * per_chunk if i < plan.chunk_count - 1 else len(outline)
                blocks.append({"index": i, "name": plan.chunk_names[i], "content": outline[start:end]})
        return blocks

    def set_auto_blocks(self, count: int):
        """auto 类型由外部调用此方法来设置分块数"""
        self.plan.chunk_count = count
        self.plan.chunk_names = [f"第{i+1}集" for i in range(count)]
        # auto 类型不按大纲分割，生成时使用全量大纲作为上下文
        self.blocks = [{"index": i, "name": self.plan.chunk_names[i], "content": ""} for i in range(count)]

    def __iter__(self):
        indices = list(range(len(self.blocks)))
        if self.plan.reverse_order:
            indices = list(reversed(indices))
        for idx in indices:
            blk = self.blocks[idx]
            # 收集前序全文（仅取 context_window 指定的数量）
            prev_texts = []
            prev_summaries = []
            for j in range(len(self.blocks)):
                if j >= idx:
                    break
                prev_texts.append(self.blocks[j].get("_output", ""))
                prev_summaries.append(self.blocks[j].get("_summary", ""))
            if self.plan.context_window > 0:
                prev_texts = prev_texts[-self.plan.context_window:]
                prev_summaries = prev_summaries[-self.plan.context_window:]
            yield ChunkContext(
                index=blk["index"],
                name=blk["name"],
                outline_section=blk["content"],
                previous_full_texts=prev_texts,
                summaries=prev_summaries,
            )

    def set_output(self, index: int, output: str, summary: str = ""):
        for blk in self.blocks:
            if blk["index"] == index:
                blk["_output"] = output
                blk["_summary"] = summary
                break
```

- [ ] **Step 5: 运行测试验证**

Run: `python -c "from core.chunk_strategy import ChunkStrategy, ChunkIter, ChunkPlan; p=ChunkStrategy.get_plan('2'); print('电影:', p.chunk_count, p.chunk_names, p.reverse_order); p2=ChunkStrategy.get_plan('1'); print('短剧:', p2.chunk_count)"`  
Expected: `电影: 3 ['第一幕', '第二幕', '第三幕'] True` + `短剧: 0 [] False`

---

### Task 2: 创建 core/summary_extractor.py

**文件:**
- Create: `core/summary_extractor.py`

- [ ] **Step 1: 实现 SummaryExtractor**

```python
class SummaryExtractor:
    @staticmethod
    def build_summary_prompt(chunk_name: str, chunk_content: str) -> str:
        return (
            f"以下是一段故事的\"{chunk_name}\"内容。请提取关键元素作为结构化摘要。\n\n"
            f"内容：\n{chunk_content[:2000]}\n\n"
            f"请按以下格式输出：\n"
            f"## 关键元素追踪\n"
            f"- 未解悬念：\n"
            f"- 角色状态变化：\n"
            f"- 重要道具/线索：\n"
            f"- 时间线推进：\n"
            f"- 情绪基调："
        )

    @staticmethod
    def parse_summary(text: str) -> str:
        """从LLM输出中提取摘要部分，去除多余说明"""
        lines = []
        in_summary = False
        for line in text.split("\n"):
            if line.startswith("## 关键元素追踪"):
                in_summary = True
            if in_summary:
                lines.append(line)
        return "\n".join(lines) if lines else text.strip()
```

- [ ] **Step 2: 运行测试验证**

Run: `python -c "from core.summary_extractor import SummaryExtractor; p=SummaryExtractor.build_summary_prompt('第一幕','test'); print('OK:', '关键元素' in p)"`  
Expected: `OK: True`

---

### Task 3: 实现 plot_expander 的分块生成

**文件:**
- Modify: `agents/plot_expander.py` (重写 run_stream)

- [ ] **Step 1: 重写 plot_expander.py**

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, WRITING_STYLES, SCREEN_ASPECTS, STORY_TYPES
from core.chunk_strategy import ChunkStrategy, ChunkIter
from core.summary_extractor import SummaryExtractor


class PlotExpander(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

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
        iterator = ChunkIter(plan, outline)

        # auto 分块：先问 LLM 决定分几块
        if plan.chunk_count == 0:
            yield from self._resolve_auto_chunks(iterator, template, outline, style_context,
                                                   writing_style_name, screen_aspect_name,
                                                   story_type_name, style, feedback)
            return

        # 固定分块：逐块生成
        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", ctx.outline_section or outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            prompt = prompt.replace("{duration_mode}", style.duration_mode or "自动")
            prompt = prompt.replace("{episode_count}", style.episode_count or "（由AI根据大纲合理分配）")
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{story_type}", story_type_name)

            # 附加上下文桥接
            if ctx.previous_full_texts:
                bridge = "\n\n## 上文回顾\n\n"
                for i, ft in enumerate(ctx.previous_full_texts):
                    bridge += f"### 前序内容（{ctx.name}之前的部分）\n{ft[-1500:]}\n\n"
                prompt += bridge
            if ctx.summaries:
                prompt += f"\n\n## 关键元素追踪\n" + "\n".join(ctx.summaries)
            prompt += f"\n\n请只写「{ctx.name}」的内容。写完后在末尾加上标记：**（全文完）**"

            if feedback and ctx.index == len(iterator.blocks) - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            if plan.summarize and chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)

    def _resolve_auto_chunks(self, iterator, template, outline, style_context,
                               writing_style_name, screen_aspect_name,
                               story_type_name, style, feedback):
        """auto 类型：先让 LLM 判断分几块"""
        count_prompt = (
            f"以下是一个故事大纲。请判断这个故事应该分为几集/几章。"
            f"考虑故事的长度和复杂度。只输出一个整数，不要其他文字。\n\n"
            f"{outline[:3000]}"
        )
        count_text = ""
        for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
            count_text += token
        import re
        nums = re.findall(r'\d+', count_text)
        chunk_count = int(nums[0]) if nums else 3
        chunk_count = max(1, min(chunk_count, 20))
        iterator.set_auto_blocks(chunk_count)

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            prompt = prompt.replace("{duration_mode}", style.duration_mode or "自动")
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chunk_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{story_type}", story_type_name)

            if ctx.previous_full_texts:
                bridge = "\n\n## 上文回顾\n\n"
                for ft in ctx.previous_full_texts:
                    bridge += ft[-1500:] + "\n\n"
                prompt += bridge
            if ctx.summaries:
                prompt += f"\n\n## 关键元素追踪\n" + "\n".join(ctx.summaries)
            prompt += f"\n\n请只写「{ctx.name}」的内容，这是系列的第{ctx.index+1}部分。写完后在末尾加上标记：**（全文完）**"

            if feedback and ctx.index == len(iterator.blocks) - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            if chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)

    def _extract_summary(self, chunk_name: str, content: str) -> str:
        summary_prompt = SummaryExtractor.build_summary_prompt(chunk_name, content)
        summary_raw = ""
        for token in self.call_llm_stream(summary_prompt, "", temperature=0.3):
            summary_raw += token
        return SummaryExtractor.parse_summary(summary_raw)
```

- [ ] **Step 2: 运行语法检查**

Run: `python -c "import ast; ast.parse(open('agents/plot_expander.py').read()); print('✅')"`  
Expected: `✅`

---

### Task 4: 重写 screenplay_writer.py

**文件:**
- Modify: `agents/screenplay_writer.py` (重写 run_stream)

- [ ] **Step 1: 重写 screenplay_writer.py**

```python
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, WRITING_STYLES, SCREEN_ASPECTS, SCRIPT_STYLES, STORY_TYPES
from core.chunk_strategy import ChunkStrategy, ChunkIter
from core.summary_extractor import SummaryExtractor


class ScreenplayWriter(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        template = self.load_prompt_template("screenplay_writer.txt")

        plot_structure = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            plot_structure = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        script_style_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "视觉化写作")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")

        plan = ChunkStrategy.get_plan(style.story_type)
        iterator = ChunkIter(plan, plot_structure)

        if plan.chunk_count == 0:
            yield from self._resolve_auto_chunks(iterator, template, plot_structure, style_context,
                                                   writing_style_name, script_style_name,
                                                   story_type_name, style, feedback)
            return

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{plot_structure}", ctx.outline_section or plot_structure)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{script_style}", script_style_name)
            prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
            prompt = prompt.replace("{duration_mode}", style.duration_mode or "自动")
            prompt = prompt.replace("{episode_count}", style.episode_count or "（由AI根据大纲合理分配）")
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{story_type}", story_type_name)

            if ctx.previous_full_texts:
                bridge = "\n\n## 上文回顾\n\n"
                for ft in ctx.previous_full_texts:
                    bridge += ft[-1500:] + "\n\n"
                prompt += bridge
            prompt += f"\n\n请只写「{ctx.name}」的剧本内容。写完后在末尾加上标记：**（全文完）**"

            if feedback and ctx.index == len(iterator.blocks) - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            if plan.summarize and chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)

    def _resolve_auto_chunks(self, iterator, template, input_content, style_context,
                               writing_style_name, script_style_name,
                               story_type_name, style, feedback):
        count_prompt = (
            f"以下是一段剧情描述。请判断应该分为几集/几章来写剧本。"
            f"只输出一个整数。\n\n{input_content[:3000]}"
        )
        count_text = ""
        for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
            count_text += token
        import re
        nums = re.findall(r'\d+', count_text)
        chunk_count = int(nums[0]) if nums else 3
        chunk_count = max(1, min(chunk_count, 20))
        iterator.set_auto_blocks(chunk_count)

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{plot_structure}", input_content)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{script_style}", script_style_name)
            prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
            prompt = prompt.replace("{duration_mode}", style.duration_mode or "自动")
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chunk_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{story_type}", story_type_name)

            if ctx.previous_full_texts:
                bridge = "\n\n## 上文回顾\n\n"
                for ft in ctx.previous_full_texts:
                    bridge += ft[-1500:] + "\n\n"
                prompt += bridge
            prompt += f"\n\n请只写「{ctx.name}」的剧本内容。写完后在末尾加上标记：**（全文完）**"

            if feedback and ctx.index == len(iterator.blocks) - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            if chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)

    def _extract_summary(self, chunk_name: str, content: str) -> str:
        summary_prompt = SummaryExtractor.build_summary_prompt(chunk_name, content)
        summary_raw = ""
        for token in self.call_llm_stream(summary_prompt, "", temperature=0.3):
            summary_raw += token
        return SummaryExtractor.parse_summary(summary_raw)
```

- [ ] **Step 2: 运行语法检查**

Run: `python -c "import ast; ast.parse(open('agents/screenplay_writer.py').read()); print('✅')"`  
Expected: `✅`

---

### Task 5: 修改 server/async_orch.py 适配分块保存

**文件:**
- Modify: `server/async_orch.py`

- [ ] **Step 1: 修改 _save_split_output 支持分块**

将 `_save_split_output` 改为接收 `chunks` 列表参数：

```python
    def _save_split_output(self, project, output_path, content):
        """保存完整合并文件（向下兼容）"""
        project.write_output(output_path, content)

    def _save_chunked_output(self, project, output_dir, chunks: list):
        """保存分块文件：每个块独立保存 + 完整文件"""
        full_content_parts = []
        for chunk_info in chunks:
            if chunk_info.get("output", "").strip():
                fname = f"{output_dir.stem}_{chunk_info['name']}.md"
                project.write_output(fname, chunk_info["output"])
                full_content_parts.append(chunk_info["output"])
        # 保存完整合并文件
        if full_content_parts:
            project.write_output(str(output_dir) + ".md", "\n\n---\n\n".join(full_content_parts))
```

- [ ] **Step 2: 修改 _get_input 支持分块输入**

`_get_input` 需要检测是否有分块输入文件（如 `02_完整剧情/完整剧情_第一幕.md`），有则按分块读取，没有则读合并文件。

```python
    async def _get_input(self, project: ProjectManager, phase) -> str:
        input_map = {
            "plot_expander": "00_任务指令/任务指令.md",
            "screenplay_writer": "02_完整剧情/完整剧情.md",
            "storyboarder": "03_完整剧本/完整剧本.md",
            "prompt_engineer": "04_分镜脚本/分镜脚本.md",
        }
        source = input_map.get(phase.agent, "")
        if not source:
            return ""

        dir_path = project.project_dir / Path(source).parent
        base_name = Path(source).stem  # 如 "完整剧情"
        # 检查是否有分块文件：完整剧情_第一幕.md, 完整剧情_第二幕.md, ...
        split_files = sorted(
            dir_path.glob(f"{base_name}_*.md"),
            key=lambda f: f.name,
        )
        if split_files:
            parts = []
            for sf in split_files:
                c = project.read_output(str(sf.relative_to(project.project_dir)))
                if c:
                    parts.append(c)
            if parts:
                joined = "\n\n---\n\n".join(parts)
                return joined

        return project.read_output(source) or ""
```

- [ ] **Step 3: 在 continue_run 和 run 中调用 _save_chunked_output**

在 `continue_run` 和 `run` 中，生成完毕后把 `stream_buf` 收集的内容按块保存。

```python
    # 在生成完整输出后，检测是否有分块信息
    if hasattr(phase, 'split') and phase.split:
        # 如果有分块信息，保存分块文件
        chunks = getattr(full_output, '_chunks', None)
        if chunks:
            self._save_chunked_output(project, output_path, chunks)
        else:
            self._save_split_output(project, output_path, full_output)
    else:
        project.write_output(output_path, full_output)
```

- [ ] **Step 4: 运行语法检查**

Run: `python -c "import ast; ast.parse(open('server/async_orch.py').read()); print('✅')"`  
Expected: `✅`

---

### Task 6: 修改 storyboarder.py 和 prompt_engineer.py

**文件:**
- Modify: `agents/storyboarder.py`
- Modify: `agents/prompt_engineer.py`

这两个 Agent 的修改较小，主要让它们从分块输入中读取对应块的内容。

- [ ] **Step 1: 修改 storyboarder.py**

```python
    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        template = self.load_prompt_template("storyboarder.txt")

        full_plot = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            full_plot = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        style_context = self.get_style_context(style)
        visual_style_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "自动适配")

        # 分镜脚本按幕拆分输出
        plan = ChunkStrategy.get_plan(style.story_type)
        if plan.chunk_count > 0 and plan.chunk_names:
            for chunk_name in plan.chunk_names:
                # 从输入中提取对应幕的内容
                section = self._extract_section(full_plot, chunk_name)
                if not section:
                    section = full_plot

                system_prompt = template.replace("{style_config}", style_context)
                system_prompt = system_prompt.replace("{full_plot}", section)
                system_prompt = system_prompt.replace("{visual_style}", visual_style_name)
                system_prompt = system_prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
                system_prompt = system_prompt.replace("{duration_mode}", style.duration_mode or "自动")

                if feedback:
                    system_prompt += f"\n\n## 修改意见\n{feedback}"

                system_prompt += f"\n\n请只写「{chunk_name}」的分镜内容。写完后在末尾加上标记：**【全片完】**"

                for token in self.call_llm_stream_with_continuation(system_prompt, "", temperature=0.8):
                    yield token
        else:
            # 非电影类型：照旧
            system_prompt = template.replace("{style_config}", style_context)
            system_prompt = system_prompt.replace("{full_plot}", full_plot)
            system_prompt = system_prompt.replace("{visual_style}", visual_style_name)
            system_prompt = system_prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
            system_prompt = system_prompt.replace("{duration_mode}", style.duration_mode or "自动")
            system_prompt += "\n\n写完后在末尾加上标记：**【全片完】**"

            if feedback:
                system_prompt += f"\n\n## 修改意见\n{feedback}"

            for token in self.call_llm_stream_with_continuation(system_prompt, "", temperature=0.8):
                yield token

    def _extract_section(self, text: str, section_name: str) -> str:
        """从文本中提取对应章节的内容"""
        import re
        # 匹配 ## 第一幕 / ## 第二幕 等
        pattern = re.compile(rf"^##\s*{re.escape(section_name)}\s*$", re.MULTILINE)
        lines = text.split("\n")
        start_idx = None
        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                start_idx = i
                break
        if start_idx is None:
            return ""
        # 找到下一个 ## 标题作为结束
        end_idx = len(lines)
        for i in range(start_idx + 1, len(lines)):
            if re.match(r"^##\s", lines[i].strip()):
                end_idx = i
                break
        return "\n".join(lines[start_idx:end_idx]).strip()
```

- [ ] **Step 2: 修改 prompt_engineer.py**

类似 storyboarder.py 的修改，按幕分段。在 `run_stream` 开头加入同样的分块逻辑，遍历 `plan.chunk_names`。

- [ ] **Step 3: 运行语法检查**

Run: `python -c "import ast; ast.parse(open('agents/storyboarder.py').read()); ast.parse(open('agents/prompt_engineer.py').read()); print('✅')"`  
Expected: `✅`

---

### Task 7: 修改 prompt 模板，移除结束标记（不再需要续写）

**文件:**
- Modify: `prompts/plot_expander.txt`
- Modify: `prompts/screenplay_writer.txt`

现在 Agent 代码中已经内置了 `（全文完）` 标记，不再需要 prompt 模板中要求。但保留作为兜底。

- [ ] **Step 1: 在 plot_expander.txt 末尾删除结束标记要求行**

找到 `全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**` 并移除它（Agent 代码中已通过 f-string 注入）。

- [ ] **Step 2: 在 screenplay_writer.txt 末尾删除同样行**

同上。

---

### Task 8: 修改 agents/orchestrator.py（CLI 模式）

**文件:**
- Modify: `agents/orchestrator.py`

- [ ] **Step 1: 在 _run_agent_phase 中保存完整文件后再拆分**

当前代码已经异步完成了分拆保存，只需要保持 `_save_split_output` 的做法一致：

```python
    if phase.split:
        path = project.write_output(output_path, result)
        # ... 后续拆分逻辑不变
```

---

### Task 9: 端到端测试

**文件:**
- Run: 测试脚本

- [ ] **Step 1: 清理旧测试项目，重启后端**

```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 创建电影类型项目，检查是否按3幕生成**

通过 API 创建项目后检查 `02_完整剧情/` 目录是否产生 `完整剧情_第一幕.md` 等 3 个文件。

- [ ] **Step 3: 检查分块文件的完整性**

验证合并文件 + 分块文件都存在，且分块文件内容不重复不缺失。

- [ ] **Step 4: 创建短剧类型项目，检查是否自动分集**

验证 `02_完整剧情/` 生成 `完整剧情_第1集.md` 等。

- [ ] **Step 5: 检查摘要文件是否被正确生成和传递**

通过检查后端日志或项目临时文件来确认摘要提取环节已执行。

---

### Task 10: 前端构建 + 全流程验证

- [ ] **Step 1: 构建前端**

Run: `npm run build`  
Expected: Build 成功

- [ ] **Step 2: 打开浏览器进行一次从头到尾的生成体验**

验证每个阶段都能正常完成，内容显示无异常。
