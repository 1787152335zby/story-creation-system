import re
import json
from pathlib import Path
from core.agent_base import AgentBase
from core.project_manager import ProjectManager
from core.style_config import StyleConfig, WRITING_STYLES, SCREEN_ASPECTS, SCRIPT_STYLES, STORY_TYPES
from core.chunk_strategy import ChunkStrategy, ChunkIter
from core.summary_extractor import SummaryExtractor
from core.voice_labels import extract_voice_labels, format_voice_injection, build_hard_constraint_card
from core.story_bible import format_bible_injection, build_bible_update, BIBLE_UPDATE_INTERVAL, load_bible, save_bible


def _load_beat_sheet(project) -> list:
    try:
        raw = project.read_output("01b_节拍表/beat_sheet.json") or ""
        if raw.strip():
            return json.loads(raw)
    except:
        pass
    return []


def _get_beat_for_ep(beat_sheet: list, ep_num: int) -> dict:
    for b in beat_sheet:
        if b.get("episode") == ep_num:
            return b
    return {}


def _format_beat_injection(beat: dict) -> str:
    if not beat or not beat.get("task"):
        return ""
    return (
        f"\n\n## 本集节拍约束\n"
        f"- 本集事件链：{beat.get('task', '')}\n"
        f"- 只能释放一块信息：{beat.get('info_piece', '')}\n"
        f"- 结尾必须是这个画面（观众知道角色不知道的事）：{beat.get('hook', '')}\n"
        f"- 角色关系变化：{beat.get('relationship_shift', '')}"
    )


def _calc_total_minutes(style: StyleConfig) -> str:
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
            "【短剧剧本规则】\n"
            "- 每场 30-60 秒可拍摄内容，动作描写 1-2 句即可\n"
            "- 镜头语言必须明确（特写/中景/全景），供分镜阶段直接使用\n"
            "- 对白不超过 3 句/场，核心靠动作和表情传递信息\n"
            "- 每集结尾的动作指令必须能直接转化为画面钩子\n"
        ),
        "2": (
            "【电影剧本规则】\n"
            "- 每场写清场景氛围和空间关系，供美术和摄影参考\n"
            "- 第一幕结尾 + 中点 + 第三幕高潮 = 三个必须细致描写的关键场\n"
            "- 转场方式必须标注（切/淡入/叠化），长镜头连续场景写明一镜调度\n"
            "- 人物动作描写到位即可，留出导演发挥空间\n"
        ),
        "3": (
            "【电视剧剧本规则】\n"
            "- A/B 线交替：每集至少切换一次线索，切换点标注「切至」\n"
            "- 每集 5-8 场，单场不超过拍摄页 3 页\n"
            "- 对白信息密度要高——每句推动剧情或揭示人物\n"
            "- 每集最后一场写清悬念画面，标注镜头类型（建议特写收尾）\n"
        ),
        "4": (
            "【小说剧本规则】\n"
            "- 对话融入叙述流，不标出场角色名单\n"
            "- 每章允许 1-2 段心理描写（150 字以内），但主要靠行动和对话推进\n"
            '- 章节结尾留「未完」感——不是悬念，是好奇\n'
        ),
        "5": (
            "【舞台剧剧本规则】\n"
            "- 每场标注：灯光（亮度/色温/变化时机）、音效、道具位置\n"
            "- 走位必须写明（上/下/左/右/前/后/转），坐标系以观众视角为准\n"
            '- 独白前标注「灯光收拢」，独白后标注「灯光复原」\n'
            "- 幕间休息点标注\n"
        ),
        "6": (
            "【广播剧剧本规则】\n"
            '- 环境音必须标注具体声源（不是「街道声」，是「汽车喇叭×2 + 远处狗叫 + 风」）\n'
            "- 每个角色的对白前标注距离感：近（耳边）/中（同空间）/远（隔障碍物）\n"
            '- 静默也是一种设计——标注「停顿 X 秒，只留环境音」\n'
            "- 关键动作通过音效传达：脚步、开关门、物品碰撞\n"
        ),
    }
    return RULES.get(story_type_id, "")


