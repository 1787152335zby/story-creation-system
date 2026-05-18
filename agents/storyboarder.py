import re
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, VISUAL_STYLES, SCREEN_ASPECTS
from core.chunk_strategy import ChunkStrategy, ChunkIter
from tools.duration_validator import validate_storyboard_durations


class Storyboarder(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str,
            visual_chars: list = None, visual_scenes: list = None) -> str:
        result = "".join(self.run_stream(project, style, input_content, visual_chars, visual_scenes))
        validated = validate_storyboard_durations(result)
        if validated != result:
            result = validated + "\n\n> ⏱️ 注：部分镜头时长已自动校验修正（对白≥3s，缓慢运镜≥4s，全局≥2s）"
        report = self._validate_storyboard(result)
        if report:
            result += "\n\n---\n\n" + report
        return result

    def _build_variant_table(self, visual_chars: list, visual_scenes: list) -> str:
        """从视觉提取数据构建变体参考表，注入分镜 prompt"""
        lines = ["【角色/场景变体参考表】"]
        lines.append("以下角色和场景有多个形象变体。写分镜时请根据当前事件进度选择正确的变体名。\n")

        bases = [c for c in visual_chars if c.get("is_base")] if visual_chars else []
        for c in bases:
            v_info = ""
            if c.get("variants"):
                v_lines = []
                for v_name in c["variants"]:
                    v_data = next((x for x in visual_chars if x["name"] == v_name), None)
                    if v_data:
                        change = v_data.get("appearance_change", "") or v_data.get("clothing_change", "")
                        trigger = v_data.get("trigger_event", "")
                        v_lines.append(f"    - {v_name}（{change[:40]}，触发：{trigger[:30]}）")
                if v_lines:
                    v_info = "\n" + "\n".join(v_lines)
            lines.append(f"- {c['name']}{v_info}")

        lines.append("")
        scene_bases = [s for s in visual_scenes if s.get("is_base")] if visual_scenes else []
        for s in scene_bases:
            v_info = ""
            if s.get("variants"):
                v_lines = []
                for v_name in s["variants"]:
                    v_data = next((x for x in visual_scenes if x["name"] == v_name), None)
                    if v_data:
                        change = v_data.get("change", "")
                        trigger = v_data.get("trigger_event", "")
                        v_lines.append(f"    - {v_name}（{change[:40]}，触发：{trigger[:30]}）")
                if v_lines:
                    v_info = "\n" + "\n".join(v_lines)
            lines.append(f"- {s['name']}{v_info}")

        return "\n".join(lines)

    def _validate_storyboard(self, content: str) -> str:
        shot_count = len(re.findall(r'镜头\d{3}\s*\|', content))
        char_entries = len(re.findall(r'出场角色：', content))
        scene_entries = len(re.findall(r'场景：', content))
        fade_in = len(re.findall(r'淡入', content))
        fade_out = len(re.findall(r'淡出', content))
        has_end_marker = '【全片完】' in content

        issues = []
        if shot_count == 0:
            issues.append("未检测到符合格式的镜头")
        if char_entries == 0:
            issues.append("缺少「出场角色」字段")
        if scene_entries == 0:
            issues.append("缺少「场景」字段")
        if not has_end_marker:
            issues.append("缺少结束标记【全片完】")

        header_pattern = re.compile(
            r'镜头\d{3}\s*\|\s*[\d.]+s\s*\|\s*.+?\|\s*.+?\|\s*.+?\|\s*.+'
        )
        format_ok = bool(re.search(header_pattern, content))
        if not format_ok:
            issues.append("镜头格式不符合规范")

        shot_total = max(shot_count, 1)
        report = f"【分镜校验】\n"
        report += f"- 镜头总数：{shot_count}\n"
        report += f"- 有出场角色的镜头：{char_entries}/{shot_total}\n"
        report += f"- 有场景标注的镜头：{scene_entries}/{shot_total}\n"
        report += f"- 淡入标记：{fade_in} 处\n"
        report += f"- 淡出标记：{fade_out} 处\n"
        report += f"- 结束标记：{'✅' if has_end_marker else '❌'}\n"
        report += f"- 格式规范：{'✅' if format_ok else '❌'}\n"
        if issues:
            report += f"- 问题：{'；'.join(issues)}\n"
        return report

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str,
                   visual_chars: list = None, visual_scenes: list = None):
        template = self.load_prompt_template("storyboarder.txt")

        # Inject variant reference table into prompt
        variant_table = self._build_variant_table(visual_chars or [], visual_scenes or [])
        template = template.replace("{variant_table}", variant_table)

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
