from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig
import math


def _build_short_drama_cards(total: int) -> str:
    twist1 = max(12, math.ceil(total * 0.25))
    twist2 = max(twist1 + 6, math.ceil(total * 0.40))
    twist3 = max(twist2 + 10, math.ceil(total * 0.70))
    p4_start = max(math.ceil(total * 0.18) + 1, math.ceil(total * 0.40))
    p5_start = max(p4_start + 1, math.ceil(total * 0.70))
    genre_reversal = max(8, math.ceil(total * 0.15))
    genre_reversal_end = genre_reversal + 3
    deform_ep = max(p4_start + 5, p4_start + (p5_start - p4_start) // 2)
    p4_transition = p5_start - 2
    p6_start = max(p5_start + 1, math.ceil(total * 0.90))
    p5_transition = p6_start - 2
    anchor_ep = max(p4_transition + 5, p4_transition + (p5_transition - p4_transition) // 2)

    return f"""## 短剧结构卡牌系统

以下结构锚点已锁定，大纲中必须对应位置体现：

**强制意外卡×3：**
- 第{twist1}集：最信任主角的人做一件背叛主角的事。不是误解——ta有自己不可告人的目的。
- 第{twist2}集：反派不是纯粹的恶——ta的动机和主角完全一样，ta是同一个系统的另一个受害者。
- 第{twist3}集：真正的敌人不在当前雷达上。之前所有线索在这一点重新洗牌。

**类型反悔卡：**
- 第{genre_reversal}-{genre_reversal_end}集：暂停超自然元素。不管超自然载体以什么形态出现，这几集它是沉默的。信息通过纯日常途径传递（纸条、档案、回忆），不能通过任何超自然触发机制到达角色手中。第{genre_reversal_end}集结尾用一行字或一个画面把超自然元素重新炸回来。

**代价变形卡：**
- 第{deform_ep}集：代价的形态发生性质翻转——不是量变，是"同一种痛换了方向"。如果之前一直在丢东西，这一集开始得到不该得到的东西。如果之前一直在遗忘，这一集突然想起一件不该自己记得的事。

**情感锚点卡：**
- 第{anchor_ep}集：放一集安静的、和主线无关的、让观众想起这个故事底色是什么的时刻。不是新的剧情推进，是一段停在原地的呼吸。例如翻开三年前的记录本，第一个客户是个老太太。

**关系熔铸：**
1. 反派和受害者之间有至少一层私人关系——不是功能标签，是"人需要"。
2. 故事里的死者/被追忆者有名字——不是代号，是一个活人可能被家里人叫的名字。
3. 在信息某条岔路上出现一个第三方——不是主角、不是反派、不是配角——他的存在让整个故事的道德天平倾斜了一度。

这些不是额外剧情——是故事本身在人格层面的纵深。"""


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

        import math
        if style.episode_count and style.episode_count.isdigit():
            ec = int(style.episode_count)
            system_prompt = system_prompt.replace("{anchor40}", str(max(10, math.ceil(ec * 0.40))))
            system_prompt = system_prompt.replace("{anchor50}", str(max(15, math.ceil(ec * 0.50))))
            system_prompt = system_prompt.replace("{anchor70}", str(max(20, math.ceil(ec * 0.70))))
        else:
            for a in ["{anchor40}", "{anchor50}", "{anchor70}"]:
                system_prompt = system_prompt.replace(a, "约中间位置")

        cards = ""
        if style.story_type == "1" and style.episode_count:
            try:
                total = int(style.episode_count)
                cards = _build_short_drama_cards(total)
            except ValueError:
                pass
        system_prompt = system_prompt.replace("{short_drama_cards}", cards)

        yield from self.call_llm_stream_with_continuation(
            system_prompt,
            "",  # user_prompt 始终为空
            temperature=0.8,
            end_markers=["全文完", "（全文完）", "全片完", "【全片完】"],
            continuation_prompt=""
        )
