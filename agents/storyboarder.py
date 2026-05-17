from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, VISUAL_STYLES, SCREEN_ASPECTS
from core.chunk_strategy import ChunkStrategy, ChunkIter
from tools.duration_validator import validate_storyboard_durations


class Storyboarder(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        result = "".join(self.run_stream(project, style, input_content))
        validated = validate_storyboard_durations(result)
        if validated != result:
            return validated + "\n\n> ⏱️ 注：部分镜头时长已自动校验修正（对白≥3s，缓慢运镜≥4s，全局≥2s）"
        return validated

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        template = self.load_prompt_template("storyboarder.txt")

        full_plot = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            full_plot = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        visual_style_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "未指定")
        screen_aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
        style_context = self.get_style_context(style)

        plan = ChunkStrategy.get_plan(style.story_type)
        iterator = ChunkIter(plan, full_plot)

        if plan.chunk_count > 0 and plan.chunk_names:
            _previous_full_plot_texts = []

            for ctx in iterator:
                prompt = template.replace("{style_config}", style_context)
                prompt = prompt.replace("{full_plot}", ctx.outline_section or full_plot)
                prompt = prompt.replace("{visual_style}", visual_style_name)
                prompt = prompt.replace("{screen_aspect}", screen_aspect_name)

                prev_full_plot_context = ""
                if _previous_full_plot_texts:
                    prev_full_plot_context = "\n\n## 前序剧本回顾（必须与此衔接，保持人物/事件/场景一致）\n\n"
                    for i, pp in enumerate(_previous_full_plot_texts):
                        prev_full_plot_context += f"{pp[-2000:]}\n\n"

                prev_storyboard_context = ""
                if ctx.previous_full_texts:
                    prev_storyboard_context = "\n\n## 前序分镜回顾（你之前的分镜输出，保持格式和衔接一致性）\n\n"
                    for ft in ctx.previous_full_texts:
                        prev_storyboard_context += ft[-1500:] + "\n\n"

                prompt += prev_full_plot_context
                prompt += prev_storyboard_context

                prompt += f"\n\n请只写「{ctx.name}」的分镜内容。全部内容输出完毕后，请在末尾加上结束标记：**【全片完】**"

                if feedback and ctx.index == plan.chunk_count - 1:
                    prompt += f"\n\n## 修改意见\n{feedback}"

                chunk_output = ""
                for token in self.call_llm_stream(prompt, "", temperature=0.7):
                    chunk_output += token
                    yield token

                _previous_full_plot_texts.append(ctx.outline_section)
                iterator.set_output(ctx.index, chunk_output)
            self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]
        else:
            system_prompt = template.replace("{style_config}", style_context)
            system_prompt = system_prompt.replace("{full_plot}", full_plot)
            system_prompt = system_prompt.replace("{visual_style}", visual_style_name)
            system_prompt = system_prompt.replace("{screen_aspect}", screen_aspect_name)
            system_prompt += "\n\n全部内容输出完毕后，请在末尾加上结束标记：**【全片完】**"

            if feedback:
                system_prompt += f"\n\n## 修改意见\n{feedback}"

            yield from self.call_llm_stream_with_continuation(system_prompt, "", temperature=0.7)
