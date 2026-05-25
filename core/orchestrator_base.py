import re
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
from core.workflow_loader import WorkflowLoader


def _split_sort_key(filename: str) -> int:
    """对分幕文件名进行排序，返回排序关键字"""
    nums = re.findall(r'[一二三四五六七八九十\d]+', filename)
    if nums:
        raw = nums[0]
        if raw.isdigit():
            return int(raw)
        total = 0
        _CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        for ch in raw:
            total = total * 10 + _CN.get(ch, 0)
        return total if total > 0 else 99
    return 0


class OrchestratorBase(AgentBase):
    """Orchestrator 基类 - 包含公共逻辑"""
    
    PHASE_OUTPUT_MAP = {
        "01_故事大纲/": "故事大纲.md",
        "02_完整剧情/": "完整剧情.md",
        "03_完整剧本/": "完整剧本.md",
        "04_角色场景/": "角色场景.md",
        "05_分镜脚本/": "分镜脚本.md",
        "06_生图需求/": "分析报告.md",
    }
    
    INPUT_SOURCE_MAP = {
        "plot_expander": "01_故事大纲/故事大纲.md",
        "screenplay_writer": "02_完整剧情/完整剧情.md",
        "storyboarder": "03_完整剧本/完整剧本.md",
        "image_preparator": "05_分镜脚本/分镜脚本.md",
    }
    
    def get_output_path(self, phase) -> str:
        """获取阶段的输出路径"""
        output = phase.output
        if output.endswith("/"):
            return output + self.PHASE_OUTPUT_MAP.get(output, "产出.md")
        return output
    
    def get_input_content(self, project: ProjectManager, phase) -> str:
        """获取阶段的输入内容（自动合并分幕文件）"""
        source = self.INPUT_SOURCE_MAP.get(phase.agent)
        if not source:
            return ""
        
        dir_path = project.project_dir / Path(source).parent
        base_name = Path(source).stem
        
        split_files = sorted(dir_path.glob(f"*/{base_name}.md"), key=lambda f: _split_sort_key(str(f)))
        if not split_files:
            split_files = sorted(dir_path.glob(f"{base_name}_*.md"), key=lambda f: _split_sort_key(f.name))
        if not split_files:
            split_files = sorted(dir_path.glob("*_[0-9][0-9]_*.md"), key=lambda f: _split_sort_key(f.name))
        
        if split_files:
            parts = [project.read_output(str(sf.relative_to(project.project_dir))) for sf in split_files]
            content = "\n\n---\n\n".join(p for p in parts if p)
            return content
        
        return project.read_output(source) or ""
    
    def load_split_content(self, project: ProjectManager, input_source: str) -> str:
        """加载分幕文件内容并合并"""
        dir_path = project.project_dir / Path(input_source).parent
        split_files = sorted(dir_path.glob("*_[0-9][0-9]_*.md"), key=lambda f: _split_sort_key(f.name))
        
        if split_files:
            parts = []
            for sf in split_files:
                c = project.read_output(str(sf.relative_to(project.project_dir)))
                if c:
                    parts.append(c)
            return "\n\n---\n\n".join(parts) if parts else ""
        
        return project.read_output(input_source) or ""
    
    def fix_character_format(self, content: str) -> str:
        """强制修正人物设定排版"""
        keys_pattern = r'(姓名|外表|性格|背景|目标|动机)[：:]'
        result = []
        for line in content.split('\n'):
            stripped = line.strip()
            matches = list(re.re_iter(keys_pattern, stripped))
            if len(matches) >= 2:
                parts = re.split(r'(?=姓名[：:]|外表[：:]|性格[：:]|背景[：:]|目标[：:]|动机[：:])', stripped)
                fixed = '\n'.join(p for p in parts if p.strip())
                result.append(fixed)
            else:
                result.append(line)
        return '\n'.join(result)
    
    def wrap_long_text(self, content: str, max_chars: int = 80) -> str:
        """对叙事文本做自动换行"""
        lines = content.split('\n')
        result = []
        for line in lines:
            stripped = line.rstrip()
            if (stripped.startswith('镜头') or
                stripped.startswith('淡入') or
                stripped.startswith('淡出') or
                stripped.startswith('硬切') or
                stripped.startswith('溶镜') or
                stripped.startswith('猛切') or
                stripped.startswith('出场角色') or
                stripped.startswith('场景') or
                stripped.startswith('---') or
                stripped.startswith('```') or
                stripped.startswith('|') or
                not stripped):
                result.append(line)
                continue
            if len(stripped) > max_chars and not stripped.startswith('#'):
                wrapped = re.sub(
                    r'([。！？；…])(?![」』）】\n])',
                    r'\1\n',
                    stripped
                )
                final_lines = []
                for wl in wrapped.split('\n'):
                    if len(wl) > max_chars + 20:
                        wl = re.sub(r'([，、；：])', r'\1\n', wl)
                    final_lines.append(wl)
                result.append('\n'.join(final_lines))
            else:
                result.append(line)
        return '\n'.join(result)
    
    def normalize_chunk_heading(self, chunk_output: str, display_name: str) -> str:
        """确保分镜/剧本的每集输出以 # 第N集 开头"""
        text = chunk_output.strip()
        episode_match = re.search(r'^(#{1,4}\s*第\d+[集章部篇])', text, re.MULTILINE)
        if episode_match:
            return text[episode_match.start():]
        for token in ["###", "##", "---", "镜头", "【全片完】"]:
            idx = text.find(token)
            if idx >= 0:
                text = text[idx:]
                break
        if not text.startswith("#"):
            text = f"# {display_name}\n\n{text}"
        return text
