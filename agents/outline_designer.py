from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig


class OutlineDesigner(AgentBase):
    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
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

        # 检测阶段：根据 input_content 中是否包含"用户选择"或"请生成版本"来判断
        # 如果包含，说明用户已经选择了方向，需要生成完整大纲
        # 如果不包含，说明需要生成方向卡
        if "用户选择" in input_content or "请生成版本" in input_content:
            yield from self._generate_full_outline(
                style, style_context, task, input_content,
                duration_mode_label, episode_total_minutes
            )
        else:
            # 第一阶段：只输出方向卡
            yield from self._generate_direction_card(style_context, task)

    def _generate_direction_card(self, style_context: str, task: str):
        """生成方向卡（第一阶段）"""
        template = self.load_prompt_template("outline_direction_card.txt")
        system_prompt = template.replace("{style_config}", style_context)
        system_prompt = system_prompt.replace("{task}", task)

        # 使用方向卡结束标记，检测到后立即停止
        direction_marker = "【方向卡完毕，请确认】"
        yield from self.call_llm_stream_with_continuation(
            system_prompt,
            "",  # user_prompt 始终为空
            temperature=0.8,
            end_markers=[direction_marker],
            continuation_prompt=""  # 不自动续写
        )

    def _generate_full_outline(self, style: StyleConfig, style_context: str, task: str,
                               input_content: str, duration_mode_label: str, episode_total_minutes: str):
        """生成完整大纲（第二阶段）"""
        template = self.load_prompt_template("outline_full.txt")
        system_prompt = template.replace("{style_config}", style_context)
        system_prompt = system_prompt.replace("{task}", task)
        system_prompt = system_prompt.replace("{version_choice}", input_content)
        system_prompt = system_prompt.replace("{duration_mode}", duration_mode_label)
        system_prompt = system_prompt.replace("{episode_count}", style.episode_count or "（由AI合理分配）")
        system_prompt = system_prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
        system_prompt = system_prompt.replace("{episode_total_minutes}", episode_total_minutes)

        yield from self.call_llm_stream_with_continuation(
            system_prompt,
            "",  # user_prompt 始终为空
            temperature=0.8,
            end_markers=["全文完", "（全文完）", "全片完", "【全片完】"],
            continuation_prompt=""
        )
