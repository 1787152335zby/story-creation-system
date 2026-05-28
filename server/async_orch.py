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
from core.agent_factory import create_agent
from core.visual_bible import VisualBibleExtractor

from .ws_manager import ConnectionManager

logger = logging.getLogger(__name__)


def _normalize_chunk_heading(chunk_output: str, display_name: str) -> str:
    """确保分镜/剧本的每集输出以 # 第N集 开头，去除前导散文内容"""
    import re
    text = chunk_output.strip()
    # 在全文中找 # 第N集 标题，找到了就从那里截取
    episode_match = re.search(r'^(#{1,4}\s*第\d+[集章部篇])', text, re.MULTILINE)
    if episode_match:
        return text[episode_match.start():]
    # 找不到集标题，去除前导散文（直到第一个有效内容标记）
    for token in ["###", "##", "---", "镜头", "【全片完】"]:
        idx = text.find(token)
        if idx >= 0:
            text = text[idx:]
            break
    if not text.startswith("#"):
        text = f"# {display_name}\n\n{text}"
    return text


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
            qc_warnings = run_qc_check(agent_name, project.project_dir)
            if qc_warnings:
                await self.ws.send_message(project_name, {
                    "type": "qc_warnings",
                    "phase": agent_name,
                    "warnings": qc_warnings,
                })
                logger.warning(f"QC警告 [{agent_name}]: {len(qc_warnings)} 条")
        except Exception as e:
            logger.error(f"QC检查失败: {e}")

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

                snake_name = phase.agent
                agent = create_agent(snake_name)

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
                    project.clear_pending_approval()
                    if approval.get("confirmed"):
                        await self.ws.send_message(project_name, {"type": "phase_confirmed", "phase_index": idx})
                        break
                    continue
                else:
                    # 非大纲阶段，正常处理
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
        project = ProjectManager(project_name)
        style = self._build_style(style_data)

        try:
            phases = WorkflowLoader.load()
            total = len(phases)
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

            if start_idx >= total:
                await self.ws.send_message(project_name, {"type": "all_complete"})
                return

            await self.ws.send_message(project_name, {
                "type": "progress", "current": start_idx, "total": total,
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
                    existing_dirs = sorted(
                        [d for d in (project.project_dir / Path(output_path).parent).iterdir()
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
                chunk = await asyncio.wait_for(queue.get(), timeout=180)
            except asyncio.TimeoutError:
                cancelled[0] = True
                error_msg = f"生成超时（180秒无响应），请检查模型是否正常运行"
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
                        token = await asyncio.wait_for(queue.get(), timeout=180)
                    except asyncio.TimeoutError:
                        cancelled[0] = True
                        await self.ws.send_message(project_name, {
                            "type": "error", "message": "生成超时（180秒无响应）", "phase_index": phase_index,
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

            # 通知前端并等待审核
            await self.ws.send_message(project_name, {
                "type": "chunk_saved",
                "phase_index": phase_index,
                "chunk_name": display_name,
                "chunk_index": ci,
                "total_chunks": chunk_count,
                "file_path": chunk_fname,
            })

            ep_result = await self.ws.wait_for_episode_approval(
                project_name, phase_index, display_name, ci, chunk_count
            )
            action = ep_result.get("action", "approve")
            if action == "approve":
                ci += 1
                current_feedback = ""
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

