import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..ws_manager import ConnectionManager
from ..async_orch import AsyncOrchestrator

router = APIRouter()
manager = ConnectionManager()
logger = logging.getLogger("uvicorn")


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
            logger.info(f"[WS] {project_name} 收到 action={action} running={manager.is_running(project_name)}")
            if action in ("start", "continue", "redo_phase") and manager.is_running(project_name):
                logger.info(f"[WS] {project_name} 拒绝重复启动，发送 reconnect_sync")
                await manager._send_reconnect_status(project_name)
                continue

            if action == "start":
                logger.info(f"[WS] {project_name} 启动 run")
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
                logger.info(f"[WS] {project_name} 启动 continue_run")
                task = asyncio.create_task(
                    orch.continue_run(project_name, msg.get("style", {}))
                )
                manager.register_task(project_name, task)
            else:
                manager.handle_client_message(project_name, msg)

    except WebSocketDisconnect:
        logger.info(f"[WS] {project_name} 断开")
        manager.disconnect(project_name, websocket)
    except Exception as e:
        logger.error(f"[WS] {project_name} 错误: {e}")
        try:
            await manager.send_message(project_name, {
                "type": "error", "message": str(e),
            })
        except Exception:
            pass
        manager.disconnect(project_name, websocket)
