import asyncio
import concurrent.futures
import json
import logging
import re
from pathlib import Path

from core.project_manager import ProjectManager
from core.style_config import StyleConfig, STORY_TYPES
from core.workflow_loader import WorkflowLoader
from agents.orchestrator import _split_sort_key
from core.content_validator import validate_content
from core.continuity import extract_continuity, save_continuity, load_last_continuity, generate_continuity_injection
from core.qc_gates import run_qc_check
from core.quality_checker import run_ai_quality_check, extract_promise_list, qc_result_to_warnings
from core.story_bible import load_bible, save_bible, format_bible_injection, should_update_bible, build_bible_update, BIBLE_UPDATE_INTERVAL
from core.agent_factory import create_agent
from core.auto_duration import get_type_default, analyze_duration
from core.visual_bible import VisualBibleExtractor

from .ws_manager import ConnectionManager

logger = logging.getLogger(__name__)


def _normalize_chunk_heading(chunk_output: str, display_name: str) -> str:
    """确保分镜/剧本的每集输出以 # 第N集 开头，去除前导散文内容。
    不截断区间标题（如 第1集-第16集），保留原样。"""
    import re
    text = chunk_output.strip()
    # 找第一个单集标题（第N集，后面不能是 -第M集）
    episode_match = re.search(r'^(#{1,4}\s*第\d+[集章部篇])(?!\s*[-–—]\s*第\d+)', text, re.MULTILINE)
    if episode_match:
        return text[episode_match.start():]
    # 如果是区间标题（第X集-第Y集），也接受
    range_match = re.search(r'^(#{1,4}\s*第\d+[集章部篇]\s*[-–—]\s*第\d+[集章部篇])', text, re.MULTILINE)
    if range_match:
        return text[range_match.start():]
    # 找不到集标题，去除前导散文（直到第一个有效内容标记）
    for token in ["###", "##", "---", "镜头", "【全片完】"]:
        idx = text.find(token)
        if idx >= 0:
            text = text[idx:]
            break
    if not text.startswith("#"):
        text = f"# {display_name}\n\n{text}"
    return text


def _build_creative_anchor(project: ProjectManager) -> str:
    """从大纲中提取世界观/类型/基调，作为每个 batch 的创作锚点。
    防止 LLM 在长剧集中忘记原始的设定和风格。"""
    outline = project.read_output("01_故事大纲/故事大纲.md") or ""
    if not outline:
        return ""

    # 取第1集标记之前的所有内容（世界观+人物+基调）
    prelude = re.split(r'\n\s*\*{1,3}\s*\*{0,2}第\d+集', outline, maxsplit=1)[0]

    # 提取关键段落：故事类型、核心主题、故事梗概
    lines: list[str] = []
    for block in prelude.split("\n\n"):
        stripped = block.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for keyword in ["故事类型", "核心主题", "故事梗概", "参考作品", "角色", "人物", "重要道具", "**名称**", "*   **名称**"]:
            if keyword in stripped:
                lines.append(stripped)
                break

    if not lines:
        # fallback: 取前 1500 字
        lines = [prelude[:1500]]

    anchor = "\n\n".join(lines)
    return (
        "\n\n【创作锚点——本剧核心设定不可遗忘】\n"
        f"{anchor}\n\n"
        "以上是贯穿全剧的世界观和风格基调。你现在编写的每一集都必须忠实于这个设定。\n"
        "严禁偏离原始类型和氛围。如果前文已偏离，请在本 batch 中逐步拉回正轨。"
    )


def _validate_chunk_quality(chunk_output: str, episode_count: int, phase: str = "") -> dict:
    """自动审核模式下的出厂质检。
    返回 {"pass": True} 或 {"pass": False, "reasons": [...]}"""
    issues = []
    is_script = "剧本" in phase or "03_" in phase

    # 1. 字数校验：剧情≥800字（给剧本生成器足够信息），剧本≥400字
    wc = len(chunk_output)
    min_words = 400 if is_script else 800
    if wc < min_words:
        issues.append(f"字数不足：{wc}字（要求≥{min_words}字）")

    # 2. 场数校验：只对剧本检查（剧情不需要分场标注）
    if is_script:
        scene_count = len(re.findall(r'场\d+-\d+', chunk_output))
        if scene_count == 0:
            scene_count = len(re.findall(r'[夜日晨昏]\s+[内外]\s+\S+', chunk_output))
        if scene_count < 1:
            issues.append(f"场数不足：{scene_count}场（要求≥1场）")
        elif scene_count > 2:
            issues.append(f"场数过多：{scene_count}场（抖音短剧每集1-2场，≤2场）")

    # 3. 重复句式校验：同一句连续出现或整集中非连续出现≥3次视为注水
    lines_in = [l.strip() for l in chunk_output.split('\n') if l.strip()]
    for i in range(len(lines_in) - 2):
        if len(lines_in[i]) > 5 and lines_in[i] == lines_in[i+1] == lines_in[i+2]:
            if not lines_in[i].startswith('#'):
                issues.append(f"重复句式：\"{lines_in[i][:40]}\" 连续出现3次")
                break
    if not issues:
        # 非连续重复检测：相同句尾（最后 15 字符）出现 3 次以上 = LLM 在兜圈
        text_lines = [l for l in lines_in if len(l) >= 15]
        if len(text_lines) >= 10:
            from collections import Counter
            endings = Counter()
            for l in text_lines:
                endings[l[-15:]] += 1
            for ending, cnt in endings.items():
                if cnt >= 3:
                    issues.append(f"结构重复：\"...{ending[:30]}\" 出现{cnt}次（LLM兜圈）")
                    break

    # 4. 纯空集校验：全是格式无内容
    text_only = re.sub(r'[#\-\*\s\n△]', '', chunk_output)
    if len(text_only) < 200:
        issues.append(f"有效内容不足：仅{len(text_only)}字符")

    # 5. token-loop 幻觉校验：
    # 剧情严格（——≤20直毙），剧本宽——高破折号可能是黑暗诗学风格
    # 只在破折号过高+内容重复同时出现时才判定幻觉
    dash_count = chunk_output.count("——")
    dash_limit = 50 if is_script else 20
    if is_script and dash_count > dash_limit:
        lines_clean = [l.strip() for l in chunk_output.split('\n') if '——' in l and l.strip()]
        repeat_burst = False
        if len(lines_clean) >= 6:
            stripped = [re.sub(r'[——△\s]', '', l) for l in lines_clean]
            for i in range(2, len(stripped)):
                if stripped[i] == stripped[i-1] == stripped[i-2]:
                    repeat_burst = True
                    break
            if not repeat_burst:
                pats = [re.split(r'——', l) for l in lines_clean]
                pat_lens = [tuple(len(p.strip()) for p in pt) for pt in pats if pt]
                for i in range(2, len(pat_lens)):
                    if pat_lens[i] == pat_lens[i-1] == pat_lens[i-2] and max(pat_lens[i]) > 0:
                        repeat_burst = True
                        break
        if repeat_burst:
            issues.append(f"幻觉：{dash_count}个\"——\"+重复结构（破折号灌水兜圈）")
        elif dash_count > 80:
            issues.append(f"幻觉：{dash_count}个\"——\"（严重超标，正常≤{dash_limit}）")
    elif not is_script and dash_count > dash_limit:
        issues.append(f"token-loop幻觉：{dash_count}个\"——\"（正常≤{dash_limit}）")
    elif wc > 10000:
        issues.append(f"集字数异常膨胀：{wc}字（正常3000-7000）")

    # 6. 尾句钩子检测：尾句是描述性收束/情绪总结/自然结束则不合格
    if is_script:
        lines = [l.strip() for l in chunk_output.split('\n') if l.strip()]
        content_end = None
        for i in range(len(lines) - 1, -1, -1):
            if '全文完' in lines[i]:
                content_end = i
                break
        if content_end is None:
            issues.append(f"缺少结尾标记\"**（全文完）**\"")
        if content_end is not None and content_end > 0:
            last_line = lines[content_end - 1]
            weak_patterns = [
                r'^(他|她|它|我|你)\w{0,2}(转身走了|转身离开了|走了出去|上车了|下车了|回头看了)[。]*$',
                r'^(天亮了|天黑了|雨停了|风停了)$',
                r'^△\s*车继续往前[开走][。]*$',
            ]
            is_weak = False
            for pat in weak_patterns:
                if re.match(pat, last_line):
                    is_weak = True
                    break
            if is_weak:
                issues.append(f"尾句钩子不足：\"{last_line[:40]}\"（禁止描述性收束/自然结束）")

    if issues:
        return {"pass": False, "reasons": issues}
    return {"pass": True}


async def _run_checkpoint_qc(agent, loop, outline: str, iterator, up_to_ci: int, rewind_count: int = 0):
    """每10集结构性质检：对比大纲和已生成剧情，检测角色消失/冲突跑偏。
    返回 (passed: bool, restart_ci: int, reason: str)"""
    if rewind_count >= 1:
        return True, 0, ""

    blocks_with_output = []
    for bi in range(up_to_ci):
        blk = iterator.blocks[bi]
        output = blk.get("_output", "")
        if output and len(output) > 500:
            blocks_with_output.append((blk["name"], blk["content"], output))

    if len(blocks_with_output) < 5:
        return True, 0, ""

    # 只对比已生成集数对应的大纲段（前 up_to_ci 集），不是全 80 集
    ep_markers = list(re.finditer(
        r'(?:^|\n)(?:\*{1,3}\s*\*{0,2}|#{1,3}\s*)第\d+[集章节]', outline
    ))
    if len(ep_markers) > up_to_ci:
        checked_outline = outline[:ep_markers[up_to_ci].start()]
    else:
        checked_outline = outline[:6000]

    snapshot_lines = []
    for name, outline_sec, text in blocks_with_output:
        snapshot_lines.append(f"\n## {name}")
        snapshot_lines.append(f"大纲: {outline_sec[:200]}")
        snapshot_lines.append(f"剧情首尾: {text[:300]}...{text[-300:]}")

    prompt = (
        f"你是剧本质检。当前进度第{up_to_ci}集——只检查前{up_to_ci}集内应该完成的内容。\n\n"
        f"## 待检查的大纲段（前{up_to_ci}集）\n"
        f"{checked_outline[:6000]}\n\n"
        "## 已生成剧集内容\n"
        + "\n".join(snapshot_lines) +
        f"\n\n检查前{up_to_ci}集内:\n"
        "1. 这些集数内大纲提到的主要角色都出场了吗？\n"
        "2. 这些集数内的核心事件都发生了吗？\n"
        "3. 如果有严重偏离（角色消失/核心事件未发生），从第几集开始偏的？\n\n"
        "注意: 后面集数的角色和事件还没写到，不算偏离。\n"
        "如果基本符合: 回复 PASS\n"
        "只有严重偏离时才回复: FAIL 第X集 原因:[一句话]"
    )

    def _run():
        result = ""
        try:
            for token in agent.call_llm_stream(prompt, "", temperature=0.3):
                result += token
        except Exception:
            pass
        return result

    result = await loop.run_in_executor(None, _run)

    if "FAIL" not in result:
        return True, 0, ""

    ep_match = re.search(r'第(\d+)集', result)
    restart_ep = int(ep_match.group(1)) if ep_match else max(1, up_to_ci - 3)
    restart_ci = max(0, restart_ep - 1)
    restart_ci = min(restart_ci, up_to_ci - 1)
    if restart_ci < up_to_ci - 5:
        restart_ci = up_to_ci - 5

    return False, restart_ci, result.strip()[:200]


