import json
import asyncio
import re
from pathlib import Path
from typing import Dict, Optional
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, list] = {}
        self.pending_approvals: Dict[str, asyncio.Event] = {}
        self.approval_results: Dict[str, Optional[dict]] = {}
        self.pending_confirms: Dict[str, asyncio.Event] = {}
        self.confirm_results: Dict[str, Optional[dict]] = {}
        self.redo_phase_idx: Dict[str, Optional[int]] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.auto_approve_flags: Dict[str, bool] = {}
        self.chunked_phases: Dict[str, set[int]] = {}
        self.pending_episode_events: Dict[str, asyncio.Event] = {}
        self.episode_results: Dict[str, Optional[dict]] = {}
        self.current_episode_info: Dict[str, Optional[dict]] = {}
        self.pending_duration_events: Dict[str, asyncio.Event] = {}
        self.duration_results: Dict[str, Optional[dict]] = {}
        self.orchestrators: Dict[str, 'AsyncOrchestrator'] = {}

    def set_orchestrator(self, project_name: str, orch: 'AsyncOrchestrator'):
        self.orchestrators[project_name] = orch

    async def connect(self, project_name: str, websocket: WebSocket):
        await websocket.accept()

        if project_name not in self.active_connections:
            self.active_connections[project_name] = []
        self.active_connections[project_name].append(websocket)

        task = self.running_tasks.get(project_name)
        is_reconnect = task is not None and not task.done()

        if not is_reconnect:
            self.pending_approvals[project_name] = asyncio.Event()
            self.approval_results[project_name] = None

        from core.project_manager import ProjectManager
        try:
            project = ProjectManager(project_name)
            self.auto_approve_flags[project_name] = project.auto_approve
        except Exception:
            self.auto_approve_flags[project_name] = False

        if is_reconnect:
            asyncio.ensure_future(self._send_reconnect_status(project_name))
            # 重连时如果有方向卡内容但版本未选择，强制推送版本选择界面
            asyncio.ensure_future(self._resend_version_selection_if_pending(project_name))

        await self._send_phase_chunks(project_name)

    def _cancel_task(self, project_name: str):
        old_task = self.running_tasks.pop(project_name, None)
        if old_task and not old_task.done():
            old_task.cancel()

    def register_task(self, project_name: str, task: asyncio.Task):
        # 如果已有后台任务在运行，不覆盖
        existing = self.running_tasks.get(project_name)
        if existing and not existing.done():
            return
        self._cancel_task(project_name)
        self.running_tasks[project_name] = task

    def is_running(self, project_name: str) -> bool:
        task = self.running_tasks.get(project_name)
        return task is not None and not task.done()

    def cancel_project_task(self, project_name: str):
        """外部 HTTP 接口调用删除/重建时清理后台任务"""
        self._cancel_task(project_name)

    async def _send_reconnect_status(self, project_name: str):
        """重新连接时告知前端当前运行状态、已完成阶段名及内容"""
        phase_index = -1
        phase_name = ""
        pending_episode = None
        completed_phases = []
        try:
            from core.project_manager import ProjectManager
            project = ProjectManager(project_name)
            phases = project.config.get("phases", [])
            pending_episode = project.pending_episode
            PHASE_DIRS = ['01_故事大纲', '02_完整剧情', '03_完整剧本', '04_角色场景', '05_分镜脚本', '06_生图需求']
            PHASE_OUTPUTS = ['故事大纲.md', '完整剧情.md', '完整剧本.md', '角色场景.md', '分镜脚本.md', '分析报告.md']
            for i, p in enumerate(phases):
                if p.get("done", False) and i < len(PHASE_DIRS):
                    out_path = f"{PHASE_DIRS[i]}/{PHASE_OUTPUTS[i]}"
                    content = project.read_output(out_path) or ""
                    completed_phases.append({
                        "phase_index": i,
                        "phase_name": p.get("name", ""),
                        "content": content[:2000],
                        "truncated": len(content) > 2000,
                    })
                elif not p.get("done", False):
                    if phase_index < 0:
                        phase_index = i
                        phase_name = p.get("name", "")
            if phase_index < 0 and phases:
                phase_index = len(phases) - 1
                phase_name = phases[-1].get("name", "")
        except Exception:
            pass
        await self.send_message(project_name, {
            "type": "reconnect_sync",
            "phase_index": phase_index,
            "phase_name": phase_name,
            "running": True,
            "pending_episode": pending_episode,
            "completed_phases": completed_phases,
        })

    async def _send_phase_chunks(self, project_name: str):
        try:
            loop = asyncio.get_event_loop()
            chunks_data = await loop.run_in_executor(None, self._scan_chunks_sync, project_name)
            if chunks_data:
                await self.send_message(project_name, {"type": "phase_chunks", "chunks": chunks_data})
        except Exception:
            pass

    @staticmethod
    def _scan_chunks_sync(project_name: str) -> dict:
        PHASE_DIRS = ['01_故事大纲', '02_完整剧情', '03_完整剧本', '04_角色场景', '05_分镜脚本', '06_生图需求']
        from core.project_manager import ProjectManager
        project = ProjectManager(project_name)
        chunks_data = {}
        for idx, dir_name in enumerate(PHASE_DIRS):
            phase_path = project.project_dir / dir_name
            if not phase_path.exists():
                continue
            subdirs = sorted(
                [d for d in phase_path.iterdir() if d.is_dir()],
                key=lambda sd: (0, int(re.findall(r'\d+', sd.name)[0])) if re.findall(r'\d+', sd.name) else (1, sd.name)
            )
            if len(subdirs) <= 1:
                continue
            chunk_list = []
            for ci, sd in enumerate(subdirs):
                md_files = list(sd.glob("*.md"))
                if md_files:
                    chunk_list.append({
                        "name": sd.name,
                        "index": ci,
                        "total": len(subdirs),
                        "filePath": f"{dir_name}/{sd.name}/{md_files[0].name}",
                    })
            if chunk_list:
                chunks_data[str(idx)] = chunk_list
        return chunks_data

    def disconnect(self, project_name: str, websocket: WebSocket = None):
        conns = self.active_connections.get(project_name, [])
        if websocket and websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(project_name, None)

        if self.active_connections.get(project_name):
            return

        # 断开时清理 pending_episode，避免重连后死循环
        from core.project_manager import ProjectManager
        try:
            project = ProjectManager(project_name)
            if project.pending_episode:
                project.clear_pending_episode()
        except Exception:
            pass

        # 如果任务处于等待用户交互状态（版本选择/审核），不杀任务
        # 只释放事件让 wait 返回默认值，任务自然结束
        is_waiting_for_user = False
        if project_name in self.pending_approvals:
            is_waiting_for_user = True
        if project_name in self.pending_confirms:
            is_waiting_for_user = True
        if project_name in self.pending_episode_events:
            is_waiting_for_user = True

        evt = self.pending_approvals.pop(project_name, None)
        if evt:
            evt.set()
        self.approval_results.pop(project_name, None)
        confirm_evt = self.pending_confirms.pop(project_name, None)
        if confirm_evt:
            confirm_evt.set()
        self.confirm_results.pop(project_name, None)
        ep_evt = self.pending_episode_events.pop(project_name, None)
        if ep_evt:
            ep_evt.set()
        self.episode_results.pop(project_name, None)
        self.current_episode_info.pop(project_name, None)

        # 任务继续在后台运行，不因 WS 断开而取消
        # client 重连后可 resume 查看进度

    async def send_message(self, project_name: str, message: dict):
        conns = list(self.active_connections.get(project_name, []))
        dead = []
        for ws in conns:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(project_name, ws)

    async def wait_for_approval(self, project_name: str, phase_index: int) -> dict:
        evt = self.pending_approvals.get(project_name)
        if not evt:
            return {"approved": True, "feedback": ""}

        chunked = self.chunked_phases.get(project_name, set())
        if self.auto_approve_flags.get(project_name, False) and phase_index not in chunked:
            return {"approved": True, "feedback": "", "auto": True}

        evt.clear()

        await self.send_message(project_name, {
            "type": "awaiting_approval",
            "phase_index": phase_index,
            "message": "请审核生成内容",
        })

        try:
            await evt.wait()
        except asyncio.CancelledError:
            raise

        result = self.approval_results.get(project_name, {"approved": True, "feedback": ""})
        self.approval_results[project_name] = None
        return result

    async def wait_for_proceed(self, project_name: str) -> bool:
        """等待用户点击「继续进行下一步」(仅在 confirm 之后调用)"""
        evt = asyncio.Event()
        self.pending_confirms[project_name] = evt

        await self.send_message(project_name, {
            "type": "waiting_for_proceed",
            "message": "已确认完成，等待继续下一步",
        })

        try:
            await evt.wait()
        except asyncio.CancelledError:
            raise

        result = self.confirm_results.get(project_name, {"proceed": False})
        self.confirm_results[project_name] = None
        self.pending_confirms.pop(project_name, None)
        return result.get("proceed", False)

    async def wait_for_episode_approval(self, project_name: str, phase_index: int, chunk_name: str, chunk_index: int, total_chunks: int) -> dict:
        """等待用户对某一集做出审核决定"""
        if self.auto_approve_flags.get(project_name, False):
            return {"action": "approve", "feedback": "", "auto": True}

        evt = asyncio.Event()
        self.pending_episode_events[project_name] = evt
        self.episode_results[project_name] = None
        self.current_episode_info[project_name] = {
            "phase_index": phase_index,
            "chunk_name": chunk_name,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
        }

        await self.send_message(project_name, {
            "type": "episode_complete",
            "phase_index": phase_index,
            "chunk_name": chunk_name,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
        })

        try:
            await evt.wait()
        except asyncio.CancelledError:
            raise

        result = self.episode_results.get(project_name, {"action": "approve", "feedback": ""})
        self.episode_results[project_name] = None
        self.pending_episode_events.pop(project_name, None)
        self.current_episode_info.pop(project_name, None)
        return result

    async def wait_for_duration_confirm(self, project_name: str) -> dict | None:
        evt = asyncio.Event()
        self.pending_duration_events[project_name] = evt
        self.duration_results[project_name] = None
        try:
            await asyncio.wait_for(evt.wait(), timeout=300)
        except asyncio.TimeoutError:
            self.pending_duration_events.pop(project_name, None)
            return None
        result = self.duration_results.get(project_name)
        self.duration_results.pop(project_name, None)
        self.pending_duration_events.pop(project_name, None)
        return result

    async def _resend_version_selection_if_pending(self, project_name: str):
        """重连时检测是否有未完成的方向卡选择，强制推送给前端"""
        try:
            from core.project_manager import ProjectManager
            project = ProjectManager(project_name)
            phases = project.config.get("phases", [])
            if not phases:
                return
            outline_done = False
            for p in phases:
                if p.get("name") == "story_outline" and p.get("done"):
                    outline_done = True
                    break
            if outline_done:
                return
            content = project.read_output("01_故事大纲/故事大纲.md") or ""
            if len(content) < 100:
                return
            if "版本A" not in content and "版本B" not in content:
                return
            await self.send_message(project_name, {
                "type": "stream",
                "phase_index": 0,
                "chunk": content,
            })
            await asyncio.sleep(0.3)
            await self.send_message(project_name, {
                "type": "awaiting_version",
                "phase_index": 0,
                "message": "请选择大纲版本",
            })
        except Exception:
            pass

    def handle_client_message(self, project_name: str, data: dict):
        action = data.get("action", "")
        if action in ("approve", "revise", "reject"):
            self.approval_results[project_name] = {
                "approved": action == "approve",
                "feedback": data.get("feedback", ""),
                "reason": data.get("reason", ""),
            }
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "duration_confirm":
            self.duration_results[project_name] = {
                "count": int(data.get("count", 0)),
                "duration": data.get("duration", ""),
            }
            evt = self.pending_duration_events.get(project_name)
            if evt:
                evt.set()
        elif action == "confirm_phase":
            self.approval_results[project_name] = {"approved": True, "confirmed": True, "feedback": ""}
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "proceed":
            self.confirm_results[project_name] = {"proceed": True}
            evt = self.pending_confirms.get(project_name)
            if evt:
                evt.set()
            from core.project_manager import ProjectManager
            project = ProjectManager(project_name)
            if project.pending_episode is not None:
                project.config["_proceed_resume"] = True
                project.save_config()
        elif action == "skip":
            self.approval_results[project_name] = {"approved": True, "feedback": "", "skip": True}
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "platform":
            self.approval_results[project_name] = {"platform": data.get("platform", "Seedance 2.0")}
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "version_select":
            self.approval_results[project_name] = {
                "version": data.get("version", ""),
                "feedback": data.get("feedback", ""),
            }
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "redo_phase":
            self.redo_phase_idx[project_name] = data.get("phase_index")
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
        elif action == "set_auto_approve":
            self.auto_approve_flags[project_name] = data.get("value", False)
        elif action in ("episode_approve", "episode_confirm", "episode_revise"):
            self.episode_results[project_name] = {
                "action": action.replace("episode_", ""),
                "feedback": data.get("feedback", ""),
            }
            evt = self.pending_episode_events.get(project_name)
            if evt:
                evt.set()
