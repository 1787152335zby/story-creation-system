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

    @staticmethod
    def _parse_episode_blocks(text: str) -> list:
        """按集/章标题自动拆分剧本内容，只匹配 H1/H2 级别标题"""
        import re
        # 匹配 # 第X集、## 第X集、# 第一幕 等格式
        # 只匹配 H1/H2，避免误匹配 ### 第X场 等场景标题
        pattern = re.compile(r'^#{1,2}\s+(第\d+[集章部篇]|第\d+集|第一幕|第二幕|第三幕|第\d+章|第\d+部|第\d+篇).*', re.MULTILINE)
        matches = list(pattern.finditer(text))
        blocks = []
        for i, m in enumerate(matches):
            label = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            blocks.append({"index": i, "name": label, "content": content})
        return blocks

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

        # 从角色-场景映射表自动加载视觉数据
        if visual_chars is None or visual_scenes is None:
            from core.visual_bible import VisualBibleExtractor
            all_chars = VisualBibleExtractor.list_characters(project)
            all_scenes = VisualBibleExtractor.list_scenes(project)
            if visual_chars is None:
                visual_chars = all_chars
            if visual_scenes is None:
                visual_scenes = all_scenes

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

        # 当 chunk_count==0 时，自动按集/章分隔符拆块
        parsed_blocks = None
        if plan.chunk_count == 0 or not plan.chunk_names:
            parsed_blocks = self._parse_episode_blocks(full_plot)
            if parsed_blocks and len(parsed_blocks) > 1:
                plan.chunk_count = len(parsed_blocks)
                plan.chunk_names = [b["name"] for b in parsed_blocks]

        if plan.chunk_count > 0 and plan.chunk_names:
            self._plot_texts = []
            iterator = ChunkIter(plan, full_plot)
            # _parse_fixed 的 delimiter 缺少捕获组，导致标签和内容错位
            # 用预解析的 blocks 覆盖
            if parsed_blocks and len(parsed_blocks) == plan.chunk_count:
                iterator.blocks = parsed_blocks

            for ctx in iterator:
                yield from self.generate_chunk(ctx, template, style_context, visual_style_name,
                                               screen_aspect_name, "", style, plan, full_plot,
                                               self._plot_texts, feedback=feedback, variant_table=variant_table)
                chunk_output = getattr(self, '_last_chunk_output', '')
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

    def prepare_generation(self, project, style, input_content):
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
        parsed_blocks = None
        if plan.chunk_count == 0 or not plan.chunk_names:
            parsed_blocks = self._parse_episode_blocks(full_plot)
            if parsed_blocks and len(parsed_blocks) > 1:
                plan.chunk_count = len(parsed_blocks)
                plan.chunk_names = [b["name"] for b in parsed_blocks]
            elif style.episode_count and style.episode_count.isdigit() and int(style.episode_count) > 0:
                # 用户配置了集数但解析失败时，使用配置值
                plan.chunk_count = int(style.episode_count)
                plan.chunk_names = [f"第{i+1}集" for i in range(plan.chunk_count)]
        if plan.chunk_count == 0 or not plan.chunk_names:
            return 0, []
        iterator = ChunkIter(plan, full_plot)
        # 用预解析的 blocks 覆盖 _parse_fixed 的错误结果
        if parsed_blocks and len(parsed_blocks) == plan.chunk_count:
            iterator.blocks = parsed_blocks
        self._gen_template = template
        self._gen_style_context = style_context
        self._gen_writing_style_name = visual_style_name
        self._gen_screen_aspect_name = screen_aspect_name
        self._gen_story_type_name = ""
        self._gen_plan = plan
        self._gen_iterator = iterator
        self._gen_outline = full_plot
        self._gen_feedback = feedback
        self._plot_texts = []
        chunk_count = len(iterator.blocks)
        chunk_names = [b["name"] for b in iterator.blocks]
        return chunk_count, chunk_names

    def generate_chunk(self, ctx, template, style_context, writing_style_name,
                       screen_aspect_name, story_type_name, style, plan, outline,
                       plot_texts=None, feedback="", variant_table="", chunk_name=""):
        self._last_chunk_output = ""
        prompt = template.replace("{style_config}", style_context)
        prompt = prompt.replace("{full_plot}", ctx.outline_section or outline)
        prompt = prompt.replace("{visual_style}", writing_style_name)
        prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
        if "{variant_table}" in prompt:
            prompt = prompt.replace("{variant_table}", "")

        if plot_texts is None:
            plot_texts = self._plot_texts if hasattr(self, '_plot_texts') else []

        prev_full_plot_context = ""
        if plot_texts:
            prev_full_plot_context = "\n\n## 前序剧本回顾（必须与此衔接，保持人物/事件/场景一致）\n\n"
            for pp in plot_texts:
                prev_full_plot_context += f"{pp[-2000:]}\n\n"

        prev_storyboard_context = ""
        if ctx.previous_full_texts:
            prev_storyboard_context = "\n\n## 前序分镜回顾（你之前的分镜输出，保持格式和衔接一致性）\n\n"
            for ft in ctx.previous_full_texts:
                prev_storyboard_context += ft[-1500:] + "\n\n"

        prompt += prev_full_plot_context
        prompt += prev_storyboard_context

        prompt += f"\n\n请只写「{ctx.name}」的分镜内容，开头务必以 Markdown 标题标明「## {ctx.name}」。全部内容输出完毕后，请在末尾加上结束标记：**【全片完】**"

        if getattr(ctx, 'spatial_state', None):
            prompt += f"\n\n**上一镜空间状态（必须延续）：**\n{ctx.spatial_state}"

        prompt += f"\n\n当前正在生成：{chunk_name}"

        if feedback and ctx.index == (plan.chunk_count or 1) - 1:
            prompt += f"\n\n## 修改意见\n{feedback}"

        chunk_output = ""
        for token in self.call_llm_stream(prompt, "", temperature=0.7):
            chunk_output += token
            yield token

        self._last_chunk_output = chunk_output
        if plot_texts is not None:
            plot_texts.append(ctx.outline_section)
        self._plot_texts = plot_texts
