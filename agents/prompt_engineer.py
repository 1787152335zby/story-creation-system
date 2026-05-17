from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, VISUAL_STYLES, RENDER_STYLES
from core.chunk_strategy import ChunkStrategy, ChunkIter


class PromptEngineer(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str, platform: str = "Seedance 2.0") -> str:
        return "".join(self.run_stream(project, style, input_content, platform))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str, platform: str = "Seedance 2.0"):
        template = self.load_prompt_template("prompt_engineer.txt")

        storyboard = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            storyboard = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        visual_style_name = VISUAL_STYLES.get(style.visual_style, {}).get("name", "未指定")
        art_style_name = RENDER_STYLES.get(style.art_style, {}).get("name", "自动适配")
        style_context = self.get_style_context(style)

        plan = ChunkStrategy.get_plan(style.story_type)
        iterator = ChunkIter(plan, storyboard)

        if plan.chunk_count > 0 and plan.chunk_names:
            _previous_storyboard_texts = []

            for ctx in iterator:
                prompt = template.replace("{style_config}", style_context)
                prompt = prompt.replace("{storyboard}", ctx.outline_section or storyboard)
                prompt = prompt.replace("{visual_style}", visual_style_name)
                prompt = prompt.replace("{art_style}", art_style_name)
                prompt = prompt.replace("{visual_reference}", style.visual_reference or "无")
                prompt = prompt.replace("{action_reference}", style.action_reference or "无")
                prompt = prompt.replace("{platform}", platform)

                prev_storyboard_context = ""
                if _previous_storyboard_texts:
                    prev_storyboard_context = "\n\n## 前序分镜回顾（必须与此衔接，保持人物/场景/服装一致）\n\n"
                    for i, ps in enumerate(_previous_storyboard_texts):
                        prev_storyboard_context += f"{ps[-2000:]}\n\n"

                prev_prompt_context = ""
                if ctx.previous_full_texts:
                    prev_prompt_context = "\n\n## 前序提示词回顾（你之前写的提示词）\n\n"
                    for ft in ctx.previous_full_texts:
                        prev_prompt_context += ft[-1500:] + "\n\n"

                prompt += prev_storyboard_context
                prompt += prev_prompt_context

                prompt += f"\n\n请只写「{ctx.name}」的提示词内容。全部内容输出完毕后，请在末尾加上结束标记：**【全片完】**"

                if feedback and ctx.index == plan.chunk_count - 1:
                    prompt += f"\n\n## 修改意见\n{feedback}"

                chunk_output = ""
                for token in self.call_llm_stream(prompt, "", temperature=0.7):
                    chunk_output += token
                    yield token

                _previous_storyboard_texts.append(ctx.outline_section)
                iterator.set_output(ctx.index, chunk_output)

                if chunk_output.strip():
                    project.write_output(f"05_提示词/提示词_{ctx.name}.md", chunk_output)
                    all_chunks = []
                    for b in iterator.blocks:
                        if b.get("_output", "").strip():
                            all_chunks.append(b["_output"])
                    if all_chunks:
                        project.write_output("05_提示词/提示词.md", "\n\n---\n\n".join(all_chunks))

            self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]
        else:
            system_prompt = template.replace("{style_config}", style_context)
            system_prompt = system_prompt.replace("{storyboard}", storyboard)
            system_prompt = system_prompt.replace("{visual_style}", visual_style_name)
            system_prompt = system_prompt.replace("{art_style}", art_style_name)
            system_prompt = system_prompt.replace("{visual_reference}", style.visual_reference or "无")
            system_prompt = system_prompt.replace("{action_reference}", style.action_reference or "无")
            system_prompt = system_prompt.replace("{platform}", platform)
            system_prompt += "\n\n全部内容输出完毕后，请在末尾加上结束标记：**【全片完】**"

            if feedback:
                system_prompt += f"\n\n## 修改意见\n{feedback}"

            yield from self.call_llm_stream_with_continuation(system_prompt, "", temperature=0.7)
