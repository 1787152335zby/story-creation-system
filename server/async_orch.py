import asyncio
import concurrent.futures
from pathlib import Path

from core.project_manager import ProjectManager
from core.style_config import StyleConfig, STORY_TYPES
from core.workflow_loader import WorkflowLoader
from agents.orchestrator import _split_sort_key
from core.content_validator import validate_content

from .ws_manager import ConnectionManager


class AsyncOrchestrator:
    AGENT_TO_CONFIG = {
        "outline_designer": "story_outline",
        "plot_expander": "full_plot",
        "screenplay_writer": "full_script",
        "storyboarder": "storyboard",
        "visual_extractor": "visual_extract",
        "prompt_factory": "prompts",
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

            await self.ws.send_message(project_name, {
                "type": "progress", "current": 0, "total": total,
            })

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
                    approval = await self._resume_approval(project, project_name, idx)
                    continue

                pending_ver = project.config.get("pending_version", -1)
                if idx == pending_ver and idx >= 0 and phase.agent == "outline_designer":
                    await self._resume_version_selection(project, project_name, idx, style)
                    continue

                import importlib
                snake_name = phase.agent
                class_name = "".join(word.capitalize() for word in snake_name.split("_"))
                module = importlib.import_module(f"agents.{snake_name}")
                agent_class = getattr(module, class_name)
                agent = agent_class()

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
                    await self._resume_approval(project, project_name, idx)
                    continue

                pending_ver = project.config.get("pending_version", -1)
                if idx == pending_ver and idx >= 0 and phase.agent == "outline_designer":
                    await self._resume_version_selection(project, project_name, idx, style)
                    continue

                # Check if phase has existing content (confirmed but not approved)
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
                    await self._resume_approval(project, project_name, idx)
                    continue

                full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, idx)
                full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)

                if hasattr(agent, '_bible_mode') and agent._bible_mode:
                    pass
                elif phase.split:
                    if hasattr(agent, '_chunks') and agent._chunks:
                        self._save_chunked_output(project, output_path, agent._chunks)
                    else:
                        self._save_split_output(project, output_path, full_output)
                else:
                    project.write_output(output_path, full_output)

                await self.ws.send_message(project_name, {
                    "type": "phase_complete", "phase_index": idx,
                    "phase_name": phase.name, "file_path": output_path,
                })

                is_outline = phase.agent == "outline_designer"
                if is_outline:
                    project.set_pending_version(idx)
                    version_result = await self._wait_for_version(project_name)
                    version_choice = version_result.get("version", "1")
                    project.clear_pending_version()

                    if version_choice in ("1", "2"):
                        version_letter = "A" if version_choice == "1" else "B"
                        fb = version_result.get("feedback", "").strip()
                        if fb:
                            revised_input = input_content + f"\n\n## 修改意见\n请以版本{version_letter}为基础，按以下要求修改：{fb}"
                            full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, idx)
                            full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                            project.write_output(output_path, full_output)
                        else:
                            self._cleanse_outline_version(project, output_path, version_letter)
                        project.mark_phase_done(idx)
                        await self.ws.send_message(project_name, {
                            "type": "version_applied",
                            "phase_index": idx,
                            "version": version_letter,
                        })
                        continue
                    elif version_choice == "3":
                        fb = version_result.get("feedback", "")
                        if fb:
                                revised_input = input_content + "\n\n## 修改意见\n请混合版本A和版本B：" + fb
                                full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, idx)
                                full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                                project.write_output(output_path, full_output)
                                project.mark_phase_done(idx)
                                await self.ws.send_message(project_name, {
                                    "type": "phase_complete", "phase_index": idx,
                                    "phase_name": phase.name, "file_path": output_path,
                                })
                        continue

                    project.set_pending_approval(idx)
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
                        if hasattr(agent, '_bible_mode') and agent._bible_mode:
                            pass
                        elif phase.split:
                            if hasattr(agent, '_chunks') and agent._chunks:
                                self._save_chunked_output(project, output_path, agent._chunks)
                            else:
                                self._save_split_output(project, output_path, full_output)
                        else:
                            project.write_output(output_path, full_output)

                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": output_path,
                    })

                    approval = await self.ws.wait_for_approval(project_name, idx)
                    iterations += 1

                if approval.get("approved"):
                    project.mark_phase_done(idx)
                elif approval.get("confirmed"):
                    project.mark_phase_done(idx)
                    await self.ws.wait_for_proceed(project_name)
                project.clear_pending_approval()

            for pi in range(min(4, len(phases))):
                p = phases[pi]
                if p.should_run(style.story_type) and project.config.get("phases", []) and len(project.config["phases"]) > pi:
                    content = project.read_output(self._get_output_path(p)) or ""
                    self._validate_and_notify(project, project_name, pi, content)

            await self.ws.send_message(project_name, {"type": "all_complete"})
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.ws.send_message(project_name, {
                "type": "error",
                "message": f"生成中断: {str(e)}",
                "phase_index": phase_index,
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
                    await self._resume_approval(project, project_name, idx)
                    continue

                pending_ver = project.config.get("pending_version", -1)
                if idx == pending_ver and idx >= 0 and phase.agent == "outline_designer":
                    await self._resume_version_selection(project, project_name, idx, style)
                    continue

                # Check if phase has existing content (confirmed but not approved)
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
                    await self._resume_approval(project, project_name, idx)
                    continue

                await self.ws.send_message(project_name, {
                    "type": "phase_start", "phase_index": idx,
                    "phase_name": phase.name, "total_phases": total,
                })
                await self.ws.send_message(project_name, {
                    "type": "progress", "current": idx, "total": total,
                })

                import importlib
                snake_name = phase.agent
                class_name = "".join(word.capitalize() for word in snake_name.split("_"))
                module = importlib.import_module(f"agents.{snake_name}")
                agent_class = getattr(module, class_name)
                agent = agent_class()

                input_content = await self._get_input(project, phase)

                if phase.agent == "outline_designer":
                    task = project.read_output("00_任务指令/任务指令.md") or input_content
                    input_content = task

                full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, idx)
                full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)

                if phase.split:
                    if hasattr(agent, '_chunks') and agent._chunks:
                        self._save_chunked_output(project, output_path, agent._chunks)
                    else:
                        self._save_split_output(project, output_path, full_output)
                else:
                    project.write_output(output_path, full_output)

                await self.ws.send_message(project_name, {
                    "type": "phase_complete", "phase_index": idx,
                    "phase_name": phase.name, "file_path": output_path,
                })

                is_outline = phase.agent == "outline_designer"
                if is_outline:
                    project.set_pending_version(idx)
                    version_result = await self._wait_for_version(project_name)
                    version_choice = version_result.get("version", "1")
                    project.clear_pending_version()
                    if version_choice in ("1", "2"):
                        version_letter = "A" if version_choice == "1" else "B"
                        self._cleanse_outline_version(project, output_path, version_letter)
                        project.mark_phase_done(idx)
                        await self.ws.send_message(project_name, {
                            "type": "version_applied", "phase_index": idx,
                            "version": version_letter,
                        })
                        continue
                    elif version_choice == "3":
                        fb = version_result.get("feedback", "")
                        if fb:
                            revised_input = input_content + "\n\n## 修改意见\n请混合版本A和版本B：" + fb
                            full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, idx)
                            full_output = self._reorder_chunked_stream(agent, full_output, project_name, idx)
                            project.write_output(output_path, full_output)
                            project.mark_phase_done(idx)
                            await self.ws.send_message(project_name, {
                                "type": "phase_complete", "phase_index": idx,
                                "phase_name": phase.name, "file_path": output_path,
                            })
                    continue

                project.set_pending_approval(idx)
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
                    if phase.split:
                        if hasattr(agent, '_chunks') and agent._chunks:
                            self._save_chunked_output(project, output_path, agent._chunks)
                        else:
                            self._save_split_output(project, output_path, full_output)
                    else:
                        project.write_output(output_path, full_output)
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": idx,
                        "phase_name": phase.name, "file_path": output_path,
                    })
                    approval = await self.ws.wait_for_approval(project_name, idx)
                    iterations += 1

                if approval.get("approved"):
                    project.mark_phase_done(idx)
                project.clear_pending_approval()

            for pi in range(min(4, len(phases))):
                p = phases[pi]
                if p.should_run(style.story_type):
                    content = project.read_output(self._get_output_path(p)) or ""
                    self._validate_and_notify(project, project_name, pi, content)

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

            import importlib
            snake_name = phase.agent
            class_name = "".join(word.capitalize() for word in snake_name.split("_"))
            module = importlib.import_module(f"agents.{snake_name}")
            agent_class = getattr(module, class_name)
            agent = agent_class()

            input_content = await self._get_input(project, phase)
            if phase.agent == "outline_designer":
                task = project.read_output("00_任务指令/任务指令.md") or input_content
                input_content = task

            if feedback:
                input_content += f"\n\n## 修改意见\n{feedback}"

            full_output = await self._run_agent_in_thread(agent, project, style, input_content, project_name, phase_index)
            full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)

            if phase.split:
                if hasattr(agent, '_chunks') and agent._chunks:
                    self._save_chunked_output(project, output_path, agent._chunks)
                else:
                    self._save_split_output(project, output_path, full_output)
            else:
                project.write_output(output_path, full_output)

            await self.ws.send_message(project_name, {
                "type": "phase_complete", "phase_index": phase_index,
                "phase_name": phase.name, "file_path": output_path,
            })

            if phase.agent == "outline_designer":
                version_result = await self._wait_for_version(project_name)
                version_choice = version_result.get("version", "1")
                if version_choice in ("1", "2"):
                    version_letter = "A" if version_choice == "1" else "B"
                    self._cleanse_outline_version(project, output_path, version_letter)
                    project.mark_phase_done(phase_index)
                    await self.ws.send_message(project_name, {
                        "type": "version_applied", "phase_index": phase_index,
                        "version": version_letter,
                    })
                    return
                elif version_choice == "3":
                    fb = version_result.get("feedback", "")
                    if fb:
                        revised_input = input_content + "\n\n## 修改意见\n请混合版本A和版本B：" + fb
                        full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, phase_index)
                        full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
                        project.write_output(output_path, full_output)
                        project.mark_phase_done(phase_index)
                        await self.ws.send_message(project_name, {
                            "type": "phase_complete", "phase_index": phase_index,
                            "phase_name": phase.name, "file_path": output_path,
                        })
            else:
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
                    if phase.split:
                        if hasattr(agent, '_chunks') and agent._chunks:
                            self._save_chunked_output(project, output_path, agent._chunks)
                        else:
                            self._save_split_output(project, output_path, full_output)
                    else:
                        project.write_output(output_path, full_output)
                    await self.ws.send_message(project_name, {
                        "type": "phase_complete", "phase_index": phase_index,
                        "phase_name": phase.name, "file_path": output_path,
                    })
                    approval = await self.ws.wait_for_approval(project_name, phase_index)
                    iterations += 1

                if approval.get("approved"):
                    project.mark_phase_done(phase_index)
                project.clear_pending_approval()
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
        await self.ws.send_message(project_name, {
            "type": "awaiting_version",
            "phase_index": 0,
            "message": "请选择大纲版本",
        })
        evt = self.ws.pending_approvals.get(project_name)
        if not evt:
            return {"version": "1"}
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
                "04_分镜脚本/": "分镜脚本.md",
                "05_提示词/": "提示词.md",
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

    async def _resume_approval(self, project, project_name, phase_index):
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
            import importlib
            snake_name = phase.agent
            class_name = "".join(word.capitalize() for word in snake_name.split("_"))
            module = importlib.import_module(f"agents.{snake_name}")
            agent_class = getattr(module, class_name)
            agent = agent_class()
            output_content = project.read_output(self._get_output_path(phase)) or ""
            revised_input = output_content + "\n\n## 修改意见\n" + feedback
            from core.style_config import StyleConfig
            style = StyleConfig()
            revised_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, phase_index)
            revised_output = self._reorder_chunked_stream(agent, revised_output, project_name, phase_index)
            project.write_output(self._get_output_path(phase), revised_output)
            await self.ws.send_message(project_name, {
                "type": "phase_complete", "phase_index": phase_index,
                "phase_name": phase.name, "file_path": self._get_output_path(phase),
            })
            approval = await self.ws.wait_for_approval(project_name, phase_index)
            iterations += 1
        if approval.get("approved"):
            project.mark_phase_done(phase_index)
        project.clear_pending_approval()

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
                import importlib
                snake_name = "outline_designer"
                class_name = "OutlineDesigner"
                module = importlib.import_module(f"agents.{snake_name}")
                agent_class = getattr(module, class_name)
                agent = agent_class()
                full_output = await self._run_agent_in_thread(agent, project, style, revised_input, project_name, phase_index)
                full_output = self._reorder_chunked_stream(agent, full_output, project_name, phase_index)
                project.write_output(output_path, full_output)
                project.mark_phase_done(phase_index)
                await self.ws.send_message(project_name, {
                    "type": "phase_complete", "phase_index": phase_index,
                    "phase_name": phase.name, "file_path": output_path,
                })
                return

    def _save_split_output(self, project, output_path, content):
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

    def _save_chunked_output(self, project, output_path, chunks: list):
        base_stem = Path(output_path).stem
        parent = str(Path(output_path).parent)
        full_parts = []
        for chunk in chunks:
            name = chunk.get("name", "")
            output = chunk.get("output", "")
            if not output.strip():
                continue
            full_parts.append(output)
            chunk_fname = f"{base_stem}_{name}.md"
            if parent and parent != ".":
                chunk_fname = f"{parent}/{chunk_fname}"
            project.write_output(chunk_fname, output)
        if full_parts:
            project.write_output(output_path, "\n\n---\n\n".join(full_parts))

    def _reorder_chunked_stream(self, agent, full_output: str, project_name: str, phase_index: int) -> str:
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
            "prompt_engineer": "04_分镜脚本/分镜脚本.md",
        }
        source = input_map.get(phase.agent)
        if source:
            dir_path = project.project_dir / Path(source).parent
            base_name = Path(source).stem
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
