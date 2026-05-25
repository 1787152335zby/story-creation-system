import json
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
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
        self.orchestrators: Dict[str, 'AsyncOrchestrator'] = {}

    def set_orchestrator(self, project_name: str, orch: 'AsyncOrchestrator'):
        self.orchestrators[project_name] = orch

    async def connect(self, project_name: str, websocket: WebSocket):
        # 保留已在后台运行的任务，不断开
        await websocket.accept()

        # 如果有后台任务在运行，先释放旧的等待事件（避免 orchestrator 永久阻塞）
        # 让 wait_for_xxx 拿到默认结果后继续执行
        task = self.running_tasks.get(project_name)
        if task and not task.done():
            old_evt = self.pending_approvals.get(project_name)
            if old_evt:
                old_evt.set()
            self.approval_results.pop(project_name, None)
            old_confirm = self.pending_confirms.get(project_name)
            if old_confirm:
                old_confirm.set()
            self.confirm_results.pop(project_name, None)
            old_ep = self.pending_episode_events.get(project_name)
            if old_ep:
                old_ep.set()
            self.episode_results.pop(project_name, None)

        self.active_connections[project_name] = websocket
        self.pending_approvals[project_name] = asyncio.Event()
        self.approval_results[project_name] = None
        from core.project_manager import ProjectManager
        try:
            project = ProjectManager(project_name)
            self.auto_approve_flags[project_name] = project.auto_approve
        except Exception:
            self.auto_approve_flags[project_name] = False

        # 如果有后台任务在运行，通知前端当前状态
        if task and not task.done():
            asyncio.ensure_future(self._send_reconnect_status(project_name))

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
        """重新连接时告知前端当前运行状态"""
        await self.send_message(project_name, {
            "type": "reconnect_status",
            "message": "后台任务正在运行中...",
        })

    def disconnect(self, project_name: str):
        self.active_connections.pop(project_name, None)
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
        # 自动审核模式下，断开不取消任务，后台继续生成
        if not self.auto_approve_flags.get(project_name, False):
            self._cancel_task(project_name)

    async def send_message(self, project_name: str, message: dict):
        ws = self.active_connections.get(project_name)
        if ws:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                self.active_connections.pop(project_name, None)
                # 释放等待事件，避免 orchestrator 永久阻塞
                evt = self.pending_approvals.get(project_name)
                if evt:
                    evt.set()
                confirm_evt = self.pending_confirms.get(project_name)
                if confirm_evt:
                    confirm_evt.set()
                ep_evt = self.pending_episode_events.get(project_name)
                if ep_evt:
                    ep_evt.set()

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