class ScreenplayWriter(AgentBase):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self._plot_infos = []
        self._last_chunk_output = ""
        self._last_chunk_summary = ""
        self.minimalist = False
        self.douyin = False

    def run(self, project: ProjectManager, style: StyleConfig, input_content: str) -> str:
        return "".join(self.run_stream(project, style, input_content))

    def _load_plot_meta(self, project: ProjectManager, input_content: str) -> dict:
        """从剧情文件中提取版本方向、承诺清单、字数信息"""
        meta = {
            "confirmed_direction": "（未设置）",
            "promise_list": "（未设置）",
            "plot_chars": "0",
            "max_script_chars": "0",
        }
        try:
            plot_content = project.read_output("02_完整剧情/完整剧情.md") or input_content
            total_chars = len(plot_content.replace(" ", "").replace("\n", ""))
            meta["plot_chars"] = str(total_chars)
            meta["max_script_chars"] = str(total_chars * 3)
            # 提取方向信息
            direction_match = re.search(r'> ✅ 已选中版本[AB]。(差异摘要.*?)$', plot_content, re.MULTILINE)
            if direction_match:
                meta["confirmed_direction"] = direction_match.group(1).strip()
            # 提取承诺清单
            promise_match = re.search(r'【本故事承诺】.*?(?=\n\n|\Z)', plot_content, re.DOTALL)
            if promise_match:
                meta["promise_list"] = promise_match.group(0).strip()
        except:
            pass
        return meta

    def generate_chunk(self, ctx, template, style_context, writing_style_name, script_style_name, script_format_name, story_type_name, style, plan, input_content, feedback="", chunk_name=""):
        self._last_chunk_output = ""

        prompt = template.replace("{style_config}", style_context)
        prompt = template.replace("{plot_structure}", ctx.outline_section or input_content)
        prompt = prompt.replace("{writing_style}", writing_style_name)
        prompt = prompt.replace("{script_style}", script_style_name)
        prompt = prompt.replace("{script_format}", script_format_name)
        prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
        duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
        prompt = prompt.replace("{duration_mode}", duration_label)
        prompt = prompt.replace("{episode_count}", style.episode_count or "（由AI根据大纲合理分配）")
        prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
        prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
        prompt = prompt.replace("{story_type}", story_type_name)
        prompt = prompt.replace("{type_specific_rules}", _type_specific_rules(style.story_type))

        prev_plot_context = ""
        if self._plot_infos:
            prev_plot_context = "\n\n## 前序剧情回顾（必须与此衔接，保持人物/事件一致）\n\n"
            for act_name, act_plot in self._plot_infos:
                prev_plot_context += f"### {act_name} 剧情\n{act_plot[-2000:]}\n\n"

        prev_screenplay_context = ""
        if ctx.previous_full_texts:
            prev_screenplay_context = "\n\n## 前序剧本回顾（你之前写的内容，保持衔接，但格式用新标准——见末尾）\n\n"
            for i, ft in enumerate(ctx.previous_full_texts):
                name = self._plot_infos[i][0] if i < len(self._plot_infos) else "前序"
                # 清洗旧格式标记，只保留内容语义
                cleaned = re.sub(r'^#{1,3}\s+.*$', '', ft, flags=re.MULTILINE)
                cleaned = re.sub(r'^出场角色：.*$', '', cleaned, flags=re.MULTILINE)
                cleaned = re.sub(r'^---\s*$', '', cleaned, flags=re.MULTILINE)
                cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
                prev_screenplay_context += f"### {name}\n{cleaned[-2000:]}\n\n"

        prompt += prev_plot_context
        prompt += prev_screenplay_context

        prompt += f"\n\n当前正在生成：{chunk_name}"

        if plan.batch_size > 1:
            ep_nums = re.findall(r'\d+', ctx.name)
            if len(ep_nums) >= 2:
                s, e = int(ep_nums[0]), int(ep_nums[-1])
                all_eps = "、".join([f"第{i}集" for i in range(s, e + 1)])
                prompt += (
                    f"\n\n【批量生成指令——必须严格遵守，这是最终要求】"
                    f"\n本批次需要一次性生成以下 {e-s+1} 集完整剧本：{all_eps}。"
                    f"\n每集不少于 1000 字，含画面描述、对白、音效。"
                    f"\n每集以「第X集」作为独立标题（不加##标记）。集与集之间用空行分隔。"
                    f"\n每集结尾必须有钩子悬念。"
                    f"\n重要：在输出「**（全文完）**」之前，请逐集检查是否已生成全部 {e-s+1} 集。"
                    f"\n禁止省略、合并、跳过任何一集。禁止把多集写成一段。"
                )

        if feedback:
            prompt += f"\n\n## 修改意见\n{feedback}"

        if getattr(self, '_constraint_card', ''):
            prompt += self._constraint_card

        # 格式约束放在最后——LLM对末尾注意力最高
        voice_rules = ""
        voice_labels = getattr(self, '_voice_labels', [])
        if voice_labels:
            voice_rules = "\n## ⚠️ 每人说话方式——逐人硬约束（不遵守则全批作废）\n\n"
            for vl in voice_labels:
                voice_rules += f"- {vl['name']}：{vl['tag']}\n"
            voice_rules += "\n写完每句对白自查：删掉角色名还能认出是谁说的吗？认不出就重写。\n"
        else:
            voice_rules = (
                "\n## ⚠️ 对白声音分化\n\n"
                "- 两个角色不能说出同样长度、同样句式、同样情绪的对白\n"
                "- 写完每句对白自查：删掉角色名还能认出是谁说的吗？\n"
            )
        prompt += (
            f"\n\n## ⚠️ 输出格式强制要求——严格照此格式输出\n\n"
            f"开头: {ctx.name}\n"
            f"场头: 场{{集号}}-{{序号}}  时间  内外  地点\n"
            f"  例如: 场1-1  夜  内  客厅\n"
            f"动作: △ 描述（每条1-2句）\n"
            f"对白: 角色名（情绪/动作）：对白（情绪跟名字同行）\n"
            f"内心独白: 角色名os：内容\n"
            f"画外音: 角色名vo：内容\n"
            f"换场: 空一行后写新场头\n"
            f"结尾: **（全文完）**\n\n"
            f"禁止: ##标记、###标记、出场角色行、宽对白行、对白超过15字\n"
            f"⚠️ 每集只写1-2场（抖音短剧2分钟一集，场多了观众记不住场景）。1场一镜到底最好，2场只在必须换地点时用。3场以上视为废稿。\n"
            f"⚠️ 每集最后一句必须是钩子——观众拇指划过三秒就走。钩子类型：\n"
            f"  - 没说完的话：角色说到一半就停下/被打断\n"
            f"  - 突然出现的威胁：一个不该出现的车/电话/人/声音\n"
            f"  - 刚被推翻的认知：以为是真的结果是假的/以为是假的结果是真的\n"
            f"  - 一个不该亮却亮了的灯/一个不该响却响了的声音\n"
            f"  尾句不能是：描述性收束（'他转身走了'）、情绪总结（'她哭了'）、自然结束（'天亮了'）。\n"
            f"{voice_rules}\n"
            f"示例:\n"
            f"第1集\n\n"
            f"场1-1  夜  内  客厅\n\n"
            f"△ 蜡烛只剩一根亮着。\n\n"
            f"陈国栋（掏手机）：谁？\n\n"
            f"△ 屏幕上躺着一条短信。\n\n"
            f"场1-2  日  外  门口\n\n"
            f"△ 铁门上贴着黄纸条。\n\n"
            f"陈国栋vo：三十年了。\n\n"
            f"**（全文完）**"
        )

        for token in self.call_llm_stream(prompt, "", temperature=0.8):
            self._last_chunk_output += token
            yield token

        if plan.summarize and self._last_chunk_output.strip():
            self._last_chunk_summary = self._extract_summary(ctx.name, self._last_chunk_output)

        self._plot_infos.append((ctx.name, input_content))

    @staticmethod
    def _filter_format_sections(template: str, is_market: bool) -> str:
        import re
        if is_market:
            template = re.sub(r'\{if_system\}.*?\{\/if_system\}', '', template, flags=re.DOTALL)
            template = template.replace('{if_market}', '').replace('{/if_market}', '')
        else:
            template = re.sub(r'\{if_market\}.*?\{\/if_market\}', '', template, flags=re.DOTALL)
            template = template.replace('{if_system}', '').replace('{/if_system}', '')
        return template.strip()

    def run_stream(self, project: ProjectManager, style: StyleConfig, input_content: str):
        if self.douyin:
            template = self.load_prompt_template("screenplay_writer_douyin.txt")
        else:
            template = self.load_prompt_template("screenplay_writer.txt")

        self._gen_beat_sheet = _load_beat_sheet(project)
        self._voice_injection = ""
        self._voice_labels = []
        if self.douyin:
            outline_text = project.read_output("01_故事大纲/故事大纲.md") or ""
            if outline_text:
                self._voice_injection = format_voice_injection(extract_voice_labels(outline_text))
                self._constraint_card = build_hard_constraint_card(outline_text)
                self._voice_labels = extract_voice_labels(outline_text)
        self._project_dir = project.project_dir

        meta = self._load_plot_meta(project, input_content)
        if not self.douyin:
            template = template.replace("{confirmed_direction}", meta["confirmed_direction"])
            template = template.replace("{promise_list}", meta["promise_list"])

        plot_structure = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            plot_structure = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""

        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        script_style_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "视觉化写作")
        script_format_name = {"1": "系统格式", "2": "市场格式"}.get(style.script_format, "系统格式")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")

        # 过滤掉非选中的格式说明块
        is_market = style.script_format == "2"
        template = self._filter_format_sections(template, is_market)
        template = template.replace("{script_format}", script_format_name)

        plan = ChunkStrategy.get_plan(style.story_type)
        iterator = ChunkIter(plan, plot_structure)

        if plan.chunk_count == 0:
            yield from self._resolve_auto_chunks(iterator, template, plot_structure, style_context,
                                                   writing_style_name, script_style_name,
                                                   story_type_name, style, feedback)
            return

        self._plot_infos = []

        for ctx in iterator:
            yield from self.generate_chunk(ctx, template, style_context, writing_style_name,
                                           script_style_name, script_format_name, story_type_name,
                                           style, plan, plot_structure, feedback)

            chunk_output = self._last_chunk_output

            if chunk_output.strip():
                project.write_output(f"03_完整剧本/完整剧本_{ctx.name}.md", chunk_output)
                all_chunks = []
                for b in iterator.blocks:
                    if b.get("_output", "").strip():
                        all_chunks.append(b["_output"])
                if all_chunks:
                    project.write_output("03_完整剧本/完整剧本.md", "\n\n---\n\n".join(all_chunks))

            if plan.summarize and chunk_output.strip():
                iterator.set_output(ctx.index, chunk_output, self._last_chunk_summary)
            else:
                iterator.set_output(ctx.index, chunk_output)
        self._chunks = [{"name": b["name"], "output": b.get("_output", "")} for b in iterator.blocks]

    def prepare_generation(self, project, style, input_content):
        if self.douyin:
            template = self.load_prompt_template("screenplay_writer_douyin.txt")
        else:
            template = self.load_prompt_template("screenplay_writer.txt")
        self._gen_beat_sheet = _load_beat_sheet(project)
        self._voice_injection = ""
        self._voice_labels = []
        if self.douyin:
            outline_text = project.read_output("01_故事大纲/故事大纲.md") or ""
            if outline_text:
                self._voice_injection = format_voice_injection(extract_voice_labels(outline_text))
                self._constraint_card = build_hard_constraint_card(outline_text)
                self._voice_labels = extract_voice_labels(outline_text)
        meta = self._load_plot_meta(project, input_content)
        if not self.douyin:
            template = template.replace("{confirmed_direction}", meta["confirmed_direction"])
            template = template.replace("{promise_list}", meta["promise_list"])
            template = template.replace("{plot_chars}", meta["plot_chars"])
            template = template.replace("{max_script_chars}", meta["max_script_chars"])
        plot_structure = input_content
        feedback = ""
        if "## 修改意见" in input_content:
            parts = input_content.split("## 修改意见")
            plot_structure = parts[0]
            feedback = parts[1] if len(parts) > 1 else ""
        style_context = self.get_style_context(style)
        writing_style_name = WRITING_STYLES.get(style.writing_style, {}).get("name", "自动适配")
        script_style_name = SCRIPT_STYLES.get(style.script_style, {}).get("name", "视觉化写作")
        script_format_name = {"1": "系统格式", "2": "市场格式"}.get(style.script_format, "系统格式")
        story_type_name = STORY_TYPES.get(style.story_type, {}).get("name", "未知")

        is_market = style.script_format == "2"
        template = self._filter_format_sections(template, is_market)
        template = template.replace("{script_format}", script_format_name)

        plan = ChunkStrategy.get_plan(style.story_type)
        iterator = ChunkIter(plan, plot_structure)
        if plan.chunk_count == 0:
            # 优先使用用户配置的集数
            if style.episode_count and style.episode_count.isdigit() and int(style.episode_count) > 0:
                chunk_count = int(style.episode_count)
                chunk_count = max(1, min(chunk_count, 200))
                iterator.set_auto_blocks(chunk_count)
            else:
                count_prompt = (f"以下是一段剧情描述。请判断应该分为几集/几章来写剧本。"
                                f"只输出一个整数。\n\n{plot_structure[:3000]}")
                count_text = ""
                for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
                    count_text += token
                nums = re.findall(r'\d+', count_text)
                chunk_count = int(nums[0]) if nums else 3
                chunk_count = max(1, min(chunk_count, 200))
                iterator.set_auto_blocks(chunk_count)
        self._gen_template = template
        self._gen_style_context = style_context
        self._gen_writing_style_name = writing_style_name
        self._gen_script_style_name = script_style_name
        self._gen_script_format_name = script_format_name
        self._gen_story_type_name = story_type_name
        self._gen_plan = plan
        self._gen_iterator = iterator
        self._gen_input_content = plot_structure
        self._gen_feedback = feedback
        self._plot_infos = []
        chunk_count = len(iterator.blocks)
        chunk_names = [b["name"] for b in iterator.blocks]
        return chunk_count, chunk_names

    def _resolve_auto_chunks(self, iterator, template, input_content, style_context,
                               writing_style_name, script_style_name,
                               story_type_name, style, feedback):
        script_format_name = {"1": "系统格式", "2": "市场格式"}.get(style.script_format, "系统格式")
        if style.episode_count and style.episode_count.isdigit() and int(style.episode_count) > 0:
            chunk_count = int(style.episode_count)
            chunk_count = max(1, min(chunk_count, 200))
        else:
            count_prompt = (
                f"以下是一段剧情描述。请判断应该分为几集/几章来写剧本。"
                f"只输出一个整数。\n\n{input_content[:3000]}"
            )
            count_text = ""
            for token in self.call_llm_stream(count_prompt, "", temperature=0.3):
                count_text += token
            nums = re.findall(r'\d+', count_text)
            chunk_count = int(nums[0]) if nums else 3
            chunk_count = max(1, min(chunk_count, 200))
        iterator.set_auto_blocks(chunk_count)

        self._plot_infos = []

        douyin_bible = load_bible(self._project_dir) or {}
        douyin_episode_buffer = []

        for ctx in iterator:
            if self.douyin:
                prompt = template.replace("{plot_structure}", input_content)
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
                if self._plot_infos:
                    prompt += "\n\n## 前序剧情\n\n"
                    for act_name, act_plot in self._plot_infos:
                        prompt += f"{act_plot[-1200:]}\n\n"
                if ctx.previous_full_texts:
                    prompt += "\n\n## 前序剧本\n\n"
                    for ft in ctx.previous_full_texts:
                        prompt += ft[-4000:] + "\n\n"
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
                            f"\n本批次需要一次性生成以下 {e-s+1} 集完整剧本：{all_eps}。"
                            f"\n每集不少于 1000 字，含画面描述、对白、音效。"
                            f"\n每集以「第X集」作为独立标题（不加##标记）。集与集之间用空行分隔。"
                            f"\n每集结尾必须有钩子悬念。"
                            f"\n重要：在输出「**（全文完）**」之前，请逐集检查是否已生成全部 {e-s+1} 集。"
                            f"\n禁止省略、合并、跳过任何一集。禁止把多集写成一段。"
                        )
                else:
                    prompt += f"\n\n请写「{ctx.name}」的剧本，以「{ctx.name}」开头（不加##标记）。用行业短剧格式：「场集号-场序 时间 内外 地点」+△动作标记+对白同行写。每集只写1-2场——抖音短剧2分钟一集，1场一镜到底最好，2场只在必须换地点时用。3场以上直接不合格。每集最后一句话必须是钩子（没说完的话、突然的威胁、反转认知、不该亮却亮了的灯），禁止描述性收束。写完加「**（全文完）**」"
                vl = getattr(self, '_voice_labels', [])
                if vl:
                    prompt += "\n\n## ⚠️ 每人说话方式——逐人硬约束\n"
                    for v in vl:
                        prompt += f"- {v['name']}：{v['tag']}\n"
                    prompt += "写完每句对白自查：删掉角色名还能认出是谁说的吗？\n"
                if feedback:
                    prompt += f"\n\n## 修改意见\n{feedback}"
                if getattr(self, '_constraint_card', ''):
                    prompt += self._constraint_card
                chunk_output = ""
                for token in self.call_llm_stream(prompt, "", temperature=0.8):
                    chunk_output += token
                    yield token
                self._plot_infos.append((ctx.name, input_content))
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
            prompt = template.replace("{plot_structure}", input_content)
            prompt = template.replace("{writing_style}", writing_style_name)
            prompt = template.replace("{script_style}", script_style_name)
            prompt = prompt.replace("{script_format}", script_format_name)
            prompt = prompt.replace("{screen_aspect}", SCREEN_ASPECTS.get(style.screen_aspect, {}).get("name", "自适应"))
            duration_label = "自动（由Agent推荐）" if style.duration_mode == "1" else "自定义"
            prompt = prompt.replace("{duration_mode}", duration_label)
            chunk_ep_count = style.episode_count or str(chunk_count)
            ep_nums = re.findall(r'\d+', ctx.name)
            if len(ep_nums) >= 2:
                chunk_ep_count = str(int(ep_nums[-1]) - int(ep_nums[0]) + 1)
            elif len(ep_nums) == 1:
                chunk_ep_count = ep_nums[0]
            prompt = prompt.replace("{episode_count}", chunk_ep_count)
            prompt = prompt.replace("{episode_duration}", style.episode_duration or "（由AI根据故事类型推荐）")
            prompt = prompt.replace("{episode_total_minutes}", _calc_total_minutes(style))
            prompt = prompt.replace("{story_type}", story_type_name)
            prompt = prompt.replace("{type_specific_rules}", _type_specific_rules(style.story_type))

            prev_plot_context = ""
            if self._plot_infos:
                prev_plot_context = "\n\n## 前序剧情回顾（必须与此衔接，保持人物/事件一致）\n\n"
                for act_name, act_plot in self._plot_infos:
                    prev_plot_context += f"### {act_name} 剧情\n{act_plot[-2000:]}\n\n"

            prev_screenplay_context = ""
            if ctx.previous_full_texts:
                prev_screenplay_context = "\n\n## 前序剧本回顾（你之前写的内容，保持格式和衔接一致性）\n\n"
                for i, ft in enumerate(ctx.previous_full_texts):
                    name = self._plot_infos[i][0] if i < len(self._plot_infos) else "前序"
                    prev_screenplay_context += f"### {name} 剧本（已生成）\n{ft[-4000:]}\n\n"

            prompt += prev_plot_context
            prompt += prev_screenplay_context

            if iterator.plan.batch_size > 1:
                ep_nums = re.findall(r'\d+', ctx.name)
                if len(ep_nums) >= 2:
                    s, e = int(ep_nums[0]), int(ep_nums[-1])
                    all_eps = "、".join([f"第{i}集" for i in range(s, e + 1)])
                    prompt += (
                        f"\n\n【批量生成指令——必须严格遵守，这是最终要求】"
                        f"\n本批次需要一次性生成以下 {e-s+1} 集完整剧本：{all_eps}。"
                        f"\n每集不少于 1000 字，含画面描述、对白、音效。"
                        f"\n每集以「第X集」作为独立标题（不加##标记）。集与集之间用空行分隔。"
                        f"\n每集结尾必须有钩子悬念。"
                        f"\n重要：在输出「**（全文完）**」之前，请逐集检查是否已生成全部 {e-s+1} 集。"
                        f"\n禁止省略、合并、跳过任何一集。禁止把多集写成一段。"
                    )
            else:
                prompt += f"\n\n请只写「{ctx.name}」的剧本，以「{ctx.name}」开头（不加##标记）。用行业短剧格式：「场集号-场序 时间 内外 地点」+△动作标记+对白同行写。每集只写1-2场——抖音短剧2分钟一集，1场一镜到底最好，3场以上直接不合格。每集最后一句话必须是钩子（没说完的话、突然的威胁、反转认知、不该亮却亮了的灯），禁止描述性收束。写完加「**（全文完）**」"

            if feedback:
                prompt += f"\n\n## 修改意见\n{feedback}"

            chunk_output = ""
            for token in self.call_llm_stream(prompt, "", temperature=0.8):
                chunk_output += token
                yield token

            self._plot_infos.append((ctx.name, input_content))

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

    def _extract_summary(self, chunk_name: str, content: str) -> str:
        summary_prompt = SummaryExtractor.build_summary_prompt(chunk_name, content)
        summary_raw = ""
        for token in self.call_llm_stream(summary_prompt, "", temperature=0.3):
            summary_raw += token
        return SummaryExtractor.parse_summary(summary_raw)
