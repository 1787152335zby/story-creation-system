import re
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, WRITING_STYLES, SCREEN_ASPECTS, SCRIPT_STYLES, STORY_TYPES
from core.chunk_strategy import ChunkStrategy, ChunkIter
from core.summary_extractor import SummaryExtractor


def _calc_total_minutes(style: StyleConfig) -> str:
    if style.duration_mode != "2" or not style.episode_count or not style.episode_duration:
        return "未设置"
    try:
        count = int(style.episode_count)
        d = style.episode_duration.replace("分钟", "").replace("分", "").strip()
        per = int(d) if d.isdigit() else 0
        return str(count * per) if per > 0 else "未设置"
    except:
        return "未设置"


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

        _plot_blocks = list(iterator.blocks)
        _previous_plot_infos = []

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{plot_structure}", ctx.outline_section or plot_structure)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{script_style}", script_style_name)
            prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or "（由AI根据大纲合理分配）")
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)

            prev_plot_context = ""
            if _previous_plot_infos:
                prev_plot_context = "\n\n## 前序剧情回顾（必须与此衔接，保持人物/事件一致）\n\n"
                for act_name, act_plot in _previous_plot_infos:
                    prev_plot_context += f"### {act_name} 剧情\n{act_plot[-2000:]}\n\n"

            prev_screenplay_context = ""
            if ctx.previous_full_texts:
                prev_screenplay_context = "\n\n## 前序剧本回顾（你之前写的内容，保持格式和衔接一致性）\n\n"
                for i, ft in enumerate(ctx.previous_full_texts):
                    name = _previous_plot_infos[i][0] if i < len(_previous_plot_infos) else f"前序"
                    prev_screenplay_context += f"### {name} 剧本（已生成）\n{ft[-1500:]}\n\n"

            prompt += prev_plot_context
            prompt += prev_screenplay_context

            prompt += f"\n\n请只写「{ctx.name}」的剧本内容，严格覆盖本幕剧情中的每一个事件。全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**"

            if feedback and ctx.index == plan.chunk_count - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            _previous_plot_infos.append((ctx.name, ctx.outline_section))

            if chunk_output.strip():
                project.write_output(f"03_完整剧本/完整剧本_{ctx.name}.md", chunk_output)
                all_chunks = []
                for b in iterator.blocks:
                    if b.get("_output", "").strip():
                        all_chunks.append(b["_output"])
                if all_chunks:
                    project.write_output("03_完整剧本/完整剧本.md", "\n\n---\n\n".join(all_chunks))

            if plan.summarize and chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

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
        nums = re.findall(r'\d+', count_text)
        chunk_count = int(nums[0]) if nums else 3
        chunk_count = max(1, min(chunk_count, 20))
        iterator.set_auto_blocks(chunk_count)

        _plot_blocks = list(iterator.blocks)
        _previous_plot_infos = []

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{plot_structure}", input_content)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{script_style}", script_style_name)
            prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chunk_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)

            prev_plot_context = ""
            if _previous_plot_infos:
                prev_plot_context = "\n\n## 前序剧情回顾（必须与此衔接，保持人物/事件一致）\n\n"
                for act_name, act_plot in _previous_plot_infos:
                    prev_plot_context += f"### {act_name} 剧情\n{act_plot[-2000:]}\n\n"

            prev_screenplay_context = ""
            if ctx.previous_full_texts:
                prev_screenplay_context = "\n\n## 前序剧本回顾（你之前写的内容，保持格式和衔接一致性）\n\n"
                for i, ft in enumerate(ctx.previous_full_texts):
                    name = _previous_plot_infos[i][0] if i < len(_previous_plot_infos) else f"前序"
                    prev_screenplay_context += f"### {name} 剧本（已生成）\n{ft[-1500:]}\n\n"

            prompt += prev_plot_context
            prompt += prev_screenplay_context

            prompt += f"\n\n请只写「{ctx.name}」的剧本内容，严格覆盖本集剧情中的每一个事件。全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**"

            if feedback and ctx.index == chunk_count - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            _previous_plot_infos.append((ctx.name, input_content))

            if chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

    def _extract_summary(self, chunk_name: str, content: str) -> str:
        summary_prompt = SummaryExtractor.build_summary_prompt(chunk_name, content)
        summary_raw = ""
        for token in self.call_llm_stream(summary_prompt, "", temperature=0.3):
            summary_raw += token
        return SummaryExtractor.parse_summary(summary_raw)