class AsyncOrchestrator:
    AGENT_TO_CONFIG = {
        "outline_designer": "story_outline",
        "plot_expander": "full_plot",
        "screenplay_writer": "full_script",
        "storyboarder": "storyboard",
        "visual_extractor": "visual_extract",
        "image_preparator": "image_prep",
        "image_artist": "image_gen",
        "video_producer": "video_gen",
    }

    def __init__(self, ws_manager: ConnectionManager):
        self.ws = ws_manager
        self._screenplay_pipeline_task = None
        self._screenplay_trigger_count = 2

    async def _analyze_and_confirm_duration(self, project, project_name: str, style):
        """自动时长模式：LLM分析大纲 → 建议集数 → 用户确认 → 回填配置"""
        default = get_type_default(style.story_type)
        per_ep = default["per_ep"]
        type_name = default["name"]

        outline = project.read_output("01_故事大纲/故事大纲.md") or ""
        if not outline:
            return

        agent = create_agent("plot_expander")
        if not agent or not hasattr(agent, 'llm'):
            return

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, analyze_duration, agent.call_llm_stream, style.story_type, outline
        )
        if not result:
            return

        result["per_ep"] = per_ep
        result["type_name"] = type_name

        await self.ws.send_message(project_name, {
            "type": "auto_duration_suggest",
            "suggestion": result,
            "phase_index": 0,
        })

        confirmed = await self.ws.wait_for_duration_confirm(project_name)
        if not confirmed:
            return

        confirmed_count = confirmed.get("count", result["count"])
        confirmed_duration = confirmed.get("duration", per_ep)

        project.config["episode_count"] = str(confirmed_count)
        project.config["episode_duration"] = confirmed_duration
        project.save_config()

        style.episode_count = str(confirmed_count)
        style.episode_duration = confirmed_duration

        total_seconds = 0
        try:
            dur_num = int(''.join(c for c in confirmed_duration if c.isdigit()))
            if "分钟" in confirmed_duration or "字" in confirmed_duration:
                total_seconds = 60
            else:
                total_seconds = 60
        except:
            pass
        total_minutes = confirmed_count
        await self.ws.send_message(project_name, {
            "type": "auto_duration_confirmed",
            "count": confirmed_count,
            "duration": confirmed_duration,
            "total_minutes": total_minutes,
        })

    def _validate_and_notify(self, project, project_name: str, phase_index: int, content: str):
        """Check content volume and warn if exceeds target"""
        try:
            config = project.config
            style_data = config.get("style", {})
            dm = style_data.get("duration_mode", "1")
            if dm != "2":
                return
            count = int(style_data.get("episode_count", 0)) if style_data.get("episode_count") else 0
            d = (style_data.get("episode_duration", "") or "").replace("分钟", "").replace("分", "").strip()
            per = int(d) if d.isdigit() else 0
            total_minutes = count * per if count > 0 and per > 0 else 0
            if total_minutes <= 0:
                return
            result = validate_content(content, total_minutes)
            if not result["passed"]:
                asyncio.ensure_future(self.ws.send_message(project_name, {
                    "type": "content_warning",
                    "phase_index": phase_index,
                    "warnings": result["warnings"],
                    "stats": result["stats"],
                }))
        except Exception:
            pass

    async def _check_qc_and_notify(self, project, project_name, phase_index, agent_name):
        try:
            warnings = list(run_qc_check(agent_name, project.project_dir))

            _AGENT_OUTPUT_MAP = {
                "plot_expander": "02_完整剧情/完整剧情.md",
                "screenplay_writer": "03_完整剧本/完整剧本.md",
                "outline_designer": "01_故事大纲/故事大纲.md",
            }
            output_rel = _AGENT_OUTPUT_MAP.get(agent_name, "")
            if output_rel and agent_name in ("plot_expander", "screenplay_writer"):
                outline = project.read_output("01_故事大纲/故事大纲.md") or ""
                phase_output = project.read_output(output_rel) or ""
                if outline and phase_output and len(phase_output) > 500:
                    agent = create_agent(agent_name)
                    if agent and hasattr(agent, 'llm'):
                        result = await asyncio.get_event_loop().run_in_executor(
                            None, run_ai_quality_check, agent.llm, outline, phase_output, agent_name
                        )
                        ai_warnings = qc_result_to_warnings(result)
                        if ai_warnings:
                            warnings.extend(ai_warnings)

            if warnings:
                await self.ws.send_message(project_name, {
                    "type": "qc_warnings",
                    "phase": agent_name,
                    "warnings": warnings,
                })
                logger.warning(f"QC警告 [{agent_name}]: {len(warnings)} 条")
        except Exception as e:
            logger.warning(f"QC 检查异常: {e}")

    async def run(self, project_name: str, style_data: dict):
        project = ProjectManager(project_name)
        style = self._build_style(style_data)

        try:
            phases = WorkflowLoader.load()
            total = len(phases)

            config_phases = project.config.get("phases", [])
            config_names = [p["name"] for p in config_phases]
            has_done = any(
                config_phases[i].get("done", False)
                for i in range(len(config_phases))
            )
            if has_done:
                await self.continue_run(project_name, style_data)
                return

            if project.pending_episode is not None:
                await self.continue_run(project_name, style_data)
                return
            if project.config.get("_version_selected"):
                await self.continue_run(project_name, style_data)
                return

            await self.ws.send_message(project_name, {
                "type": "progress", "current": 0, "total": total,
            })

            paused_phase = False
            for idx, phase in enumerate(phases):
                if not phase.should_run(style.story_type):
                    continue

                output_path = self._get_output_path(phase)

                await self.ws.send_message(project_name, {
                    "type": "phase_start", "phase_index": idx,
                    "phase_name": phase.name, "total_phases": total,
                })
                await self.ws.send_message(project_name, {
                    "type": "progress", "current": idx, "total": total,
                })

                chunk_resume_ci = 0
                existing_full_parts = None
                pending_idx = project.config.get("pending_approval", -1)
                if idx == pending_idx and idx >= 0:
                    output_content = project.read_output(self._get_output_path(phase)) or ""
                    if output_content:
                        await self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": idx,
                            "chunk": output_content,
                        })
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": self._get_output_path(phase),
                    })
                    approval = await self._resume_approval(project, project_name, idx, style)
                    continue

                pending_ver = project.config.get("pending_version", -1)
                if idx == pending_ver and idx >= 0 and phase.agent == "outline_designer":
                    await self._resume_version_selection(project, project_name, idx, style)
                    continue
                # 兜底：pending_version 在断线时被清除，但磁盘上方向卡还在
                if phase.agent == "outline_designer" and idx == 0:
                    existing = project.read_output(output_path) or ""
                    if existing and len(existing) > 100 and ("版本A" in existing or "版本B" in existing):
                        project.set_pending_version(idx)
                        await self._resume_version_selection(project, project_name, idx, style)
                        continue

                snake_name = phase.agent
                agent = create_agent(snake_name)
                if hasattr(agent, 'douyin') and (style.story_type == "1" or style.writer_mode == "minimal"):
                    agent.douyin = True

                input_content = await self._get_input(project, phase)

                if phase.agent == "outline_designer":
                    task = project.read_output("00_任务指令/任务指令.md") or input_content
                    input_content = task

                pending_idx = project.config.get("pending_approval", -1)
                if idx == pending_idx and idx >= 0:
                    output_content = project.read_output(self._get_output_path(phase)) or ""
                    if output_content:
                        await self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": idx,
                            "chunk": output_content,
                        })
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": self._get_output_path(phase),
                    })
                    await self._resume_approval(project, project_name, idx, style)
                    continue

                pending_ver = project.config.get("pending_version", -1)
                if idx == pending_ver and idx >= 0 and phase.agent == "outline_designer":
                    await self._resume_version_selection(project, project_name, idx, style)
                    continue
                # 兜底：pending_version 在断线时被清除，但磁盘上方向卡还在
                if phase.agent == "outline_designer" and idx == 0:
                    existing = project.read_output(self._get_output_path(phase)) or ""
                    if existing and len(existing) > 100 and ("版本A" in existing or "版本B" in existing):
                        project.set_pending_version(idx)
                        await self._resume_version_selection(project, project_name, idx, style)
                        continue

                # Check if phase has existing content (confirmed but not approved)
                is_outline = phase.agent == "outline_designer"
                # 对于大纲阶段，即使有现有内容也不跳过，因为我们需要重新走两阶段流程
                if not is_outline:
                    output_path_check = self._get_output_path(phase)
                    existing_content = project.read_output(output_path_check) or ""
                    if existing_content.strip():
                        await self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": idx,
                            "chunk": existing_content,
                        })
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": output_path_check,
                        })
                        await self._resume_approval(project, project_name, idx, style)
                        continue

                if is_outline:
                    # 大纲阶段：先生成方向卡，不保存完整文件
                    # 方向卡生成，不发送 phase_complete
                    direction_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, idx)
                    direction_output = self._reorder_chunked_stream(agent, direction_output, project_name, idx)
                    project.write_output(output_path, direction_output)

                    # 方向卡生成完成，等待用户选择版本
                    await self.ws.send_message(project_name, {
                        "type": "awaiting_version",
                        "phase_index": idx,
                    })
                    project.set_pending_version(idx)
                    version_result = await self._wait_for_version(project_name)
                    version_choice = version_result.get("version", "1")
                    project.clear_pending_version()
                    project.config["_version_selected"] = version_choice
                    project.save_config()

                    # 用户已选择，开始生成完整大纲
                    version_letter = "A" if version_choice == "1" else "B"
                    fb = version_result.get("feedback", "").strip()

                    # 重新生成完整大纲的输入
                    second_input = f"\n\n## 用户选择\n请生成版本{version_letter}的完整大纲。" + (f"\n\n## 修改意见\n{fb}" if fb else "")
                    base_revise_input = second_input

                    await self.ws.send_message(project_name, {
                        "type": "phase_start", "phase_index": idx,
                        "phase_name": phase.name,
                    })

                    # 生成并保存完整大纲
                    if phase.split:
                        cr = await self._run_chunked_generation(
                            type(agent), project, style, second_input,
                            project_name, output_path, idx,
                            start_ci=chunk_resume_ci,
                            existing_full_parts=existing_full_parts
                        )
                        if cr.get("confirmed"):
                            project.config.pop("_version_selected", None)
                            project.save_config()
                            project.mark_phase_done(idx)
                            project.clear_pending_approval()
                            await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                            break
                        elif cr.get("action") == "paused":
                            await self.ws.send_message(project_name, {
                                "type": "phase_paused",
                                "phase_index": idx,
                                "phase_name": phase.name,
                            })
                            paused_phase = True
                            break
                    else:
                        full_output = await self._run_agent_in_thread(agent, project, style, second_input, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)

                        # 大纲集数校验：自动审核模式下，集数不足自动重试
                        expected_eps = int(style.episode_count) if style.episode_count and style.episode_count.isdigit() else 0
                        if expected_eps > 0 and self.ws.auto_approve_flags.get(project_name, False):
                            ep_count_retries = 0
                            while ep_count_retries < 3:
                                actual_eps = len(re.findall(
                                    r'(?:^|\n)(?:\*{1,3}\s*\*{0,2}|#{1,3}\s*)第\d+[集章节]', full_output
                                ))
                                if actual_eps >= expected_eps:
                                    break
                                ep_count_retries += 1
                                logger.warning(f"大纲集数不足: {actual_eps}/{expected_eps}，重试 {ep_count_retries}/3")
                                retry_input = second_input + (
                                    f"\n\n## 修改意见\n你只写了 {actual_eps} 集，但需要恰好 {expected_eps} 集。"
                                    f"请从第1集到第{expected_eps}集逐集完整写出，少一集都不行。"
                                )
                                full_output = await self._run_agent_in_thread(agent, project, style, retry_input, project_name, idx)
                                full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                                project.write_output(output_path, full_output)
                            if ep_count_retries >= 3:
                                logger.error(f"大纲集数校验失败: 3次重试后仍不足 {expected_eps} 集")
                                await self.ws.send_message(project_name, {
                                    "type": "episode_count_warning",
                                    "message": f"大纲集数可能不足 {expected_eps} 集，已自动重试3次",
                                })

                    project.config.pop("_version_selected", None)
                    project.save_config()

                    await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": output_path,
                    })

                    await self.ws.send_message(project_name, {
                        "type": "version_applied",
                        "phase_index": idx,
                        "version": version_letter,
                    })

                    await self.ws.send_message(project_name, {
                        "type": "awaiting_approval",
                        "phase_index": idx,
                    })

                    # 等待用户审核通过
                    project.set_pending_approval(idx)
                    approval = await self.ws.wait_for_approval(project_name, idx)
                    iterations = 0
                    while not approval.get("approved") and iterations < 5:
                        feedback = approval.get("feedback", "")
                        if not feedback:
                            project.clear_pending_approval()
                            break
                        revised_input = second_input + "\n\n## 修改意见\n" + feedback
                        full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)
                        approval = await self.ws.wait_for_approval(project_name, idx)
                        iterations += 1

                    if approval.get("approved"):
                        project.mark_phase_done(idx)

                        if style.duration_mode == "1":
                            await self._analyze_and_confirm_duration(project, project_name, style)

                    project.clear_pending_approval()
                    if approval.get("confirmed"):
                        await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                        break
                    continue
                elif phase.agent == "story_engine":
                    from agents.story_engine import StoryEngine
                    outline_text = project.read_output("01_故事大纲/故事大纲.md") or ""
                    episode_count = int(style.episode_count) if style.episode_count and style.episode_count.isdigit() else 80
                    loop = asyncio.get_event_loop()
                    beats = await loop.run_in_executor(
                        None,
                        lambda: StoryEngine().run_from_outline(outline_text, episode_count)
                    )
                    if beats:
                        project.write_output(output_path, json.dumps(beats, ensure_ascii=False, indent=2))
                    project.mark_phase_done(idx)
                else:
                    # 非大纲阶段，正常处理
                    # 流水线：如果剧本已在后台生成，直接等待并跳过
                    if phase.agent == "screenplay_writer" and self._screenplay_pipeline_task:
                        logger.info(f"流水线: 等待剧本后台任务完成")
                        await self._screenplay_pipeline_task
                        self._screenplay_pipeline_task = None
                        project.mark_phase_done(idx)
                        project.clear_pending_approval()
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": "03_完整剧本/完整剧本.md",
                        })
                        continue

                    if hasattr(agent, '_bible_mode') and agent._bible_mode:
                        full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        pass
                    elif phase.split:
                        cr = await self._run_chunked_generation(
                            type(agent), project, style, input_content,
                            project_name, output_path, idx
                        )
                        if cr.get("confirmed"):
                            project.mark_phase_done(idx)
                            project.clear_pending_approval()
                            await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                            break
                        elif cr.get("action") == "paused":
                            await self.ws.send_message(project_name, {
                                "type": "phase_paused",
                                "phase_index": idx,
                                "phase_name": phase.name,
                            })
                            paused_phase = True
                            break
                    else:
                        full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)

                    await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": output_path,
                    })
                    # 非大纲阶段，标记完成
                    project.mark_phase_done(idx)
                    project.clear_pending_approval()

            for pi in range(min(4, len(phases))):
                p = phases[pi]
                if p.should_run(style.story_type) and project.config.get("phases", []) and len(project.config["phases"]) > pi:
                    content = project.read_output(self._get_output_path(p)) or ""
                    self._validate_and_notify(project, project_name, pi, content)

            if not paused_phase:
                await self.ws.send_message(project_name, {"type": "all_complete"})
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.ws.send_message(project_name, {
                "type": "error",
                "message": f"生成中断: {str(e)}",
            })

    async def continue_run(self, project_name: str, style_data: dict):
        """从第一个未完成的阶段继续生成，跳过已完成的阶段"""
        logger.info(f"[CONTINUE] {project_name} 开始 continue_run, style_data keys={list(style_data.keys())}")
        project = ProjectManager(project_name)

        # 从 project_config 补齐缺失的 style 参数
        if not style_data or not style_data.get("story_type"):
            proj_style = project.config.get("style", {})
            if not style_data:
                style_data = {}
            if not style_data.get("story_type") and proj_style.get("story_type"):
                style_data["story_type"] = proj_style["story_type"]
            if not style_data.get("genre") and proj_style.get("genre"):
                style_data["genre"] = proj_style["genre"]
            if not style_data.get("episode_count") and proj_style.get("episode_count"):
                style_data["episode_count"] = proj_style["episode_count"]
            if not style_data.get("episode_duration") and proj_style.get("episode_duration"):
                style_data["episode_duration"] = proj_style["episode_duration"]
            if not style_data.get("writing_style") and proj_style.get("writing_style"):
                style_data["writing_style"] = proj_style["writing_style"]
            if not style_data.get("visual_style") and proj_style.get("visual_style"):
                style_data["visual_style"] = proj_style["visual_style"]
            if not style_data.get("art_style") and proj_style.get("art_style"):
                style_data["art_style"] = proj_style["art_style"]
            if not style_data.get("screen_aspect") and proj_style.get("screen_aspect"):
                style_data["screen_aspect"] = proj_style["screen_aspect"]
            if not style_data.get("script_style") and proj_style.get("script_style"):
                style_data["script_style"] = proj_style["script_style"]

        style = self._build_style(style_data)
        logger.info(f"[CONTINUE] {project_name} style built, story_type={style.story_type}, ep_count={style.episode_count}")

        try:
            phases = WorkflowLoader.load()
            total = len(phases)
            logger.info(f"[CONTINUE] {project_name} loaded {total} phases")
            start_idx = total
            config_phases = project.config.get("phases", [])
            config_names = [p["name"] for p in config_phases]

            for idx, phase in enumerate(phases):
                if not phase.should_run(style.story_type):
                    continue
                config_name = self.AGENT_TO_CONFIG.get(phase.agent, phase.agent)
                if config_name in config_names:
                    pidx = config_names.index(config_name)
                    phase_done = config_phases[pidx].get("done", False)
                else:
                    phase_done = False
                if not phase_done:
                    start_idx = idx
                    break

            logger.info(f"[CONTINUE] {project_name} 起始阶段 idx={start_idx}, total={total}")
            if start_idx >= total:
                logger.info(f"[CONTINUE] {project_name} 全部完成，发送 all_complete")
                await self.ws.send_message(project_name, {"type": "all_complete"})
                return

            await self.ws.send_message(project_name, {
                "type": "progress", "current": start_idx, "total": total,
            })

            # 发送已完成阶段的内容给前端（重连/新连接的客户端看不到历史阶段）
            for idx in range(start_idx):
                phase = phases[idx]
                if not phase.should_run(style.story_type):
                    continue
                config_name = self.AGENT_TO_CONFIG.get(phase.agent, phase.agent)
                phase_done = False
                for p in config_phases:
                    if p.get("name") == config_name:
                        phase_done = p.get("done", False)
                        break
                if phase_done:
                    output_path = self._get_output_path(phase)
                    content = project.read_output(output_path) or ""
                    if content:
                        await self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": idx,
                            "chunk": content,
                        })
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": output_path,
                        })

            paused_phase = False
            for idx in range(start_idx, total):
                phase = phases[idx]
                if not phase.should_run(style.story_type):
                    continue

                output_path = self._get_output_path(phase)

                pending_idx = project.config.get("pending_approval", -1)
                if idx == pending_idx and idx >= 0:
                    output_content = project.read_output(output_path) or ""
                    if output_content:
                        await self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": idx,
                            "chunk": output_content,
                        })
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": output_path,
                    })
                    await self._resume_approval(project, project_name, idx, style)
                    continue

                # story_engine (beat sheet) is silent - skip if done
                if phase.agent == "story_engine":
                    project.mark_phase_done(idx)
                    continue

                pending_ver = project.config.get("pending_version", -1)
                if idx == pending_ver and idx >= 0 and phase.agent == "outline_designer":
                    await self._resume_version_selection(project, project_name, idx, style)
                    continue

                # Check if phase has existing content (confirmed but not approved)
                is_outline = phase.agent == "outline_designer"
                # Check for pending episode approval (refresh after chunk complete but before approval)
                pending_ep = project.pending_episode
                chunk_resume_ci = 0
                existing_full_parts = None
                if pending_ep and pending_ep.get("phase_index") == idx:
                    # 先验证 pending_ep 的 chunk_files 是否还在磁盘上
                    chunk_files = pending_ep.get("chunk_files", [])
                    any_exists = any(project.read_output(cf) for cf in chunk_files)
                    if not any_exists:
                        logger.info(f"[CONTINUE] {project_name} pending_ep 无有效文件，清除")
                        project.clear_pending_episode()
                        pending_ep = None
                if pending_ep and pending_ep.get("phase_index") == idx:
                    resumed = await self._resume_chunked_approval(project, project_name, idx, pending_ep)
                    if resumed == "_paused":
                        paused_phase = True
                        break
                    if resumed:
                        continue
                    # 文件不存在 → 直接从 pending_ep 的索引继续生成
                    auto_resume = project.config.pop("_proceed_resume", False)
                    project.save_config()
                    if auto_resume:
                        chunk_resume_ci = pending_ep["chunk_index"]
                        chunk_files = pending_ep.get("chunk_files", [])
                        parts = []
                        for cf in chunk_files:
                            content = project.read_output(cf) or ""
                            if content:
                                parts.append(content)
                        if parts:
                            existing_full_parts = parts
                    else:
                        chunk_resume_ci = pending_ep["chunk_index"]
                        chunk_files = pending_ep.get("chunk_files", [])
                        parts = []
                        for cf in chunk_files:
                            content = project.read_output(cf) or ""
                            if content:
                                parts.append(content)
                        if parts:
                            existing_full_parts = parts
                # 无 pending_episode 时自动扫描已存在的剧集，从中断处继续
                if chunk_resume_ci == 0 and existing_full_parts is None and phase.split:
                    output_parent = project.project_dir / Path(output_path).parent
                    existing_dirs = []
                    if output_parent.exists():
                        existing_dirs = sorted(
                            [d for d in output_parent.iterdir()
                             if d.is_dir() and re.search(r'第\d+集', d.name)],
                            key=lambda d: int(re.search(r'第(\d+)集', d.name).group(1)) if re.search(r'第(\d+)集', d.name) else 0
                        )
                    if existing_dirs:
                        chunk_resume_ci = len(existing_dirs)
                        parts = []
                        base_stem = Path(output_path).stem
                        for d in existing_dirs:
                            md_files = list(d.glob("*.md"))
                            if md_files:
                                parts.append(md_files[0].read_text(encoding="utf-8"))
                        if parts:
                            existing_full_parts = parts
                        logger.info(f"自动检测到 {len(existing_dirs)} 个已有剧集，从第 {chunk_resume_ci+1} 集继续")
                # 对于大纲阶段，即使有现有内容也不跳过，因为我们需要重新走两阶段流程
                if not is_outline:
                    # 如果后面还有 pending_episode，当前阶段有内容就直接标记完成，不弹审核
                    pending_ep_later = project.pending_episode
                    if pending_ep_later and isinstance(pending_ep_later, dict) and pending_ep_later.get("phase_index", -1) > idx:
                        existing_content = project.read_output(output_path) or ""
                        if existing_content.strip():
                            project.mark_phase_done(idx)
                            continue
                    existing_content = project.read_output(output_path) or ""
                    if existing_content.strip():
                        await self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": idx,
                            "chunk": existing_content,
                        })
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": output_path,
                        })
                        await self._resume_approval(project, project_name, idx, style)
                        continue

                await self.ws.send_message(project_name, {
                    "type": "phase_start", "phase_index": idx,
                    "phase_name": phase.name, "total_phases": total,
                })
                await self.ws.send_message(project_name, {
                    "type": "progress", "current": idx, "total": total,
                })

                snake_name = phase.agent
                agent = create_agent(snake_name)
                if hasattr(agent, 'minimalist') and style.writer_mode == "minimal":
                    agent.minimalist = True
                if hasattr(agent, 'douyin') and style.story_type == "1":
                    agent.douyin = True

                input_content = await self._get_input(project, phase)
                if phase.agent == "outline_designer":
                    task = project.read_output("00_任务指令/任务指令.md") or input_content
                    input_content = task

                is_outline = phase.agent == "outline_designer"

                if is_outline:
                    vs = project.config.get("_version_selected")
                    if vs and project.read_output(output_path):
                        version_letter = "A" if vs == "1" else "B"
                        second_input = f"\n\n## 用户选择\n请生成版本{version_letter}的完整大纲。"
                        await self.ws.send_message(project_name, {
                            "type": "phase_start", "phase_index": idx,
                            "phase_name": phase.name, "total_phases": total,
                        })
                        full_output = await self._run_agent_in_thread(agent, project, style, second_input, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)
                        project.config.pop("_version_selected", None)
                        project.save_config()
                        await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": output_path,
                        })
                        await self.ws.send_message(project_name, {
                            "type": "version_applied",
                            "phase_index": idx,
                            "version": version_letter,
                        })
                        await self.ws.send_message(project_name, {
                            "type": "awaiting_approval",
                            "phase_index": idx,
                        })
                        project.set_pending_approval(idx)
                        approval = await self.ws.wait_for_approval(project_name, idx)
                        iterations = 0
                        while not approval.get("approved") and iterations < 5:
                            feedback = approval.get("feedback", "")
                            if not feedback:
                                project.clear_pending_approval()
                                break
                            revised_input = second_input + "\n\n## 修改意见\n" + feedback
                            full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, idx)
                            full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                            project.write_output(output_path, full_output)
                            await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                            await self.ws.send_message(project_name, {
                                "type": "phase_complete", "phase_index": idx,
                                "phase_name": phase.name, "file_path": output_path,
                            })
                            approval = await self.ws.wait_for_approval(project_name, idx)
                            iterations += 1
                        if approval.get("approved"):
                            project.mark_phase_done(idx)
                        project.clear_pending_approval()
                        if approval.get("confirmed"):
                            await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                            break
                        continue

                    direction_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, idx)
                    direction_output = self._reorder_chunked_stream(agent, direction_output, project_name, idx)
                    project.write_output(output_path, direction_output)

                    await self.ws.send_message(project_name, {
                        "type": "awaiting_version",
                        "phase_index": idx,
                    })
                    project.set_pending_version(idx)
                    version_result = await self._wait_for_version(project_name)
                    version_choice = version_result.get("version", "1")
                    project.clear_pending_version()
                    project.config["_version_selected"] = version_choice
                    project.save_config()

                    # 用户已选择，开始生成完整大纲
                    version_letter = "A" if version_choice == "1" else "B"
                    fb = version_result.get("feedback", "").strip()

                    # 重新生成完整大纲的输入
                    second_input = f"\n\n## 用户选择\n请生成版本{version_letter}的完整大纲。" + (f"\n\n## 修改意见\n{fb}" if fb else "")

                    await self.ws.send_message(project_name, {
                        "type": "phase_start", "phase_index": idx,
                        "phase_name": phase.name,
                    })

                    # 生成并保存完整大纲
                    if phase.split:
                        cr = await self._run_chunked_generation(
                            type(agent), project, style, second_input,
                            project_name, output_path, idx,
                            start_ci=chunk_resume_ci,
                            existing_full_parts=existing_full_parts
                        )
                        if cr.get("confirmed"):
                            project.config.pop("_version_selected", None)
                            project.save_config()
                            project.mark_phase_done(idx)
                            project.clear_pending_approval()
                            await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                            break
                        elif cr.get("action") == "paused":
                            await self.ws.send_message(project_name, {
                                "type": "phase_paused",
                                "phase_index": idx,
                                "phase_name": phase.name,
                            })
                            paused_phase = True
                            break
                    else:
                        full_output = await self._run_agent_in_thread(agent, project, style, second_input, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)

                    project.config.pop("_version_selected", None)
                    project.save_config()

                    await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": output_path,
                    })

                    await self.ws.send_message(project_name, {
                        "type": "version_applied",
                        "phase_index": idx,
                        "version": version_letter,
                    })

                    await self.ws.send_message(project_name, {
                        "type": "awaiting_approval",
                        "phase_index": idx,
                    })

                    # 等待用户审核通过
                    project.set_pending_approval(idx)
                    approval = await self.ws.wait_for_approval(project_name, idx)
                    iterations = 0
                    while not approval.get("approved") and iterations < 5:
                        feedback = approval.get("feedback", "")
                        if not feedback:
                            project.clear_pending_approval()
                            break
                        revised_input = second_input + "\n\n## 修改意见\n" + feedback
                        full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)
                        await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": output_path,
                        })
                        approval = await self.ws.wait_for_approval(project_name, idx)
                        iterations += 1

                    if approval.get("approved"):
                        project.mark_phase_done(idx)
                    project.clear_pending_approval()
                    if approval.get("confirmed"):
                        await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                        break
                    continue
                elif phase.agent == "story_engine":
                    await self.ws.send_message(project_name, {
                        "type": "phase_start", "phase_index": idx,
                        "phase_name": "节拍表",
                    })
                    from agents.story_engine import StoryEngine
                    outline_text = project.read_output("01_故事大纲/故事大纲.md") or ""
                    episode_count = int(style.episode_count) if style.episode_count and style.episode_count.isdigit() else 80
                    engine = StoryEngine()
                    beats = engine.run_from_outline(outline_text, episode_count)
                    if beats:
                        project.write_output(output_path, json.dumps(beats, ensure_ascii=False, indent=2))
                        project.mark_phase_done(idx)
                        await self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": idx,
                            "chunk": "节拍表已生成：" + str(len(beats)) + "集",
                        })
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": output_path,
                            "beat_count": len(beats),
                        })
                    else:
                        await self.ws.send_message(project_name, {
                            "type": "error", "message": "节拍表生成失败，跳过节拍表阶段",
                            "phase_index": idx,
                        })
                        project.mark_phase_done(idx)
                    await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                else:
                    # 非大纲阶段，正常处理
                    if phase.split:
                        cr = await self._run_chunked_generation(
                            type(agent), project, style, input_content,
                            project_name, output_path, idx,
                            start_ci=chunk_resume_ci,
                            existing_full_parts=existing_full_parts
                        )
                        if cr.get("confirmed"):
                            project.mark_phase_done(idx)
                            project.clear_pending_approval()
                            await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                            break
                        elif cr.get("action") == "paused":
                            await self.ws.send_message(project_name, {
                                "type": "phase_paused",
                                "phase_index": idx,
                                "phase_name": phase.name,
                            })
                            paused_phase = True
                            break
                    else:
                        full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)

                    await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": output_path,
                    })

                project.set_pending_approval(idx)
                # chunked phases: approval handled inside _run_chunked_generation
                if not phase.split:
                    approval = await self.ws.wait_for_approval(project_name, idx)
                    iterations = 0
                    while not approval.get("approved") and iterations < 5:
                        feedback = approval.get("feedback", "")
                        if not feedback:
                            project.clear_pending_approval()
                            break
                        revised_input = input_content + "\n\n## 修改意见\n" + feedback
                        full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, idx)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                        project.write_output(output_path, full_output)
                        await self._check_qc_and_notify(project, project_name, idx, phase.agent)
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": idx,
                            "phase_name": phase.name, "file_path": output_path,
                        })
                        approval = await self.ws.wait_for_approval(project_name, idx)
                        iterations += 1

                    if approval.get("approved"):
                        project.mark_phase_done(idx)
                    project.clear_pending_approval()
                    if approval.get("confirmed"):
                        await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                        break
                else:
                    project.mark_phase_done(idx)
                    project.clear_pending_approval()

            for pi in range(min(4, len(phases))):
                p = phases[pi]
                if p.should_run(style.story_type):
                    content = project.read_output(self._get_output_path(p)) or ""
                    self._validate_and_notify(project, project_name, pi, content)

            if not paused_phase:
                await self.ws.send_message(project_name, {"type": "all_complete"})
        except asyncio.CancelledError:
            pass

    async def redo_phase(self, project_name: str, style_data: dict, phase_index: int, feedback: str = ""):
        try:
            project = ProjectManager(project_name)
            style = self._build_style(style_data)
            phases = WorkflowLoader.load()

            if phase_index < 0 or phase_index >= len(phases):
                return
            phase = phases[phase_index]

            output_path = self._get_output_path(phase)

            await self.ws.send_message(project_name, {
                "type": "phase_start", "phase_index": phase_index,
                "phase_name": phase.name, "total_phases": len(phases),
            })

            snake_name = phase.agent
            agent = create_agent(snake_name)
            if hasattr(agent, 'minimalist') and style.writer_mode == "minimal":
                agent.minimalist = True
            if hasattr(agent, 'douyin') and style.story_type == "1":
                agent.douyin = True

            input_content = await self._get_input(project, phase)
            if phase.agent == "outline_designer":
                task = project.read_output("00_任务指令/任务指令.md") or input_content
                input_content = task

            if feedback:
                input_content += f"\n\n## 修改意见\n{feedback}"

            is_outline = phase.agent == "outline_designer"

            # 将当前阶段及所有下游阶段标记为未完成
            config_phases = project.config.get("phases", [])
            config_names = [p["name"] for p in config_phases]
            phase_config_name = self.AGENT_TO_CONFIG.get(phase.agent, phase.agent)
            if phase_config_name in config_names:
                start_pidx = config_names.index(phase_config_name)
                for i in range(start_pidx, len(config_phases)):
                    config_phases[i]["done"] = False
                project.save_config()
                # 清理当前阶段及下游阶段的输出文件
                for i in range(start_pidx, len(config_phases)):
                    for p in phases:
                        p_config_name = self.AGENT_TO_CONFIG.get(p.agent, p.agent)
                        if p_config_name == config_phases[i]["name"]:
                            out_path = self._get_output_path(p)
                            project.delete_output(out_path)
                            # 清理分集文件：删除 output 目录下所有 base_stem_*.md
                            parent_dir = project.project_dir / str(Path(out_path).parent)
                            base_stem = Path(out_path).stem
                            if parent_dir.exists():
                                for f in parent_dir.glob(f"{base_stem}_*.md"):
                                    f.unlink()
                                for subdir in parent_dir.iterdir():
                                    if subdir.is_dir():
                                        for f in subdir.glob(f"{base_stem}.md"):
                                            f.unlink()
                                        try:
                                            subdir.rmdir()
                                        except OSError:
                                            pass
                            break

            if is_outline:
                # 方向卡生成，不发送 phase_complete
                direction_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, phase_index)
                direction_output = self._reorder_chunked_stream(agent, direction_output, project_name, phase_index)

                # 方向卡生成完成，等待用户选择版本
                await self.ws.send_message(project_name, {
                    "type": "awaiting_version",
                    "phase_index": phase_index,
                })
                project.set_pending_version(phase_index)
                version_result = await self._wait_for_version(project_name)
                version_choice = version_result.get("version", "1")
                project.clear_pending_version()

                # 用户已选择，开始生成完整大纲
                version_letter = "A" if version_choice == "1" else "B"
                fb = version_result.get("feedback", "").strip()

                # 重新生成完整大纲的输入
                second_input = f"\n\n## 用户选择\n请生成版本{version_letter}的完整大纲。" + (f"\n\n## 修改意见\n{fb}" if fb else "")

                await self.ws.send_message(project_name, {
                    "type": "phase_start", "phase_index": phase_index,
                    "phase_name": phase.name,
                })

                # 生成并保存完整大纲
                if phase.split:
                    await self._run_chunked_generation(
                        type(agent), project, style, second_input,
                        project_name, output_path, phase_index
                    )
                else:
                    full_output = await self._run_agent_in_thread(agent, project, style, second_input, project_name, phase_index)
                    full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
                    project.write_output(output_path, full_output)

                await self._check_qc_and_notify(project, project_name, phase_index, phase.agent)
                await self.ws.send_message(project_name, {
                    "type": "phase_complete", "phase_index": phase_index,
                    "phase_name": phase.name, "file_path": output_path,
                })

                await self.ws.send_message(project_name, {
                    "type": "version_applied",
                    "phase_index": phase_index,
                    "version": version_letter,
                })

                await self.ws.send_message(project_name, {
                    "type": "awaiting_approval",
                    "phase_index": phase_index,
                })

                # 等待用户审核通过
                project.set_pending_approval(phase_index)
                approval = await self.ws.wait_for_approval(project_name, phase_index)
                iterations = 0
                while not approval.get("approved") and iterations < 5:
                    feedback = approval.get("feedback", "")
                    if not feedback:
                        project.clear_pending_approval()
                        break
                    revised_input = second_input + "\n\n## 修改意见\n" + feedback
                    full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, phase_index)
                    full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
                    project.write_output(output_path, full_output)
                    approval = await self.ws.wait_for_approval(project_name, phase_index)
                    iterations += 1

                if approval.get("approved"):
                    project.mark_phase_done(phase_index)
                project.clear_pending_approval()
                if approval.get("confirmed"):
                    await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": phase_index})
                    return
            else:
                # 非大纲阶段，正常处理
                if phase.split:
                    cr = await self._run_chunked_generation(
                        type(agent), project, style, input_content,
                        project_name, output_path, phase_index
                    )
                    if cr.get("confirmed"):
                        project.mark_phase_done(phase_index)
                        project.clear_pending_approval()
                        await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": phase_index})
                        return
                    elif cr.get("action") == "paused":
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": phase_index,
                            "phase_name": phase.name, "file_path": output_path,
                        })
                        await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": phase_index})
                        return
                else:
                    full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, phase_index)
                    full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
                    project.write_output(output_path, full_output)

                await self._check_qc_and_notify(project, project_name, phase_index, phase.agent)
                await self.ws.send_message(project_name, {
                    "type": "phase_complete", "phase_index": phase_index,
                    "phase_name": phase.name, "file_path": output_path,
                })

                await self.ws.send_message(project_name, {
                    "type": "awaiting_approval",
                    "phase_index": phase_index,
                })

                # 第一阶段第二步：等待用户审核通过
                project.set_pending_approval(phase_index)
                approval = await self.ws.wait_for_approval(project_name, phase_index)
                iterations = 0
                while not approval.get("approved") and iterations < 5:
                    feedback = approval.get("feedback", "")
                    if not feedback:
                        project.clear_pending_approval()
                        break
                    revised_input = input_content + "\n\n## 修改意见\n" + feedback
                    full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, phase_index)
                    full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
                    project.write_output(output_path, full_output)
                    approval = await self.ws.wait_for_approval(project_name, phase_index)
                    iterations += 1

                if approval.get("approved"):
                    project.mark_phase_done(phase_index)
                project.clear_pending_approval()
                if approval.get("confirmed"):
                    return
        except asyncio.CancelledError:
            pass

    @staticmethod
    def _auto_anchor_abstract_concepts(custom_requirements: str) -> str:
        anchor_rules = [
            "画面永远比解释多一步。抽象概念通过实物触发：钟停在几点几分、水杯里没有波纹、镜子里多了一行字。",
            "同一画面、同一句话、同一句台词——在同一集中绝对不要重复。每个△行描述一个新的视觉变化。",
        ]
        return custom_requirements + "\n\n" + "\n".join(anchor_rules)

    def _build_style(self, style_data: dict) -> StyleConfig:
        style = StyleConfig()
        style.story_type = style_data.get("story_type", "")
        style.genre = style_data.get("genre", "")
        style.writing_style = style_data.get("writing_style", "")
        style.visual_style = style_data.get("visual_style", "")
        style.art_style = style_data.get("art_style", "")
        style.screen_aspect = style_data.get("screen_aspect", "")
        style.script_style = style_data.get("script_style", "")
        style.duration_mode = style_data.get("duration_mode", "")
        style.episode_count = style_data.get("episode_count", "")
        style.episode_duration = style_data.get("episode_duration", "")
        style.custom_requirements = style_data.get("custom_requirements", "")
        style.visual_reference = style_data.get("visual_reference", "")
        style.action_reference = style_data.get("action_reference", "")
        style.mood = style_data.get("mood", "")
        style.custom_requirements = self._auto_anchor_abstract_concepts(
            style.custom_requirements
        )
        return style

    async def _wait_for_version(self, project_name: str) -> dict:
        # 自动审核模式下，自动选版本 A
        if self.ws.auto_approve_flags.get(project_name, False):
            return {"version": "1", "feedback": "", "auto": True}
        await self.ws.send_message(project_name, {
            "type": "awaiting_version",
            "phase_index": 0,
            "message": "请选择大纲版本",
        })
        evt = self.ws.pending_approvals.get(project_name)
        if not evt:
            # 创建一个新的事件来等待用户选择
            evt = asyncio.Event()
            self.ws.pending_approvals[project_name] = evt
        evt.clear()
        try:
            await evt.wait()
        except asyncio.CancelledError:
            raise
        result = self.ws.approval_results.get(project_name, {})
        self.ws.approval_results[project_name] = None
        return result if result else {"version": "1"}

    def _cleanse_outline_version(self, project, output_path, version):
        import re
        content = project.read_output(output_path)
        if not content:
            return
        if version == "A":
            pattern = r"^(#{1,4}\s*\*{0,2}版本B\s*\*{0,2}.*?)(?=^#{1,4}|\Z)"
            replacement = ""
            cleaned = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
            cleaned = cleaned.rstrip() + "\n\n---\n\n> ✅ 已选中版本A，版本B已移除。"
        elif version == "B":
            pattern = r"^(#{1,4}\s*\*{0,2}版本A\s*\*{0,2}.*?)(?=^#{1,4}|\Z)"
            replacement = ""
            cleaned = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
            cleaned = cleaned.rstrip() + "\n\n---\n\n> ✅ 已选中版本B，版本A已移除。"
        else:
            return
        project.write_output(output_path, cleaned)

    def _get_output_path(self, phase) -> str:
        output = phase.output
        if output.endswith("/"):
            filename_map = {
                "01_故事大纲/": "故事大纲.md",
                "02_完整剧情/": "完整剧情.md",
                "03_完整剧本/": "完整剧本.md",
                "04_角色场景/": "角色场景.md",
                "05_分镜脚本/": "分镜脚本.md",
                "06_生图需求/": "分析报告.md",
            }
            return output + filename_map.get(output, "产出.md")
        return output

    async def _run_agent_in_thread(self, agent, project, style, input_content, project_name, phase_index):
        import asyncio
        import traceback
        import os
        from .routes.gen import _get_active_agg_config

        agg = _get_active_agg_config("llm")
        has_key = agg and agg.get("api_key")
        if not has_key:
            backend = os.getenv("LLM_BACKEND", "deepseek")
            key_map = {"deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY", "claude": "CLAUDE_API_KEY"}
            env_key = key_map.get(backend, "DEEPSEEK_API_KEY")
            has_key = bool(os.getenv(env_key))

        if not has_key:
            error_msg = "API Key 未配置，请在设置页配置 API Key"
            await self.ws.send_message(project_name, {
                "type": "error",
                "message": error_msg,
                "phase_index": phase_index,
            })
            raise RuntimeError(error_msg)

        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        cancelled = [False]

        def _run():
            try:
                for chunk in agent.run_stream(project, style, input_content):
                    if cancelled[0]:
                        break
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                tb = traceback.format_exc()
                if not cancelled[0]:
                    loop.call_soon_threadsafe(queue.put_nowait, {"__error__": str(e), "__traceback__": tb})
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        future = loop.run_in_executor(None, _run)

        full_output = ""
        error_info = None
        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=600)
            except asyncio.TimeoutError:
                cancelled[0] = True
                error_msg = f"生成超时（600秒无响应），请检查模型是否正常运行"
                await self.ws.send_message(project_name, {
                    "type": "error", "message": error_msg, "phase_index": phase_index,
                })
                raise RuntimeError(error_msg)
            if chunk is None:
                break
            if isinstance(chunk, dict) and "__error__" in chunk:
                error_info = chunk
                continue
            full_output += chunk
            await self.ws.send_message(project_name, {
                "type": "stream", "phase_index": phase_index, "chunk": chunk,
            })

        if error_info:
            error_msg = f"Agent 执行出错: {error_info['__error__']}"
            await self.ws.send_message(project_name, {
                "type": "error", "message": error_msg, "phase_index": phase_index,
            })
            raise RuntimeError(error_msg)

        return full_output

    async def _resume_approval(self, project, project_name, phase_index, style=None):
        project.set_pending_approval(phase_index)
        approval = await self.ws.wait_for_approval(project_name, phase_index)
        iterations = 0
        while not approval.get("approved") and iterations < 5:
            feedback = approval.get("feedback", "")
            if not feedback:
                project.clear_pending_approval()
                break
            from core.workflow_loader import WorkflowLoader
            phases = WorkflowLoader.load()
            phase = phases[phase_index] if phase_index < len(phases) else None
            if not phase:
                project.clear_pending_approval()
                break
            snake_name = phase.agent
            agent = create_agent(snake_name)
            if hasattr(agent, 'minimalist') and style and style.writer_mode == "minimal":
                agent.minimalist = True
            if hasattr(agent, 'douyin') and style and style.story_type == "1":
                agent.douyin = True
            output_content = project.read_output(self._get_output_path(phase)) or ""
            if phase.agent == "outline_designer":
                revised_input = "## 用户选择\n请生成版本A的完整大纲。\n\n## 修改意见\n" + feedback
            else:
                revised_input = output_content + "\n\n## 修改意见\n" + feedback
            if style is None:
                from core.style_config import StyleConfig
                style = StyleConfig()
            revised_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, phase_index)
            revised_output = self._reorder_chunked_stream(agent, revised_output, project_name, phase_index)
            project.write_output(self._get_output_path(phase), revised_output)
            await self._check_qc_and_notify(project, project_name, phase_index, phase.agent)
            await self.ws.send_message(project_name, {
                "type": "phase_complete", "phase_index": phase_index,
                "phase_name": phase.name, "file_path": self._get_output_path(phase),
            })
            approval = await self.ws.wait_for_approval(project_name, phase_index)
            iterations += 1
        if approval.get("approved"):
            project.mark_phase_done(phase_index)
        project.clear_pending_approval()
        if approval.get("confirmed"):
            return

    async def _resume_version_selection(self, project, project_name, phase_index, style):
        from core.workflow_loader import WorkflowLoader
        phases = WorkflowLoader.load()
        phase = phases[phase_index] if phase_index < len(phases) else None
        if not phase:
            return
        output_path = self._get_output_path(phase)
        content = project.read_output(output_path) or ""
        if content:
            await self.ws.send_message(project_name, {
                "type": "stream", "phase_index": phase_index, "chunk": content,
            })
            await asyncio.sleep(0.3)

        project.set_pending_version(phase_index)
        version_result = await self._wait_for_version(project_name)
        version_choice = version_result.get("version", "1")
        project.clear_pending_version()

        if version_choice in ("1", "2"):
            version_letter = "A" if version_choice == "1" else "B"
            self._cleanse_outline_version(project, output_path, version_letter)
            project.mark_phase_done(phase_index)
            await self.ws.send_message(project_name, {
                "type": "version_applied", "phase_index": phase_index,
                "version": version_letter,
            })
        elif version_choice == "3":
            fb = version_result.get("feedback", "")
            if fb:
                revised_input = content + "\n\n## 修改意见\n请混合版本A和版本B：" + fb
                agent = create_agent("outline_designer")
                full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, phase_index)
                full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
                project.write_output(output_path, full_output)
                project.mark_phase_done(phase_index)
                await self._check_qc_and_notify(project, project_name, phase_index, phase.agent)
                await self.ws.send_message(project_name, {
                    "type": "phase_complete", "phase_index": phase_index,
                    "phase_name": phase.name, "file_path": output_path,
                })
                return

    def _save_split_output(self, project, output_path, content):
        content = self._fix_character_format(content)
        content = self._wrap_long_text(content)
        project.write_output(output_path, content)
        from tools.content_splitter import split_by_headings, make_split_filename
        split_parts = split_by_headings(content)
        for title, section in split_parts:
            if not section.strip():
                continue
            if not title:
                fname_clean = str(output_path).replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                project.write_output(fname_clean, section)
            else:
                fname = make_split_filename(str(output_path), title)
                fname_clean = fname.replace(str(project.project_dir) + "\\", "").replace(str(project.project_dir) + "/", "")
                project.write_output(fname_clean, section)

    @staticmethod
    def _fix_character_format(content: str) -> str:
        """强制修正人物设定排版：让 姓名/外表/性格/背景/目标/动机 每个属性独立成行"""
        import re
        keys_pattern = r'(姓名|外表|性格|背景|目标|动机)[：:]'
        result = []
        for line in content.split('\n'):
            stripped = line.strip()
            matches = list(re.finditer(keys_pattern, stripped))
            if len(matches) >= 2:
                parts = re.split(r'(?=姓名[：:]|外表[：:]|性格[：:]|背景[：:]|目标[：:]|动机[：:])', stripped)
                fixed = '\n'.join(p for p in parts if p.strip())
                result.append(fixed)
            else:
                result.append(line)
        return '\n'.join(result)

    @staticmethod
    def _wrap_long_text(content: str, max_chars: int = 80) -> str:
        """对叙事文本做自动换行：在中句号/感叹号/问号/分号/省略号后分行"""
        import re
        lines = content.split('\n')
        result = []
        for line in lines:
            stripped = line.rstrip()
            # 跳过镜头头标行、转场行、角色/场景行、空行、代码块
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
            # 只对纯叙事文本（长于 max_chars 的行）换行
            if len(stripped) > max_chars and not stripped.startswith('#'):
                # 在句末标点后换行，保留标点
                wrapped = re.sub(
                    r'([。！？；…])(?![」』）】\n])',
                    r'\1\n',
                    stripped
                )
                # 如果换行后的行还是太长，在逗号后也折一下
                final_lines = []
                for wl in wrapped.split('\n'):
                    if len(wl) > max_chars + 20:
                        wl = re.sub(r'([，、；：])', r'\1\n', wl)
                    final_lines.append(wl)
                result.append('\n'.join(final_lines))
            else:
                result.append(line)
        return '\n'.join(result)

    def _ep_sort_key(self, name: str):
        nums = re.findall(r'\d+', name)
        return int(nums[0]) if nums else 0

    async def _run_screenplay_pipeline(self, project, project_name: str, style):
        """后台流水线：每检测到新剧情分集，立即生成对应剧本。与 plot 并行。"""
        from agents.screenplay_writer import ScreenplayWriter
        import os

        plot_dir = project.project_dir / "02_完整剧情"
        script_dir = project.project_dir / "03_完整剧本"
        script_dir.mkdir(parents=True, exist_ok=True)

        processed = set()
        total_expected = int(style.episode_count) if style.episode_count and style.episode_count.isdigit() else 80

        await self.ws.send_message(project_name, {
            "type": "phase_start", "phase_index": 3,
            "phase_name": "完整剧本（流水线）", "total_phases": 7,
        })

        while True:
            # 扫描已完成剧情分集
            if not plot_dir.exists():
                await asyncio.sleep(5)
                continue

            plot_subdirs = sorted(
                [d for d in plot_dir.iterdir() if d.is_dir()],
                key=lambda d: self._ep_sort_key(d.name)
            )
            available = [d for d in plot_subdirs if d.name not in processed]
            if not available:
                # 检查 plot 是否全部完成
                config_phases = project.config.get("phases", [])
                plot_done = any(
                    p.get("name", "") == "完整剧情" and p.get("done")
                    for p in config_phases
                )
                if plot_done or len(plot_subdirs) >= total_expected:
                    break
                await asyncio.sleep(3)
                continue

            # 取下一批待处理的剧情
            batch = available[:4]  # 一次处理 4 个分集
            for ep_dir in batch:
                ep_name = ep_dir.name
                md_path = ep_dir / "完整剧情.md"
                if not md_path.exists():
                    continue
                plot_text = md_path.read_text(encoding="utf-8")

                # 构建上下文：仅取前一集剧本尾段，避免历史主题在后半段累积压过本集剧情
                prev_scripts = []
                _prev_sorted = sorted(
                    [sd for sd in script_dir.iterdir()
                     if sd.is_dir() and sd.name < ep_name and (sd / "完整剧本.md").exists()],
                    key=lambda d: self._ep_sort_key(d.name)
                )
                if _prev_sorted:
                    _last = _prev_sorted[-1] / "完整剧本.md"
                    prev_scripts.append(_last.read_text(encoding="utf-8")[-1200:])

                # 构建 prompt
                agent = ScreenplayWriter()
                agent.douyin = (style.story_type == "1" or style.writer_mode == "minimal")

                if agent.douyin:
                    template = agent.load_prompt_template("screenplay_writer_douyin.txt")
                else:
                    template = agent.load_prompt_template("screenplay_writer.txt")
                    meta = agent._load_plot_meta(project, plot_text)
                    template = template.replace("{confirmed_direction}", meta["confirmed_direction"])
                    template = template.replace("{promise_list}", meta["promise_list"])

                outline_text = project.read_output("01_故事大纲/故事大纲.md") or ""
                voice_labels_pipeline = []
                if outline_text and agent.douyin:
                    from core.voice_labels import format_voice_injection, extract_voice_labels
                    voice_labels_pipeline = extract_voice_labels(outline_text)
                    voice = format_voice_injection(voice_labels_pipeline)
                    if voice:
                        template += "\n\n" + voice

                if agent.douyin:
                    bible = load_bible(project.project_dir)
                    if bible:
                        bible_inj = format_bible_injection(bible)
                        if bible_inj:
                            template += "\n\n" + bible_inj
                    from core.voice_labels import build_hard_constraint_card
                    card = build_hard_constraint_card(outline_text)
                    if card:
                        template += card

                anchor = _build_creative_anchor(project)
                if anchor:
                    template += anchor

                # 生成：本集剧情不再内联中段，改放末尾（见下方追加），此处仅占位
                prompt = template.replace("{plot_structure}", "（本集剧情见文末「本集剧情·唯一事件依据」一节，以那里为准）")

                # Batch hint goes AFTER main prompt — the last instruction carries the most weight
                _nums = re.findall(r'\d+', ep_name)
                is_batch = len(_nums) >= 2
                if is_batch:
                    s, e = int(_nums[0]), int(_nums[-1])
                    all_eps = "、".join([f"第{i}集" for i in range(s, e + 1)])
                    prompt += (
                        f"\n\n【批量生成指令——必须严格遵守，这是最终要求】"
                        f"\n本批次需要一次性生成以下 {e-s+1} 集完整剧本：{all_eps}。"
                        f"\n每集不少于 1000 字，必须包含画面描述和对白。"
                        f"\n每集以「第X集」作为独立标题（不加##标记）。集与集之间用空行分隔。"
                        f"\n每集结尾必须有悬念钩子。"
                        f"\n重要：在输出「**（全文完）**」之前，请逐集检查是否已生成全部 {e-s+1} 集。"
                        f"\n禁止省略、合并、跳过任何一集。禁止把多集写成一段。"
                    )
                else:
                    prompt += f"\n\n当前正在生成：{ep_name}"

                if prev_scripts:
                    # 清洗旧格式，避免LLM跟着抄
                    cleaned = []
                    for ps in prev_scripts[-3:]:
                        c = re.sub(r'^#{1,3}\s+.*$', '', ps, flags=re.MULTILINE)
                        c = re.sub(r'^出场角色：.*$', '', c, flags=re.MULTILINE)
                        c = re.sub(r'^---\s*$', '', c, flags=re.MULTILINE)
                        c = re.sub(r'\n{3,}', '\n\n', c)
                        cleaned.append(c)
                    prompt += "\n\n## 前序剧本\n\n" + "\n\n".join(cleaned)

                # 格式约束放最后——LLM对末尾注意力最高
                ep_num = re.search(r'\d+', ep_name)
                ep_n = ep_num.group(0) if ep_num else "1"
                voice_rules_p = ""
                if voice_labels_pipeline:
                    voice_rules_p = "\n\n## ⚠️ 每人说话方式——逐人硬约束（不遵守则全批作废）\n\n"
                    for vl in voice_labels_pipeline:
                        voice_rules_p += f"- {vl['name']}：{vl['tag']}\n"
                    voice_rules_p += "\n写完每句对白自查：删掉角色名还能认出是谁说的吗？认不出就重写。\n"
                else:
                    voice_rules_p = "\n\n## ⚠️ 对白声音分化\n\n- 两个角色不能说出同样长度、同样句式、同样情绪的对白\n- 写完每句对白自查：删掉角色名还能认出是谁说的吗？\n\n"
                prompt += (
                    f"\n\n## ⚠️ 输出格式强制要求\n\n"
                    f"开头: {ep_name}\n"
                    f"场头: 场{ep_n}-{{序号}}  时间  内外  地点\n"
                    f"  例如: 场{ep_n}-1  夜  内  客厅\n"
                    f"动作: △ 描述（每条1-2句）\n"
                    f"对白: 角色名（情绪/动作）：对白（同行写，不换行）\n"
                    f"换场: 空一行后写新场头\n"
                    f"结尾: **（全文完）**\n\n"
                    f"禁止: ##标记、###标记、出场角色行、对白独占三行、对白超15字\n"
                    f"⚠️ 每集只写1-2场（抖音短剧2分钟一集，场多了观众记不住场景）。1场一镜到底最好，2场只在必须换地点时用。3场以上视为废稿。\n"
                    f"{voice_rules_p}"
                    f"示例:\n"
                    f"{ep_name}\n\n"
                    f"场{ep_n}-1  夜  内  客厅\n\n"
                    f"△ 蜡烛只剩一根亮着。\n\n"
                    f"陈国栋（掏手机）：谁？\n\n"
                    f"△ 屏幕上躺着短信。\n\n"
                    f"场{ep_n}-2  日  外  门口\n\n"
                    f"△ 铁门上贴着黄纸条。\n\n"
                    f"陈国栋vo：三十年了。\n\n"
                    f"**（全文完）**"
                )

                # 本集剧情放在最末尾——LLM对末尾注意力最高，确保本集事件不被前序上下文/历史主题淹没
                prompt += (
                    f"\n\n## ⚠️ 本集剧情·唯一事件依据（最高优先级）\n\n"
                    f"以下是{ep_name}的剧情，是本集唯一的事件来源。"
                    f"你必须把其中描述的每一个具体动作、每一处场景、每一个道具逐一转成镜头。"
                    f"故事主线和人物情感要延续前文，但本集发生的【事件】必须严格按下面这份剧情推进，"
                    f"禁止用前几集已经出现过的场景、画面或台词替代本集剧情，禁止停在原地复述。\n\n"
                    f"{plot_text}"
                )

                # 结尾钩子强化——放最末尾，决定追剧率。验证可显著把抒情收束改成真钩子
                prompt += (
                    f"\n\n## ⚠️ 结尾钩子·强制要求（追剧率命门，最高优先级）\n"
                    f"本集最后一个镜头必须是「不公平钩子」——让观众知道一件角色还不知道的事，"
                    f"或一个正在发生、尚未揭晓结果的危险/异常。\n"
                    f"禁止用以下方式收尾（这些会让观众划走）：\n"
                    f"- 情绪收束：『她没有回头』『她哭了』『她笑了』『阳光落在她身上』\n"
                    f"- 平淡动作：『她往前走』『她走出去』『天亮了』\n"
                    f"- 模糊意象：『像是在笑』『又像是哭』\n"
                    f"正确钩子示例：『△ 她锁上门。△ 门内，那张照片自己翻了一面。』"
                    f"『△ 手机亮了。△ 屏幕上是她自己的号码——正在拨入。』\n"
                    f"最后一行必须制造『下一集会发生什么』的疑问，不是给本集画句号。"
                )

                chunk_output = ""
                retries = 0
                while retries < 3:
                    try:
                        for token in agent.call_llm_stream(prompt, "", temperature=0.8):
                            chunk_output += token
                        break
                    except Exception as e:
                        retries += 1
                        logger.error(f"剧本流水线 [{ep_name}] LLM失败 ({retries}/3): {e}")
                        if retries >= 3:
                            break
                        await asyncio.sleep(5)

                if not chunk_output.strip():
                    processed.add(ep_name)
                    continue

                # 保存
                save_dir = script_dir / ep_name
                save_dir.mkdir(parents=True, exist_ok=True)
                (save_dir / "完整剧本.md").write_text(chunk_output, encoding="utf-8")

                processed.add(ep_name)
                logger.info(f"剧本流水线: {ep_name} 完成")

            # 合并已生成的所有剧本
            all_scripts = []
            for sd in sorted(script_dir.iterdir(), key=lambda d: self._ep_sort_key(d.name)):
                if sd.is_dir():
                    sf = sd / "完整剧本.md"
                    if sf.exists():
                        all_scripts.append(sf.read_text(encoding="utf-8"))
            if all_scripts:
                (script_dir / "完整剧本.md").write_text("\n\n---\n\n".join(all_scripts), encoding="utf-8")

            # 检查是否全部完成
            config_phases = project.config.get("phases", [])
            plot_done = any(p.get("name", "") == "完整剧情" and p.get("done") for p in config_phases)
            if (plot_done and len(processed) >= len(plot_subdirs)) or len(processed) >= total_expected:
                break

        await self.ws.send_message(project_name, {
            "type": "phase_complete", "phase_index": 3,
            "phase_name": "完整剧本（流水线）",
        })

    async def _run_chunked_generation(self, agent_class, project, style, input_content, project_name, output_path, phase_index,
                                      start_ci=0, existing_full_parts=None):
        """逐集生成+审核：每集生成完->保存->审核->通过后才生成下一集
        支持 start_ci 从指定位置继续，existing_full_parts 恢复已生成的内容
        返回 {"action": "approve"} | {"action": "confirm", "confirmed": True} | {"action": "paused"}
        """
        agent = agent_class()
        chunk_count, chunk_names = agent.prepare_generation(project, style, input_content)
        if chunk_count <= 0:
            # 不分集模式（如短剧），退回全量生成
            full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, phase_index)
            full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
            project.write_output(output_path, full_output)
            return {"action": "approve"}

        iterator = agent._gen_iterator
        is_reverse = iterator.plan.reverse_order
        indices = list(range(chunk_count))
        if is_reverse:
            indices = list(reversed(indices))

        base_stem = Path(output_path).stem
        parent = str(Path(output_path).parent)
        full_parts = list(existing_full_parts) if existing_full_parts else []

        if project_name and phase_index >= 0:
            if project_name not in self.ws.chunked_phases:
                self.ws.chunked_phases[project_name] = set()
            self.ws.chunked_phases[project_name].add(phase_index)

        def _build_gen_kwargs(agent_obj, ctx_):
            """根据 agent 类型构建 generate_chunk 的参数"""
            kwargs = dict(
                ctx=ctx_,
                template=agent_obj._gen_template,
                style_context=agent_obj._gen_style_context,
                writing_style_name=agent_obj._gen_writing_style_name,
                story_type_name=agent_obj._gen_story_type_name,
                style=style,
                plan=agent_obj._gen_plan,
                feedback="",
            )
            if hasattr(agent_obj, '_gen_screen_aspect_name'):
                kwargs["screen_aspect_name"] = agent_obj._gen_screen_aspect_name
            if hasattr(agent_obj, '_gen_outline'):
                kwargs["outline"] = agent_obj._gen_outline
            if hasattr(agent_obj, '_gen_script_style_name'):
                kwargs["script_style_name"] = agent_obj._gen_script_style_name
            if hasattr(agent_obj, '_gen_script_format_name'):
                kwargs["script_format_name"] = agent_obj._gen_script_format_name
            if hasattr(agent_obj, '_gen_input_content'):
                kwargs["input_content"] = agent_obj._gen_input_content
            return kwargs

        current_feedback = ""
        ci = start_ci
        while ci < len(indices):
            chunk_index = indices[ci]
            ctx = iterator.get_chunk_context(chunk_index)
            if ctx is None:
                ci += 1
                continue
            display_name = ctx.name if ctx.name else f"第{ci+1}集"

            # 大纲加权：当前集大纲 + 前后各2集，让LLM知道从哪来到哪去
            if "完整剧情" in output_path and len(iterator.blocks) > 5:
                expanded = ""
                for offset in range(-2, 3):
                    ni = chunk_index + offset
                    if 0 <= ni < len(iterator.blocks):
                        blk = iterator.blocks[ni]
                        tag = "【本集大纲-必须遵循】" if offset == 0 else f"（第{ni+1}集大纲参考·{abs(offset)}集{'后' if offset>0 else '前'}）"
                        expanded += f"\n{tag}\n{blk['content']}\n"
                if expanded:
                    ctx.outline_section = expanded

            # 生成单集（在后台线程中运行 generate_chunk，流式输出）
            loop = asyncio.get_event_loop()
            queue = asyncio.Queue()
            cancelled = [False]

            kwargs = _build_gen_kwargs(agent, ctx)
            kwargs["chunk_name"] = display_name
            if current_feedback:
                kwargs["feedback"] = current_feedback

            prev_continuity = load_last_continuity(project.project_dir)
            if prev_continuity:
                injection = generate_continuity_injection(prev_continuity, None)
                if injection:
                    kwargs["template"] = kwargs["template"] + "\n\n## 前情提要（上一集状态追踪）\n\n" + injection
                    logger.info(f"ContinuityLog 已注入前情提要到 {display_name}")

            story_bible = load_bible(project.project_dir)
            if story_bible:
                bible_injection = format_bible_injection(story_bible)
                if bible_injection:
                    kwargs["template"] = kwargs["template"] + "\n\n" + bible_injection
                    logger.info(f"StoryBible 已注入到 {display_name}")

            anchor = _build_creative_anchor(project)
            if anchor:
                kwargs["template"] = kwargs["template"] + anchor
                logger.info(f"[ANCHOR] 创作锚点已注入到 {display_name}")

            def _run():
                try:
                    gen = agent.generate_chunk(**kwargs)
                    for token in gen:
                        if cancelled[0]:
                            break
                        loop.call_soon_threadsafe(queue.put_nowait, token)
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    if not cancelled[0]:
                        loop.call_soon_threadsafe(queue.put_nowait, {"__error__": str(e), "__traceback__": tb})
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            await self.ws.send_message(project_name, {"type": "stream_clear"})
            future = loop.run_in_executor(None, _run)

            chunk_output = ""
            try:
                while True:
                    try:
                        token = await asyncio.wait_for(queue.get(), timeout=900)
                    except asyncio.TimeoutError:
                        cancelled[0] = True
                        await self.ws.send_message(project_name, {
                            "type": "error", "message": "生成超时（900秒无响应）", "phase_index": phase_index,
                        })
                        raise RuntimeError("生成超时")
                    if token is None:
                        break
                    if isinstance(token, dict) and "__error__" in token:
                        raise RuntimeError(token.get("__error__", "未知错误"))
                    chunk_output += token
                    await self.ws.send_message(project_name, {
                        "type": "stream", "phase_index": phase_index, "chunk": token,
                    })
            except asyncio.CancelledError:
                cancelled[0] = True
                raise

            # 保存当前集文件
            chunk_output = self._fix_character_format(chunk_output)
            chunk_output = self._wrap_long_text(chunk_output)
            chunk_output = _normalize_chunk_heading(chunk_output, display_name)
            ep_dir_rel = Path(output_path).parent / display_name
            ep_dir_rel_str = ep_dir_rel.as_posix()
            chunk_fname = f"{ep_dir_rel_str}/{base_stem}.md"
            project.write_output(chunk_fname, chunk_output)
            full_parts.append(chunk_output)
            iterator.set_output(chunk_index, chunk_output)
            if hasattr(agent, '_last_chunk_output'):
                agent._last_chunk_output = chunk_output

            # 自动审核模式：出厂质检
            if self.ws.auto_approve_flags.get(project_name, False):
                ep_count = int(style.episode_count) if style.episode_count and style.episode_count.isdigit() else 0
                qc = _validate_chunk_quality(chunk_output, ep_count, phase=output_path)
                if not qc["pass"]:
                    retry_key = f"_qc_retry_{phase_index}_{chunk_index}"
                    retry_count = getattr(self, retry_key, 0)
                    if retry_count < 2:
                        setattr(self, retry_key, retry_count + 1)
                        logger.warning(f"QC FAIL [{display_name}] retry {retry_count+1}/2: {qc['reasons']}")
                        current_feedback = "【质量检查不通过，请重新生成】\n" + "\n".join(qc["reasons"])
                        continue
                    else:
                        logger.error(f"QC FAIL [{display_name}] after 2 retries, proceeding with degraded quality")
                        await self.ws.send_message(project_name, {
                            "type": "qc_warning",
                            "phase_index": phase_index,
                            "chunk_name": display_name,
                            "reasons": qc["reasons"],
                        })

            try:
                log = extract_continuity(chunk_output, None)
                save_continuity(project.project_dir, display_name, log)
                logger.info(f"ContinuityLog 已提取: {display_name}")
            except Exception as e:
                logger.warning(f"ContinuityLog 提取失败 ({display_name}): {e}")

            if "完整剧本" in output_path:
                try:
                    inc_result = VisualBibleExtractor.extract_incremental(chunk_output)
                    if inc_result.get("characters") or inc_result.get("scenes"):
                        inc_dir = project.project_dir / "04_角色场景" / "_incremental"
                        inc_dir.mkdir(parents=True, exist_ok=True)
                        inc_file = inc_dir / f"{display_name}.json"
                        inc_file.write_text(json.dumps(inc_result, ensure_ascii=False, indent=2), encoding="utf-8")
                        char_count = len(inc_result.get("characters", []))
                        scene_count = len(inc_result.get("scenes", []))
                        await self.ws.send_message(project_name, {
                            "type": "visual_incremental",
                            "phase_index": phase_index,
                            "chunk_name": display_name,
                            "char_count": char_count,
                            "scene_count": scene_count,
                            "message": f"已提取 {display_name} 的 {char_count} 个角色、{scene_count} 个场景",
                        })
                except Exception as e:
                    logger.warning(f"增量视觉提取失败 ({display_name}): {e}")

            # 持久化逐集审核状态（刷新后可恢复）
            project.set_pending_episode(phase_index, ci, display_name, chunk_count, chunk_files=[chunk_fname])

            # StoryBible: 每 N 集更新一次全局故事圣经
            if should_update_bible(ci + 1) and hasattr(agent, 'llm'):
                try:
                    blocks_with_output = sorted(
                        [b for b in iterator.blocks if b.get("_output")],
                        key=lambda b: b["index"]
                    )
                    recent_eps = [(b["name"], b["_output"]) for b in blocks_with_output[-BIBLE_UPDATE_INTERVAL:]]
                    if len(recent_eps) >= 2:
                        existing = load_bible(project.project_dir)
                        loop = asyncio.get_event_loop()
                        updated = await loop.run_in_executor(
                            None, build_bible_update, agent.llm, project.project_dir, recent_eps, existing
                        )
                        if updated:
                            save_bible(project.project_dir, updated)
                            logger.info(f"StoryBible 已更新（第 {ci + 1} 集后）")
                except Exception as e:
                    logger.warning(f"StoryBible 更新异常: {e}")

            # 通知前端并等待审核
            await self.ws.send_message(project_name, {
                "type": "chunk_saved",
                "phase_index": phase_index,
                "chunk_name": display_name,
                "chunk_index": ci,
                "total_chunks": chunk_count,
                "file_path": chunk_fname,
            })

            # 流水线：剧情阶段完成 N 个 chunk 后自动启动剧本生成
            if phase_index == 2 and not self._screenplay_pipeline_task:
                completed_chunks = ci + 1 - start_ci
                if completed_chunks >= self._screenplay_trigger_count:
                    self._screenplay_pipeline_task = asyncio.create_task(
                        self._run_screenplay_pipeline(project, project_name, style)
                    )
                    logger.info(f"流水线: 剧情已完成 {completed_chunks} chunk，启动剧本并行生成")

            ep_result = await self.ws.wait_for_episode_approval(
                project_name, phase_index, display_name, ci, chunk_count
            )
            action = ep_result.get("action", "approve")
            if action == "approve":
                ci += 1
                current_feedback = ""

                # 每10集结构性质检（仅剧情阶段）：对比大纲全文检查角色消失/冲突跑偏
                if "完整剧情" in output_path and ci >= 10 and ci % 10 == 0 and ci < chunk_count:
                    ck_key = ci // 10
                    if ck_key not in getattr(self, '_cp_rewound', set()):
                        passed, restart_ci, reason = await _run_checkpoint_qc(
                            agent, loop, input_content, iterator, ci,
                            rewind_count=sum(1 for k in getattr(self, '_cp_rewound', set()) if k == ck_key)
                        )
                        if not passed:
                            logger.warning(f"CheckpointQC [{ci}/{chunk_count}] FAIL → restart ep{restart_ci+1}: {reason[:80]}")
                            if not hasattr(self, '_cp_rewound'):
                                self._cp_rewound = set()
                            self._cp_rewound.add(ck_key)
                            for bi in range(restart_ci, len(iterator.blocks)):
                                iterator.blocks[bi].pop("_output", None)
                                iterator.blocks[bi].pop("_summary", None)
                            if hasattr(self, '_screenplay_processed'):
                                for bi in range(restart_ci, len(iterator.blocks)):
                                    self._screenplay_processed.discard(iterator.blocks[bi]["name"])
                            ci = restart_ci
                            current_feedback = (
                                f"【结构检查不通过·从第{restart_ci+1}集重写】{reason}\n"
                                f"大纲中的所有角色必须出场，核心冲突不能偏离，剧情方向必须与大纲一致。"
                            )
                            continue

            elif action == "confirm":
                project.clear_pending_episode()
                if ci < chunk_count - 1:
                    # 还有剩余集 → 暂停，不结束阶段
                    # 构建已生成的 chunk 文件名列表（用于恢复时重建 existing_full_parts）
                    saved_chunk_files = []
                    for i in range(ci + 1):
                        cidx = indices[i]
                        ctxi = iterator.get_chunk_context(cidx)
                        name = ctxi.name if ctxi.name else f"第{i+1}集"
                        ep_dir_r = Path(output_path).parent / name
                        cfname = f"{ep_dir_r.as_posix()}/{base_stem}.md"
                        saved_chunk_files.append(cfname)
                    project.set_pending_episode(phase_index, ci + 1, f"第{ci+2}集", chunk_count, chunk_files=saved_chunk_files)
                    return {"action": "paused"}
                break
            elif action == "revise":
                feedback = ep_result.get("feedback", "")
                if feedback:
                    current_feedback = feedback
                    full_parts.pop()
                    project.clear_pending_episode()
                else:
                    ci += 1
                    current_feedback = ""
                    project.clear_pending_episode()

        # 所有块通过后写入合并文件
        if full_parts:
            project.write_output(output_path, "\n\n---\n\n".join(full_parts))
        project.clear_pending_episode()
        return {"action": "confirm" if action == "confirm" else "approve", "confirmed": action == "confirm"}

    async def _resume_chunked_approval(self, project, project_name, phase_index, pending_ep):
        """恢复逐集审核：读取已保存的 chunk 文件，重放，发送 episode_complete，等待用户操作
        如果文件不存在（暂停后续生成场景），返回 None 让调用方走正常生成流程
        """
        chunk_name = pending_ep["chunk_name"]
        chunk_index = pending_ep["chunk_index"]
        total_chunks = pending_ep["total_chunks"]

        phases = WorkflowLoader.load()
        if phase_index < 0 or phase_index >= len(phases):
            return True
        phase = phases[phase_index]
        output_path = self._get_output_path(phase)
        base_stem = Path(output_path).stem
        parent = str(Path(output_path).parent)

        chunk_fname_rel = Path(output_path).parent / chunk_name / (base_stem + ".md")
        chunk_fname = chunk_fname_rel.as_posix()
        content = project.read_output(chunk_fname) or ""
        if not content.strip():
            # 文件不存在 → 这是暂停后继续生成的场景，走正常生成流程
            return False

        # 重放流式内容
        await self.ws.send_message(project_name, {"type": "stream_clear"})
        await self.ws.send_message(project_name, {
            "type": "stream", "phase_index": phase_index, "chunk": content,
        })

        # 重新发送 chunk_saved
        await self.ws.send_message(project_name, {
            "type": "chunk_saved",
            "phase_index": phase_index,
            "chunk_name": chunk_name,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "file_path": chunk_fname,
        })

        # 发送 episode_complete，进入逐集审核等待
        await self.ws.send_message(project_name, {
            "type": "episode_complete",
            "phase_index": phase_index,
            "chunk_name": chunk_name,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
        })

        # 等待用户操作
        ep_result = await self.ws.wait_for_episode_approval(
            project_name, phase_index, chunk_name, chunk_index, total_chunks
        )
        action = ep_result.get("action", "approve")
        if action == "confirm":
            project.clear_pending_episode()
            if chunk_index < total_chunks - 1:
                saved_chunk_files = pending_ep.get("chunk_files", [])
                project.set_pending_episode(phase_index, chunk_index + 1, f"第{chunk_index + 2}集", total_chunks, chunk_files=saved_chunk_files)
                await self.ws.send_message(project_name, {
                    "type": "phase_paused",
                    "phase_index": phase_index,
                    "phase_name": phases[phase_index].name if phase_index < len(phases) else "",
                })
                return "_paused"
            project.mark_phase_done(phase_index)
            await self._check_qc_and_notify(project, project_name, phase_index, phase.agent)
            await self.ws.send_message(project_name, {"type": "phase_complete", "phase_index": phase_index})
            await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": phase_index})
        elif action == "revise":
            feedback = ep_result.get("feedback", "")
            if feedback:
                project.clear_pending_episode()
                project.mark_phase_done(phase_index)
                await self.redo_phase(project_name, {"story_type": "", "genre": "", "writing_style": ""}, phase_index, feedback)
            else:
                project.clear_pending_episode()
                project.mark_phase_done(phase_index)
                await self._check_qc_and_notify(project, project_name, phase_index, phase.agent)
                await self.ws.send_message(project_name, {"type": "phase_complete", "phase_index": phase_index})
                await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": phase_index})
        else:
            project.clear_pending_episode()
            next_ci = chunk_index + 1
            if next_ci >= total_chunks:
                project.mark_phase_done(phase_index)
                await self._check_qc_and_notify(project, project_name, phase_index, phase.agent)
                await self.ws.send_message(project_name, {"type": "phase_complete", "phase_index": phase_index})
                await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": phase_index})
                return True
            return False
        return True

    def _reorder_chunked_stream(self, agent, full_output: str, project_name: str, phase_index: int) -> str:
        full_output = self._fix_character_format(full_output)
        if hasattr(agent, '_chunks') and agent._chunks:
            ordered = [c["output"] for c in agent._chunks if c.get("output")]
            if len(ordered) > 1:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.ws.send_message(project_name, {"type": "stream_clear"}))
                        loop.create_task(self.ws.send_message(project_name, {
                            "type": "stream", "phase_index": phase_index,
                            "chunk": "\n\n---\n\n".join(ordered),
                        }))
                except RuntimeError:
                    pass
                return "\n\n---\n\n".join(ordered)
            elif ordered:
                return ordered[0]
        return full_output

    async def _get_input(self, project: ProjectManager, phase) -> str:
        input_map = {
            "plot_expander": "01_故事大纲/故事大纲.md",
            "screenplay_writer": "02_完整剧情/完整剧情.md",
            "storyboarder": "03_完整剧本/完整剧本.md",
            "image_preparator": "05_分镜脚本/分镜脚本.md",
        }
        source = input_map.get(phase.agent)
        if source:
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
            else:
                content = project.read_output(source)
            return content or ""
        return ""

