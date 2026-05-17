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

        system_prompt = template.replace("{style_config}", style_context)
        system_prompt = system_prompt.replace("{task}", task)

        if input_content and "修改意见" in input_content:
            system_prompt += f"\n\n## 修改意见\n{input_content}"

        yield from self.call_llm_stream_with_continuation(system_prompt, "", temperature=0.8)
