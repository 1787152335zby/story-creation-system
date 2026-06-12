import re
import json
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, WRITING_STYLES, SCREEN_ASPECTS, STORY_TYPES
from core.chunk_strategy import ChunkStrategy, ChunkIter
from core.summary_extractor import SummaryExtractor
from core.voice_labels import extract_voice_labels, format_voice_injection, build_hard_constraint_card
from core.story_bible import format_bible_injection, build_bible_update, BIBLE_UPDATE_INTERVAL, load_bible, save_bible


def _load_beat_sheet(project) -> list:
    """加载节拍表JSON，不存在则返回空列表"""
    try:
        raw = project.read_output("01b_节拍表/beat_sheet.json") or ""
        if raw.strip():
            return json.loads(raw)
    except:
        pass
    return []


def _get_beat_for_ep(beat_sheet: list, ep_num: int) -> dict:
    """获取指定集的节拍"""
    for b in beat_sheet:
        if b.get("episode") == ep_num:
            return b
    return {}


def _format_beat_injection(beat: dict) -> str:
    """将单集节拍格式化为prompt注入文本"""
    if not beat or not beat.get("task"):
        return ""
    return (
        f"\n\n## 本集节拍约束\n"
        f"- 本集事件链：{beat.get('task', '')}\n"
        f"- 只能释放一块信息：{beat.get('info_piece', '')}\n"
        f"- 结尾必须是这个画面（观众知道角色不知道的事）：{beat.get('hook', '')}\n"
        f"- 角色关系变化：{beat.get('relationship_shift', '')}\n"
        f"- 剧情阶段：{beat.get('phase', '')}"
    )


def _calc_total_minutes(style: StyleConfig) -> str:
    """Calculate total minutes from episode_count and episode_duration"""
    if style.duration_mode != "2" or not style.episode_count or not style.episode_duration:
        return "未设置"
    try:
        count = int(style.episode_count)
        d = style.episode_duration.replace("分钟", "").replace("分", "").strip()
        per = int(d) if d.isdigit() else 0
        return str(count * per) if per > 0 else "未设置"
    except:
        return "未设置"


def _type_specific_rules(story_type_id: str) -> str:
    RULES = {
        "1": (
            "【短剧专用规则】\n"
            "- 每集 1-2 分钟，每 30 秒必须有一个让观众记住的点（反转/爆点/金句）\n"
            "- 每集只推进一件事，结尾必留钩子\n"
            "- 场景极简（1-3 个），对白短促，情绪密度极高\n"
            "- 避免长铺垫，信息通过冲突递出\n"
            '- 禁止「后来」和「第二天」，一集 = 一个连续的时间段\n'
        ),
        "2": (
            "【电影专用规则】\n"
            "- 三幕结构：第一幕建立世界和欲望 → 第二幕对抗升级 → 第三幕最终对决\n"
            "- 第一幕结尾必有意料之外的事件（inciting incident）\n"
            "- 中点（全片 50%）必须是主角从被动变主动的转折\n"
            "- 每幕内部有自己的起承转合\n"
            "- 结尾必须有情绪余韵，不戛然而止\n"
        ),
        "3": (
            "【电视剧专用规则】\n"
            "- 多线叙事：A线（主线）+ B线（副线）+ 可选的 C线（支线），每集至少切换一次\n"
            '- 每集结尾必须留悬念——观众必须在 3 秒内决定「看下一集」\n'
            "- 每集有自己的单元冲突，同时推进季度主线\n"
            "- 配角要有独立弧光，不只是主角的陪衬\n"
            "- 第 1 集必须建立世界+引出核心悬念\n"
        ),
        "4": (
            "【小说专用规则】\n"
            "- 章节节奏：每章 3000-5000 字，开头抓人、中段推进、结尾留钩\n"
            "- 允许心理描写和内心独白，但每次不超过 200 字\n"
            '- 每章至少 1 个「读者会记住的场景」\n'
            "- 伏笔回收周期：小型 3-5 章，中大型 10-20 章\n"
            "- 角色成长要有梯度，不能一蹴而就\n"
        ),
        "5": (
            "【舞台剧专用规则】\n"
            "- 三幕结构，但每幕时长均匀（各约 30-40 分钟）\n"
            "- 场景受限（2-5 个主要场景），通过对话和动作交代空间变化\n"
            "- 对白占 80%+，是驱动剧情的主要手段\n"
            "- 每个角色进场和退场都必须有戏剧性理由\n"
            "- 独白是武器，但全剧不超过 3 段独白\n"
        ),
        "6": (
            "【广播剧专用规则】\n"
            "- 全程无画面，靠声音叙事——环境音 + 对白 + 音效 = 全部\n"
            "- 每场开场必须用 1 句环境音描述建立空间感\n"
            "- 对白要区分远近感（近/中/远），角色移动通过声音变化表现\n"
            "- 关键动作必须通过音效或对白间接传达（听众看不见）\n"
            "- 每集结尾用声音悬念代替视觉悬念\n"
        ),
    }
    return RULES.get(story_type_id, "")


