import re
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, WRITING_STYLES, SCREEN_ASPECTS, STORY_TYPES
from core.chunk_strategy import ChunkStrategy, ChunkIter
from core.summary_extractor import SummaryExtractor


def _calc_total_minutes(style: StyleConfig) -> str:
    """Calculate total minutes from episode_count and episode_duration"""
    if style.duration_mode != "2" or not style.episode_count or not style.episode_duration:
        return "未设置"
    try:
        count = int(style.episode_count)
        d = style.episode_duration.replace("分钟", "").replace("分", "").strip()
        per = int(d) if d.isdigit() else 0
        return str(count * per) if per > 0 else "未设置"
    except:
        return "未设置"


class PlotExpander(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        template = self.load_prompt_template("plot_expander.txt")

        confirmed_direction = ""
        outline_content = project.read_output("01_故事大纲/故事大纲.md") or ""
        direction_match = re.search(r'> ✅ 已选中版本[AB]。(差异摘要.*?)$', outline_content, re.MULTILINE)
        if direction_match:
            confirmed_direction = direction_match.group(1).strip()
        if not confirmed_direction:
            confirmed_direction = "（未设置）"
        template = template.replace("{confirmed_direction}", confirmed_direction)

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

        if plan.bible_mode:
            self._bible_mode = True
            yield from self._generate_novel_chapters(project, template, outline, style_context,
                                                       writing_style_name, screen_aspect_name,
                                                       story_type_name, style, feedback, plan)
            return

        pre_analyzed = ChunkStrategy.pre_analyze_split_points(outline, self.call_llm_stream)
        iterator = ChunkIter(plan, outline, pre_analyzed)

        if plan.chunk_count == 0:
            yield from self._resolve_auto_chunks(iterator, template, outline, style_context,
                                                   writing_style_name, screen_aspect_name,
                                                   story_type_name, style, feedback)
            return

        _outline_blocks = list(iterator.blocks)
        _previous_outline_infos = []

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", ctx.outline_section or outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or "（由AI根据大纲合理分配）")
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)

            prev_outline_context = ""
            if _previous_outline_infos:
                prev_outline_context = "\n\n## 前序大纲回顾（你的剧情必须与此衔接）\n\n"
                for act_name, act_outline in _previous_outline_infos:
                    prev_outline_context += f"### {act_name} 大纲\n{act_outline[-1500:]}\n\n"

            prev_plot_context = ""
            if ctx.previous_full_texts:
                prev_plot_context = "\n\n## 前序剧情回顾（你之前写的内容）\n\n"
                for i, ft in enumerate(ctx.previous_full_texts):
                    name = _previous_outline_infos[i][0] if i < len(_previous_outline_infos) else f"前序"
                    prev_plot_context += f"### {name} 剧情（已生成）\n{ft[-1500:]}\n\n"

            prompt += prev_outline_context
            prompt += prev_plot_context

            if ctx.summaries:
                prompt += "\n\n## 关键元素追踪\n" + "\n".join(ctx.summaries)
            prompt += f"\n\n请只写「{ctx.name}」的内容。全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**"

            if feedback and ctx.index == (iterator.plan.chunk_count or 1) - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            _previous_outline_infos.append((ctx.name, ctx.outline_section))

            if plan.summarize and chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

    def _resolve_auto_chunks(self, iterator, template, outline, style_context,
                               writing_style_name, screen_aspect_name,
                               story_type_name, style, feedback):
        count_prompt = (
            f"以下是一个故事大纲。请判断这个故事应该分为几集/几章。"
            f"考虑故事的长度和复杂度。只输出一个整数，不要其他文字。\n\n"
            f"{outline[:3000]}"
        )
        count_text = ""
        for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
            count_text += token
        nums = re.findall(r'\d+', count_text)
        chunk_count = int(nums[0]) if nums else 3
        chunk_count = max(1, min(chunk_count, 20))
        iterator.set_auto_blocks(chunk_count)

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chunk_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)

            if ctx.previous_full_texts:
                bridge = "\n\n## 上文回顾\n\n"
                for ft in ctx.previous_full_texts:
                    bridge += ft[-1500:] + "\n\n"
                prompt += bridge
            if ctx.summaries:
                prompt += "\n\n## 关键元素追踪\n" + "\n".join(ctx.summaries)
            prompt += f"\n\n请只写「{ctx.name}」的内容，这是系列的第{ctx.index+1}部分。全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**"

            if feedback and ctx.index == iterator.plan.chunk_count - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            if chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

    def _generate_novel_chapters(self, project, template, outline, style_context,
                                   writing_style_name, screen_aspect_name,
                                   story_type_name, style, feedback, plan):
        from core.novel_bible import BibleManager, BibleFormatter
        from core.bible_updater import BibleUpdater

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

        bible = BibleManager.load(project.project_dir)

        for chapter_num in range(1, chapter_count + 1):
            recent_summaries = []
            for i in range(max(1, chapter_num - plan.context_window), chapter_num):
                if i in bible.chapter_summaries:
                    recent_summaries.append(f"第{i}章: {bible.chapter_summaries[i]}")

            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chapter_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)

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

            if chapter_output.strip():
                chapter_file = f"02_完整剧情/第{chapter_num:03d}章.md"
                project.write_output(chapter_file, chapter_output)
                try:
                    bible = BibleUpdater.update(bible, chapter_num, chapter_output, self.call_llm_stream)
                    BibleManager.save(bible, project.project_dir)
                except Exception:
                    pass

    def _extract_summary(self, chunk_name: str, content: str) -> str:
        summary_prompt = SummaryExtractor.build_summary_prompt(chunk_name, content)
        summary_raw = ""
        for token in self.call_llm_stream(summary_prompt, "", temperature=0.3):
            summary_raw += token
        return SummaryExtractor.parse_summary(summary_raw)

    def _extract_promise_list(self, outline_content: str) -> str:
        if not outline_content:
            return "（无大纲内容）"
        prompt = (
            "以下是一个故事大纲。请分析并输出该故事必须包含的角色、关键事件和核心冲突。\n"
            "格式如下，不要额外内容：\n"
            "```\n"
            "【本故事承诺】\n"
            "- 必须出场的角色：XXX、XXX\n"
            "- 必须发生的关键事件：XXX、XXX\n"
            "- 必须解决的核心冲突：XXX\n"
            "```\n\n"
            f"{outline_content[:4000]}"
        )
        result = ""
        for token in self.call_llm_stream(prompt, "", temperature=0.3):
            result += token
        match = re.search(r'【本故事承诺】.*', result, re.DOTALL)
        return match.group(0) if match else "（未能提取承诺清单）"
