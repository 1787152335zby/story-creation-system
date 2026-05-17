import json
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.pending_approvals: Dict[str, asyncio.Event] = {}
        self.approval_results: Dict[str, Optional[dict]] = {}
        self.redo_phase_idx: Dict[str, Optional[int]] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, project_name: str, websocket: WebSocket):
        self._cancel_task(project_name)
        await websocket.accept()
        self.active_connections[project_name] = websocket
        self.pending_approvals[project_name] = asyncio.Event()
        self.approval_results[project_name] = None

    def _cancel_task(self, project_name: str):
        old_task = self.running_tasks.pop(project_name, None)
        if old_task and not old_task.done():
            old_task.cancel()

    def register_task(self, project_name: str, task: asyncio.Task):
        self._cancel_task(project_name)
        self.running_tasks[project_name] = task

    def disconnect(self, project_name: str):
        self.active_connections.pop(project_name, None)
        evt = self.pending_approvals.pop(project_name, None)
        if evt:
            evt.set()
        self.approval_results.pop(project_name, None)

    async def send_message(self, project_name: str, message: dict):
        ws = self.active_connections.get(project_name)
        if ws:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                self.disconnect(project_name)

    async def wait_for_approval(self, project_name: str, phase_index: int) -> dict:
        evt = self.pending_approvals.get(project_name)
        if not evt:
            return {"approved": True, "feedback": ""}
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
            self.approval_results[project_name] = {"confirmed": True, "approved": False, "feedback": ""}
            evt = self.pending_approvals.get(project_name)
            if evt:
                evt.set()
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
