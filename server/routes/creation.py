import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..ws_manager import ConnectionManager
from ..async_orch import AsyncOrchestrator

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/create/{project_name}")
async def websocket_create(websocket: WebSocket, project_name: str):
    await manager.connect(project_name, websocket)
    orch = AsyncOrchestrator(manager)
    manager.set_orchestrator(project_name, orch)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            action = msg.get("action", "")
            if action in ("start", "continue", "redo_phase") and manager.is_running(project_name):
                # 已有后台任务运行中，不重复启动
                await manager.send_message(project_name, {
                    "type": "reconnect_status",
                    "message": "任务正在后台运行中，请稍候...",
                })
                continue

            if action == "start":
                task = asyncio.create_task(
                    orch.run(project_name, msg.get("style", {}))
                )
                manager.register_task(project_name, task)
            elif action == "redo_phase":
                phase_idx = msg.get("phase_index", 0)
                feedback = msg.get("feedback", "")
                task = asyncio.create_task(
                    orch.redo_phase(project_name, msg.get("style", {}), phase_idx, feedback)
                )
                manager.register_task(project_name, task)
            elif action == "continue":
                task = asyncio.create_task(
                    orch.continue_run(project_name, msg.get("style", {}))
                )
                manager.register_task(project_name, task)
            else:
                manager.handle_client_message(project_name, msg)

    except WebSocketDisconnect:
        manager.disconnect(project_name)
    except Exception as e:
        try:
            await manager.send_message(project_name, {
                "type": "error", "message": str(e),
            })
        except Exception:
            pass
        manager.disconnect(project_name)
