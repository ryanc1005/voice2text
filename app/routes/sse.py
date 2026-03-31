"""Server-Sent Events 進度串流"""

import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.services.tasks import TaskManager

router = APIRouter()
task_manager = TaskManager()


@router.get("/tasks/{task_id}/progress")
async def task_progress(task_id: str):
    """SSE 串流任務進度"""

    async def event_generator():
        task = task_manager.get_task(task_id)
        if not task:
            yield {"event": "error", "data": json.dumps({"message": "任務不存在"})}
            return

        # 如果任務已完成/失敗，直接回傳最終狀態
        if task["status"] == "completed":
            yield {"event": "done", "data": json.dumps({"progress": 100, "message": "轉錄完成"})}
            return
        if task["status"] == "failed":
            yield {"event": "error", "data": json.dumps({"message": f"轉錄失敗：{task.get('error', '未知錯誤')}"})}
            return

        # 任務進行中：建立持久 queue，整個 SSE 連線期間共用
        queue = asyncio.Queue()
        task_manager.subscribe(task_id, queue)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    # 心跳：檢查任務是否已完成（防止漏接事件）
                    task = task_manager.get_task(task_id)
                    if task and task["status"] == "completed":
                        yield {"event": "done", "data": json.dumps({"progress": 100, "message": "轉錄完成"})}
                        break
                    elif task and task["status"] == "failed":
                        yield {"event": "error", "data": json.dumps({"message": f"轉錄失敗：{task.get('error', '未知錯誤')}"})}
                        break
                    # 仍在處理中，送心跳
                    yield {"event": "heartbeat", "data": json.dumps({"status": task.get("status"), "progress": task.get("progress", 0)})}
                    continue

                yield {"event": event["type"], "data": json.dumps(event["data"])}
                if event["type"] in ("done", "error"):
                    break
        finally:
            task_manager.unsubscribe(task_id, queue)

    return EventSourceResponse(event_generator())
