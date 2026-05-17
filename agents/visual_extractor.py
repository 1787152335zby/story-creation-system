from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.visual_bible import VisualBibleExtractor


class VisualExtractor(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        data = VisualBibleExtractor.extract_all(project)
        chars = data.get("characters", [])
        scenes = data.get("scenes", [])
        mains = [c for c in chars if c.get("type") == "main"]
        minors = [c for c in chars if c.get("type") != "main"]
        report = f"✅ 角色/场景提取完成\n\n"
        report += f"主要角色（{len(mains)}个）：{'、'.join(c['name'] for c in mains[:5])}\n"
        report += f"次要角色（{len(minors)}个）：{'、'.join(c['name'] for c in minors[:5])}\n"
        report += f"场景（{len(scenes)}个）：{'、'.join(s['name'] for s in scenes[:5])}\n"
        report += f"\n⚠️ 请检查提取结果，在生图页面确认或修改"
        yield report
