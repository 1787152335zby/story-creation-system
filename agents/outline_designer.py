from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig


class OutlineDesigner(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        template = self.load_prompt_template("outline_designer.txt")
        style_context = self.get_style_context(style)

        task = project.read_output("00_任务指令/任务指令.md") or input_content

        duration_mode_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
        episode_total_minutes = "未设置"
        if style.episode_count and style.episode_duration:
            try:
                count = int(style.episode_count)
                duration_str = style.episode_duration.replace("分钟", "").replace("分", "").strip()
                per = int(duration_str) if duration_str.isdigit() else 0
                episode_total_minutes = str(count * per)
            except:
                episode_total_minutes = "未设置"

        system_prompt = template.replace("{style_config}", style_context)
        system_prompt = system_prompt.replace("{task}", task)
        system_prompt = system_prompt.replace("{duration_mode}", duration_mode_label)
        system_prompt = system_prompt.replace("{episode_count}", style.episode_count or "（由AI合理分配）")
        system_prompt = system_prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
        system_prompt = system_prompt.replace("{episode_total_minutes}", episode_total_minutes)

        if input_content and "修改意见" in input_content:
            system_prompt += f"\n\n## 修改意见\n{input_content}"

        yield from self.call_llm_stream_with_continuation(system_prompt, "", temperature=0.8)