class PlotExpander(AgentBase):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.minimalist = False
        self.douyin = False

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        if self.douyin:
            template = self.load_prompt_template("plot_expander_douyin.txt")
        else:
            template = self.load_prompt_template("plot_expander.txt")

        self._gen_beat_sheet = _load_beat_sheet(project)
        self._voice_injection = ""

        confirmed_direction = ""
        outline_content = project.read_output("01_故事大纲/故事大纲.md") or ""
        if self.douyin and outline_content:
            self._voice_injection = format_voice_injection(extract_voice_labels(outline_content))
            self._constraint_card = build_hard_constraint_card(outline_content)
        self._project_dir = project.project_dir
        direction_match = re.search(r'> ✅ 已选中版本[AB]。(差异摘要.*?)$', outline_content, re.MULTILINE)
        if direction_match:
            confirmed_direction = direction_match.group(1).strip()
        if not confirmed_direction:
            confirmed_direction = "（未设置）"
        template = template.replace("{confirmed_direction}", confirmed_direction)

        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            outline = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""
        else:
            outline = input_content

        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        screen_aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")

        plan = ChunkStrategy.get_plan(style.story_type)

        if plan.bible_mode:
            self._bible_mode = True
            yield from self._generate_novel_chapters(project, template, outline, style_context,
                                                       writing_style_name, screen_aspect_name,
                                                       story_type_name, style, feedback, plan)
            return

        pre_analyzed = ChunkStrategy.pre_analyze_split_points(outline, self.call_llm_stream)
        iterator = ChunkIter(plan, outline, pre_analyzed)

        if plan.chunk_count == 0:
            yield from self._resolve_auto_chunks(iterator, template, outline, style_context,
                                                   writing_style_name, screen_aspect_name,
                                                   story_type_name, style, feedback)
            return

        _outline_blocks = list(iterator.blocks)
        self._outline_infos = []

        for ctx in iterator:
            yield from self.generate_chunk(ctx, template, style_context, writing_style_name,
                                           screen_aspect_name, story_type_name, style, plan,
                                           outline, feedback=feedback)
            chunk_output = getattr(self, '_last_chunk_output', '')
            if plan.summarize and chunk_output.strip():
                summary = getattr(self, '_last_chunk_summary', '')
                iterator.set_output(ctx.index, chunk_output, summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

    def prepare_generation(self, project, style, input_content):
        """为逐集生成做初始化准备，返回 (chunk_count, chunk_names)"""
        if self.douyin:
            template = self.load_prompt_template("plot_expander_douyin.txt")
        elif self.minimalist:
            template = self.load_prompt_template("plot_expander_minimal.txt")
        else:
            template = self.load_prompt_template("plot_expander.txt")
        self._gen_beat_sheet = _load_beat_sheet(project)
        self._voice_injection = ""
        confirmed_direction = ""
        outline_content = project.read_output("01_故事大纲/故事大纲.md") or ""
        if self.douyin and outline_content:
            self._voice_injection = format_voice_injection(extract_voice_labels(outline_content))
            self._constraint_card = build_hard_constraint_card(outline_content)
        direction_match = re.search(r'> ✅ 已选中版本[AB]。(差异摘要.*?)$', outline_content, re.MULTILINE)
        if direction_match:
            confirmed_direction = direction_match.group(1).strip()
        if not confirmed_direction:
            confirmed_direction = "（未设置）"
        template = template.replace("{confirmed_direction}", confirmed_direction)
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            outline = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""
        else:
            outline = input_content
        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        screen_aspect_name = SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")
        plan = ChunkStrategy.get_plan(style.story_type)
        if plan.bible_mode:
            self._bible_mode = True
            return 0, []
        pre_analyzed = ChunkStrategy.pre_analyze_split_points(outline, self.call_llm_stream)
        iterator = ChunkIter(plan, outline, pre_analyzed)
        if plan.chunk_count == 0:
            # 优先使用用户配置的集数
            if style.episode_count and style.episode_count.isdigit() and int(style.episode_count) > 0:
                chunk_count = int(style.episode_count)
                chunk_count = max(1, min(chunk_count, 200))
                iterator.set_auto_blocks(chunk_count, outline=outline)
            else:
                count_prompt = (
                    f"以下是一个故事大纲。请判断这个故事应该分为几集/几章。"
                    f"考虑故事的长度和复杂度。只输出一个整数，不要其他文字。\n\n"
                    f"{outline[:3000]}"
                )
                count_text = ""
                for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
                    count_text += token
                nums = re.findall(r'\d+', count_text)
                chunk_count = int(nums[0]) if nums else 3
                chunk_count = max(1, min(chunk_count, 200))
                iterator.set_auto_blocks(chunk_count, outline=outline)
        self._gen_template = template
        self._gen_style_context = style_context
        self._gen_writing_style_name = writing_style_name
        self._gen_screen_aspect_name = screen_aspect_name
        self._gen_story_type_name = story_type_name
        self._gen_plan = plan
        self._gen_iterator = iterator
        self._gen_outline = outline
        self._gen_feedback = feedback
        self._outline_infos = []
        chunk_count = len(iterator.blocks)
        chunk_names = [b["name"] for b in iterator.blocks]
        return chunk_count, chunk_names

    def generate_chunk(self, ctx, template, style_context, writing_style_name,
                       screen_aspect_name, story_type_name, style, plan, outline,
                       feedback="", chunk_name=""):
        if self.douyin:
            prompt = template.replace("{outline}", ctx.outline_section or outline)
            # 注入节拍表
            beat_sheet = _load_beat_sheet(project) if hasattr(self, '_project') else getattr(self, '_gen_beat_sheet', None)
            if not beat_sheet:
                beat_sheet = getattr(self, '_gen_beat_sheet', [])
            if beat_sheet:
                ep_match = re.search(r'第(\d+)集', ctx.name or '')
                if ep_match:
                    ep_num = int(ep_match.group(1))
                    beat = _get_beat_for_ep(beat_sheet, ep_num)
                    if beat:
                        prompt += _format_beat_injection(beat)
            if getattr(self, '_voice_injection', ''):
                prompt += self._voice_injection
            # 前序上下文：继承前文，保持衔接
            if ctx.previous_full_texts:
                prompt += "\n\n## 前序剧情\n\n"
                for ft in ctx.previous_full_texts:
                    prompt += ft[-3000:] + "\n\n"
            if ctx.summaries:
                prompt += "\n\n## 关键元素追踪（前序已生成内容中必须衔接的线索）\n" + "\n".join(ctx.summaries)

            if feedback:
                prompt += f"\n\n## 修改意见\n{feedback}"

            if getattr(self, '_constraint_card', ''):
                prompt += self._constraint_card

            # 格式约束放在最后——LLM对末尾注意力最高
            prompt += (
                f"\n\n## ⚠️ 输出格式强制要求——仔细看，照抄格式\n\n"
                f"开头: {ctx.name}\n"
                f"场景头: 时间  内外  地点  (例如: 夜 内 陈家客厅)\n"
                f"动作: △ 描述\n"
                f"对白: 角色名（情绪）：对白\n"
                f"换场: 空一行的新场景头\n"
                f"结尾: **（全文完）**\n\n"
                f"禁止: ##标记、###标记、用数字编号场景（不写场1）、"
                f"不用标题。500-700字，最多3场。\n\n"
                f"示例:\n"
                f"{ctx.name}\n\n"
                f"夜 内 客厅\n\n"
                f"△ 蛋糕上的蜡烛只剩一根亮着。\n"
                f"△ 陈国栋站在人群外。\n\n"
                f"陈国栋（掏手机）：谁？\n\n"
                f"△ 屏幕上躺着一条短信。\n\n"
                f"日 外 门口\n\n"
                f"△ 铁门上贴着半张黄纸条。\n\n"
                f"陈国栋（推门）：没锁。\n\n"
                f"**（全文完）**"
            )

            self._last_chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                self._last_chunk_output += token
                yield token
            self._outline_infos.append((ctx.name, ctx.outline_section))
            if plan.summarize and self._last_chunk_output.strip():
                self._last_chunk_summary = self._extract_summary(ctx.name, self._last_chunk_output)
            return

        prompt = template.replace("{style_config}", style_context)
        prompt = prompt.replace("{outline}", ctx.outline_section or outline)
        prompt = prompt.replace("{writing_style}", writing_style_name)
        prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
        duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
        prompt = prompt.replace("{duration_mode}", duration_label)
        # Use chunk-specific episode count, not global total
        chunk_ep_count = style.episode_count or "（由AI根据大纲合理分配）"
        chunk_name = ctx.name or ""
        ep_nums = re.findall(r'\d+', chunk_name)
        if len(ep_nums) >= 2:
            chunk_ep_count = str(int(ep_nums[-1]) - int(ep_nums[0]) + 1)
        elif len(ep_nums) == 1:
            chunk_ep_count = ep_nums[0]
        prompt = prompt.replace("{episode_count}", chunk_ep_count)
        prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
        prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
        prompt = prompt.replace("{story_type}", story_type_name)
        prompt = prompt.replace("{type_specific_rules}", _type_specific_rules(style.story_type))

        prev_outline_context = ""
        if self._outline_infos:
            prev_outline_context = "\n\n## 前序大纲回顾（你的剧情必须与此衔接）\n\n"
            for act_name, act_outline in self._outline_infos:
                prev_outline_context += f"### {act_name} 大纲\n{act_outline[-4000:]}\n\n"

        prev_plot_context = ""
        if ctx.previous_full_texts:
            prev_plot_context = "\n\n## 前序剧情回顾（你之前写的内容）\n\n"
            for i, ft in enumerate(ctx.previous_full_texts):
                name = self._outline_infos[i][0] if i < len(self._outline_infos) else f"前序"
                prev_plot_context += f"### {name} 剧情（已生成）\n{ft[-4000:]}\n\n"

        prompt += prev_outline_context
        prompt += prev_plot_context

        if ctx.summaries:
            prompt += "\n\n## 关键元素追踪\n" + "\n".join(ctx.summaries)

        prompt += f"\n\n当前正在生成：{chunk_name}"

        # Batch: replace ambiguous single-chunk instruction with explicit multi-episode instruction
        if plan.batch_size > 1:
            ep_nums = re.findall(r'\d+', ctx.name)
            if len(ep_nums) >= 2:
                s, e = int(ep_nums[0]), int(ep_nums[-1])
                all_eps = "、".join([f"第{i}集" for i in range(s, e + 1)])
                prompt += (
                    f"\n\n【批量生成指令——必须严格遵守，这是最终要求】"
                    f"\n本批次需要一次性生成以下 {e-s+1} 集完整剧情：{all_eps}。"
                    f"\n每集不少于 800 字，以「## 第X集 - 分集标题」作为独立标题。"
                    f"\n集与集之间用空行分隔。每集结尾必须有悬念钩子。"
                    f"\n重要：在输出「**（全文完）**」之前，请逐集检查是否已生成全部 {e-s+1} 集。"
                    f"\n禁止省略、合并、跳过任何一集。禁止把多集写成一段。"
                )
        else:
            prompt += f"\n\n请只写「{ctx.name}」的内容，开头务必以 Markdown 标题标明「## {ctx.name}」。全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**"

        if feedback and ctx.index == (plan.chunk_count or 1) - 1:
            prompt += f"\n\n## 修改意见\n{feedback}"

        if getattr(self, '_constraint_card', ''):
            prompt += self._constraint_card

        self._last_chunk_output = ""
        for token in self.call_llm_stream(prompt, "", temperature=0.8):
            self._last_chunk_output += token
            yield token

        self._outline_infos.append((ctx.name, ctx.outline_section))

        if plan.summarize and self._last_chunk_output.strip():
            self._last_chunk_summary = self._extract_summary(ctx.name, self._last_chunk_output)

    def _resolve_auto_chunks(self, iterator, template, outline, style_context,
                               writing_style_name, screen_aspect_name,
                               story_type_name, style, feedback):
        if style.episode_count and style.episode_count.isdigit() and int(style.episode_count) > 0:
            chunk_count = int(style.episode_count)
            chunk_count = max(1, min(chunk_count, 200))
        else:
            count_prompt = (
                f"以下是一个故事大纲。请判断这个故事应该分为几集/几章。"
                f"考虑故事的长度和复杂度。只输出一个整数，不要其他文字。\n\n"
                f"{outline[:3000]}"
            )
            count_text = ""
            for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
                count_text += token
            nums = re.findall(r'\d+', count_text)
            chunk_count = int(nums[0]) if nums else 3
            chunk_count = max(1, min(chunk_count, 200))
        iterator.set_auto_blocks(chunk_count, outline=outline)

        douyin_bible = load_bible(self._project_dir) or {}
        douyin_episode_buffer = []

        for ctx in iterator:
            if self.minimalist or self.douyin:
                prompt = template.replace("{outline}", ctx.outline_section or outline)
                if ctx.previous_full_texts:
                    bridge = "\n\n## 上文回顾\n\n"
                    for ft in ctx.previous_full_texts:
                        bridge += ft[-4000:] + "\n\n"
                    prompt += bridge
                if ctx.summaries:
                    prompt += "\n\n## 关键元素追踪（前序已生成内容中必须衔接的线索）\n" + "\n".join(ctx.summaries)
                bible_injection = format_bible_injection(douyin_bible)
                if bible_injection:
                    prompt += "\n\n" + bible_injection
                if iterator.plan.batch_size > 1:
                    ep_nums = re.findall(r'\d+', ctx.name)
                    if len(ep_nums) >= 2:
                        s, e = int(ep_nums[0]), int(ep_nums[-1])
                        all_eps = "、".join([f"第{i}集" for i in range(s, e + 1)])
                        prompt += (
                            f"\n\n【批量生成指令——必须严格遵守，这是最终要求】"
                            f"\n本批次需要一次性生成以下 {e-s+1} 集完整剧情：{all_eps}。"
                            f"\n每集不少于 800 字，以「## 第X集」作为独立标题。"
                            f"\n集与集之间用空行分隔。每集结尾必须有钩子悬念。"
                            f"\n重要：在输出「**（全文完）**」之前，请逐集检查是否已生成全部 {e-s+1} 集。"
                            f"\n禁止省略、合并、跳过任何一集。禁止把多集写成一段。"
                        )
                else:
                    prompt += f"\n\n请写「{ctx.name}」的剧情，以「{ctx.name}」开头（不加##标记）。采用行业短剧格式：场景头「时间 内外 地点」+△动作标记。每集至少800字，最多3场。写完加「**（全文完）**」"
                if feedback and ctx.index == iterator.plan.chunk_count - 1:
                    prompt += f"\n\n## 修改意见\n{feedback}"
                if getattr(self, '_constraint_card', ''):
                    prompt += self._constraint_card
                chunk_output = ""
                for token in self.call_llm_stream(prompt, "", temperature=0.8):
                    chunk_output += token
                    yield token
                if chunk_output.strip():
                    summary = self._extract_summary(ctx.name, chunk_output)
                    iterator.set_output(ctx.index, chunk_output, summary)
                    douyin_episode_buffer.append((ctx.name, chunk_output))
                    if len(douyin_episode_buffer) >= BIBLE_UPDATE_INTERVAL:
                        try:
                            douyin_bible = build_bible_update(self.llm, None, douyin_episode_buffer, douyin_bible)
                            save_bible(self._project_dir, douyin_bible)
                        except Exception:
                            pass
                        douyin_episode_buffer = []
                else:
                    iterator.set_output(ctx.index, chunk_output)
                continue

            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", ctx.outline_section or outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chunk_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)
            prompt = prompt.replace("{type_specific_rules}", _type_specific_rules(style.story_type))

            if ctx.previous_full_texts:
                bridge = "\n\n## 上文回顾\n\n"
                for ft in ctx.previous_full_texts:
                    bridge += ft[-4000:] + "\n\n"
                prompt += bridge
            if ctx.summaries:
                prompt += "\n\n## 关键元素追踪\n" + "\n".join(ctx.summaries)

            if iterator.plan.batch_size > 1:
                ep_nums = re.findall(r'\d+', ctx.name)
                if len(ep_nums) >= 2:
                    s, e = int(ep_nums[0]), int(ep_nums[-1])
                    all_eps = "、".join([f"第{i}集" for i in range(s, e + 1)])
                    prompt += (
                        f"\n\n【批量生成指令——必须严格遵守，这是最终要求】"
                        f"\n本批次需要一次性生成以下 {e-s+1} 集完整剧情：{all_eps}。"
                        f"\n每集不少于 800 字，以「## 第X集 - 分集标题」作为独立标题。"
                        f"\n集与集之间用空行分隔。每集结尾必须有钩子悬念。"
                        f"\n重要：在输出「**（全文完）**」之前，请逐集检查是否已生成全部 {e-s+1} 集。"
                        f"\n禁止省略、合并、跳过任何一集。禁止把多集写成一段。"
                    )
            else:
                prompt += f"\n\n请只写「{ctx.name}」的内容，这是系列的第{ctx.index+1}部分，开头务必以 Markdown 标题标明「## {ctx.name}」。全部内容输出完毕后，请在末尾加上结束标记：**（全文完）**"

            if feedback and ctx.index == iterator.plan.chunk_count - 1:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            if chunk_output.strip():
                summary = self._extract_summary(ctx.name, chunk_output)
                iterator.set_output(ctx.index, chunk_output, summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        if douyin_episode_buffer:
            try:
                douyin_bible = build_bible_update(self.llm, None, douyin_episode_buffer, douyin_bible)
                save_bible(self._project_dir, douyin_bible)
            except Exception:
                pass
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

    def _generate_novel_chapters(self, project, template, outline, style_context,
                                   writing_style_name, screen_aspect_name,
                                   story_type_name, style, feedback, plan):
        from core.novel_bible import BibleManager, BibleFormatter
        from core.bible_updater import BibleUpdater

        count_prompt = (
            f"以下是一个故事大纲。请判断这个故事应该分为多少章。"
            f"考虑故事的长度和复杂度。只输出一个整数，不要其他文字。\n\n"
            f"{outline[:3000]}"
        )
        count_text = ""
        for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
            count_text += token
        nums = re.findall(r'\d+', count_text)
        chapter_count = int(nums[0]) if nums else 10
        chapter_count = max(1, min(chapter_count, 1000))

        bible = BibleManager.load(project.project_dir)

        for chapter_num in range(1, chapter_count + 1):
            recent_summaries = []
            for i in range(max(1, chapter_num - plan.context_window), chapter_num):
                if i in bible.chapter_summaries:
                    recent_summaries.append(f"第{i}章: {bible.chapter_summaries[i]}")

            prompt = template.replace("{style_config}", style_context)
            prompt = prompt.replace("{outline}", outline)
            prompt = prompt.replace("{writing_style}", writing_style_name)
            prompt = prompt.replace("{screen_aspect}", screen_aspect_name)
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            prompt = prompt.replace("{episode_count}", style.episode_count or str(chapter_count))
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)
            prompt = prompt.replace("{type_specific_rules}", _type_specific_rules(style.story_type))

            active_chars = BibleFormatter.format_active_characters(bible)
            if active_chars:
                prompt += f"\n\n## 当前角色状态\n{active_chars}"
            hook_panel = BibleFormatter.format_hook_status_panel(bible)
            if hook_panel:
                prompt += f"\n\n{hook_panel}"
            timeline = BibleFormatter.format_timeline(bible)
            if timeline:
                prompt += f"\n\n## 重要事件回顾\n{timeline}"
            rel_graph = BibleFormatter.format_relationship_graph(bible)
            if rel_graph and bible.characters:
                prompt += f"\n\n{rel_graph}"
            if recent_summaries:
                prompt += f"\n\n## 近期章节回顾\n" + "\n".join(recent_summaries)

            prompt += f"\n\n请写第{chapter_num}章的内容，开头务必以 Markdown 标题标明「## 第{chapter_num}章」。这是小说的第{chapter_num}章，共{chapter_count}章。写完后在末尾加上结束标记：**（全文完）**"

            if feedback:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chapter_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chapter_output += token
                yield token

            if chapter_output.strip():
                chapter_file = f"02_完整剧情/第{chapter_num:03d}章.md"
                project.write_output(chapter_file, chapter_output)
                try:
                    bible = BibleUpdater.update(bible, chapter_num, chapter_output, self.call_llm_stream)
                    BibleManager.save(bible, project.project_dir)
                except Exception:
                    pass

    def _extract_summary(self, chunk_name: str, content: str) -> str:
        summary_prompt = SummaryExtractor.build_summary_prompt(chunk_name, content)
        summary_raw = ""
        for token in self.call_llm_stream(summary_prompt, "", temperature=0.3):
            summary_raw += token
        return SummaryExtractor.parse_summary(summary_raw)

    def _extract_promise_list(self, outline_content: str) -> str:
        if not outline_content:
            return "（无大纲内容）"
        prompt = (
            "以下是一个故事大纲。请分析并输出该故事必须包含的角色、关键事件和核心冲突。\n"
            "格式如下，不要额外内容：\n"
            "```\n"
            "【本故事承诺】\n"
            "- 必须出场的角色：XXX、XXX\n"
            "- 必须发生的关键事件：XXX、XXX\n"
            "- 必须解决的核心冲突：XXX\n"
            "```\n\n"
            f"{outline_content[:4000]}"
        )
        result = ""
        for token in self.call_llm_stream(prompt, "", temperature=0.3):
            result += token
        match = re.search(r'【本故事承诺】.*', result, re.DOTALL)
        return match.group(0) if match else "（未能提取承诺清单）"
