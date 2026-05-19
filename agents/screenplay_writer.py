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
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self._plot_infos = []
        self._last_chunk_output = ""
        self._last_chunk_summary = ""

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def _load_plot_meta(self, project: ProjectManager, input_content: str) -> dict:
        """从剧情文件中提取版本方向、承诺清单、字数信息"""
        meta = {
            "confirmed_direction": "（未设置）",
            "promise_list": "（未设置）",
            "plot_chars": "0",
            "max_script_chars": "0",
        }
        try:
            plot_content = project.read_output("02_完整剧情/完整剧情.md") or input_content
            total_chars = len(plot_content.replace(" ", "").replace("\n", ""))
            meta["plot_chars"] = str(total_chars)
            meta["max_script_chars"] = str(total_chars * 3)
            # 提取方向信息
            direction_match = re.search(r'> ✅ 已选中版本[AB]。(差异摘要.*?)$', plot_content, re.MULTILINE)
            if direction_match:
                meta["confirmed_direction"] = direction_match.group(1).strip()
            # 提取承诺清单
            promise_match = re.search(r'【本故事承诺】.*?(?=\n\n|\Z)', plot_content, re.DOTALL)
            if promise_match:
                meta["promise_list"] = promise_match.group(0).strip()
        except:
            pass
        return meta

    def generate_chunk(self, ctx, template, style_context, writing_style_name, script_style_name, script_format_name, story_type_name, style, plan, input_content, feedback=""):
        self._last_chunk_output = ""

        prompt = template.replace("{style_config}", style_context)
        prompt = template.replace("{plot_structure}", ctx.outline_section or input_content)
        prompt = prompt.replace("{writing_style}", writing_style_name)
        prompt = prompt.replace("{script_style}", script_style_name)
        prompt = prompt.replace("{script_format}", script_format_name)
        prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
        duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
        prompt = prompt.replace("{duration_mode}", duration_label)
        prompt = prompt.replace("{episode_count}", style.episode_count or "（由AI根据大纲合理分配）")
        prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
        prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
        prompt = prompt.replace("{story_type}", story_type_name)

        prev_plot_context = ""
        if self._plot_infos:
            prev_plot_context = "\n\n## 前序剧情回顾（必须与此衔接，保持人物/事件一致）\n\n"
            for act_name, act_plot in self._plot_infos:
                prev_plot_context += f"### {act_name} 剧情\n{act_plot[-2000:]}\n\n"

        prev_screenplay_context = ""
        if ctx.previous_full_texts:
            prev_screenplay_context = "\n\n## 前序剧本回顾（你之前写的内容，保持格式和衔接一致性）\n\n"
            for i, ft in enumerate(ctx.previous_full_texts):
                name = self._plot_infos[i][0] if i < len(self._plot_infos) else "前序"
                prev_screenplay_context += f"### {name} 剧本（已生成）\n{ft[-1500:]}\n\n"

        prompt += prev_plot_context
        prompt += prev_screenplay_context

        prompt += f"\n\n请只写「{ctx.name}」的剧本内容，严格覆盖本幕剧情中的每一个事件。全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**"

        if feedback and ctx.index == plan.chunk_count - 1:
            prompt += f"\n\n## 修改意见\n{feedback}"

        for token in self.call_llm_stream(prompt, "", temperature=0.8):
            self._last_chunk_output += token
            yield token

        if plan.summarize and self._last_chunk_output.strip():
            self._last_chunk_summary = self._extract_summary(ctx.name, self._last_chunk_output)

        self._plot_infos.append((ctx.name, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        template = self.load_prompt_template("screenplay_writer.txt")

        meta = self._load_plot_meta(project, input_content)
        template = template.replace("{confirmed_direction}", meta["confirmed_direction"])
        template = template.replace("{promise_list}", meta["promise_list"])
        template = template.replace("{plot_chars}", meta["plot_chars"])
        template = template.replace("{max_script_chars}", meta["max_script_chars"])

        plot_structure = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            plot_structure = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        script_style_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "视觉化写作")
        script_format_name = {"1": "系统格式", "2": "市场格式"}.get(style.script_format, "系统格式")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")

        plan = ChunkStrategy.get_plan(style.story_type)
        iterator = ChunkIter(plan, plot_structure)

        if plan.chunk_count == 0:
            yield from self._resolve_auto_chunks(iterator, template, plot_structure, style_context,
                                                   writing_style_name, script_style_name,
                                                   story_type_name, style, feedback)
            return

        self._plot_infos = []

        for ctx in iterator:
            yield from self.generate_chunk(ctx, template, style_context, writing_style_name,
                                           script_style_name, script_format_name, story_type_name,
                                           style, plan, plot_structure, feedback)

            chunk_output = self._last_chunk_output

            if chunk_output.strip():
                project.write_output(f"03_完整剧本/完整剧本_{ctx.name}.md", chunk_output)
                all_chunks = []
                for b in iterator.blocks:
                    if b.get("_output", "").strip():
                        all_chunks.append(b["_output"])
                if all_chunks:
                    project.write_output("03_完整剧本/完整剧本.md", "\n\n---\n\n".join(all_chunks))

            if plan.summarize and chunk_output.strip():
                iterator.set_output(ctx.index, chunk_output, self._last_chunk_summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

    def prepare_generation(self, project, style, input_content):
        template = self.load_prompt_template("screenplay_writer.txt")
        meta = self._load_plot_meta(project, input_content)
        template = template.replace("{confirmed_direction}", meta["confirmed_direction"])
        template = template.replace("{promise_list}", meta["promise_list"])
        template = template.replace("{plot_chars}", meta["plot_chars"])
        template = template.replace("{max_script_chars}", meta["max_script_chars"])
        plot_structure = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            plot_structure = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""
        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        script_style_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "视觉化写作")
        script_format_name = {"1": "系统格式", "2": "市场格式"}.get(style.script_format, "系统格式")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
        plan = ChunkStrategy.get_plan(style.story_type)
        iterator = ChunkIter(plan, plot_structure)
        if plan.chunk_count == 0:
            count_prompt = (f"以下是一段剧情描述。请判断应该分为几集/几章来写剧本。"
                            f"只输出一个整数。\n\n{plot_structure[:3000]}")
            count_text = ""
            for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
                count_text += token
            nums = re.findall(r'\d+', count_text)
            chunk_count = int(nums[0]) if nums else 3
            chunk_count = max(1, min(chunk_count, 20))
            iterator.set_auto_blocks(chunk_count)
        self._gen_template = template
        self._gen_style_context = style_context
        self._gen_writing_style_name = writing_style_name
        self._gen_script_style_name = script_style_name
        self._gen_script_format_name = script_format_name
        self._gen_story_type_name = story_type_name
        self._gen_plan = plan
        self._gen_iterator = iterator
        self._gen_input_content = plot_structure
        self._gen_feedback = feedback
        self._plot_infos = []
        chunk_count = len(iterator.blocks)
        chunk_names = [b["name"] for b in iterator.blocks]
        return chunk_count, chunk_names

    def _resolve_auto_chunks(self, iterator, template, input_content, style_context,
                               writing_style_name, script_style_name,
                               story_type_name, style, feedback):
        script_format_name = {"1": "系统格式", "2": "市场格式"}.get(style.script_format, "系统格式")
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

        self._plot_infos = []

        for ctx in iterator:
            prompt = template.replace("{style_config}", style_context)
            prompt = template.replace("{plot_structure}", input_content)
            prompt = template.replace("{writing_style}", writing_style_name)
            prompt = template.replace("{script_style}", script_style_name)
            prompt = prompt.replace("{script_format}", script_format_name)
            prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chunk_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)

            prev_plot_context = ""
            if self._plot_infos:
                prev_plot_context = "\n\n## 前序剧情回顾（必须与此衔接，保持人物/事件一致）\n\n"
                for act_name, act_plot in self._plot_infos:
                    prev_plot_context += f"### {act_name} 剧情\n{act_plot[-2000:]}\n\n"

            prev_screenplay_context = ""
            if ctx.previous_full_texts:
                prev_screenplay_context = "\n\n## 前序剧本回顾（你之前写的内容，保持格式和衔接一致性）\n\n"
                for i, ft in enumerate(ctx.previous_full_texts):
                    name = self._plot_infos[i][0] if i < len(self._plot_infos) else "前序"
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

            self._plot_infos.append((ctx.name, input_content))

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
