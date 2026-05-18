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
        bases = [c for c in chars if c.get("is_base")]
        variants = [c for c in chars if not c.get("is_base")]
        scene_bases = [s for s in scenes if s.get("is_base")]
        scene_variants = [s for s in scenes if not s.get("is_base")]

        report = f"✅ 角色/场景提取完成\n\n"
        report += f"## 主要角色（{len([c for c in bases if c.get('type')=='main'])}个）\n"
        for c in bases:
            if c.get("type") != "main":
                continue
            v = ""
            if c.get("variants"):
                v = f"（{len(c['variants'])}个变体）"
            features = ""
            if c.get("key_features"):
                features = f"\n   标志特征：{'、'.join(c['key_features'][:3])}"
            report += f"- **{c['name']}**{v}\n"
            report += f"  {c.get('age','?')}岁 {c.get('gender','?')} · {c.get('expression','')}\n"
            report += f"  服装：{c.get('clothing','')[:80]}{features}\n"

        report += f"\n## 次要角色（{len([c for c in bases if c.get('type')!='main'])}个）\n"
        for c in bases:
            if c.get("type") == "main":
                continue
            report += f"- {c['name']}（{c.get('age','?')}岁 {c.get('gender','?')}）\n"

        if variants:
            report += f"\n## 角色变体（{len(variants)}个）\n"
            for v in variants:
                report += f"- {v['name']}（源于：{v.get('trigger_event','')}）\n"

        report += f"\n## 场景（{len(scene_bases)}个）\n"
        for s in scene_bases:
            v = ""
            if s.get("variants"):
                v = f"（{len(s['variants'])}个变体）"
            report += f"- **{s['name']}**{v}\n"
            report += f"  {s.get('environment','')[:80]}\n"

        if scene_variants:
            report += f"\n## 场景变体（{len(scene_variants)}个）\n"
            for v in scene_variants:
                report += f"- {v['name']}（源于：{v.get('trigger_event','')}）\n"

        report += f"\n⚠️ 请检查提取结果，在生图页面确认或修改"
        yield report
