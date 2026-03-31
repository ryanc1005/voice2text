"""REST API 端點"""

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.config import LANGUAGES, PROVIDERS, SOURCES_DIR
from app.services.audio import get_audio_info
from app.services.settings import get_settings, save_settings
from app.services.tasks import TaskManager

router = APIRouter()
task_manager = TaskManager()

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}


# === 檔案相關 ===

@router.get("/files")
async def list_files():
    """列出 sources/ 中的音檔，含任務狀態"""
    files = []
    for ext in ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A", "*.flac", "*.FLAC"):
        for f in SOURCES_DIR.glob(ext):
            info = await get_audio_info(f)
            # 附加任務狀態
            active = task_manager.find_active_task(f.name)
            completed = task_manager.find_completed_task(f.name)
            if active:
                info["task_status"] = active["status"]
                info["task_id"] = active["id"]
            elif completed:
                info["task_status"] = "completed"
                info["task_id"] = completed["id"]
            else:
                info["task_status"] = None
                info["task_id"] = None
            files.append(info)
    files.sort(key=lambda x: x["name"])
    return files


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """上傳音檔到 sources/"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供檔案")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的檔案格式：{ext}。支援格式：{', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
        )

    dest = SOURCES_DIR / file.filename

    # 如果同名檔案已存在，加上序號
    if dest.exists():
        stem = dest.stem
        i = 1
        while dest.exists():
            dest = SOURCES_DIR / f"{stem}_{i}{ext}"
            i += 1

    content = await file.read()
    dest.write_bytes(content)

    info = await get_audio_info(dest)
    info["task_status"] = None
    info["task_id"] = None
    return info


# === 服務商與模型 ===

@router.get("/providers")
async def list_providers():
    """取得可用的服務商、模型與語言清單"""
    return {
        "providers": PROVIDERS,
        "languages": LANGUAGES,
    }


# === 設定 ===

class SettingsUpdate(BaseModel):
    openai_api_key: str = ""
    google_api_key: str = ""
    google_credentials: str = ""
    elevenlabs_api_key: str = ""
    default_provider: str = "openai"
    default_model: str = "whisper-1"
    default_language: str = "zh"


@router.get("/settings")
async def get_app_settings():
    """取得應用設定"""
    return get_settings()


@router.put("/settings")
async def update_settings(data: SettingsUpdate):
    """更新應用設定"""
    save_settings(data.model_dump())
    return {"status": "ok"}


# === 任務 ===

class TaskCreate(BaseModel):
    filename: str
    provider: str = "openai"
    model: str = "whisper-1"
    language: str = "zh"
    prompt: str = ""
    force: bool = False  # 強制重新轉錄（即使已有完成的任務）


@router.post("/tasks")
async def create_task(data: TaskCreate):
    """建立轉錄任務"""
    filepath = SOURCES_DIR / data.filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="檔案不存在")

    # 防呆：檢查是否有相同檔案正在處理中或等待中
    existing = task_manager.find_active_task(data.filename)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"此檔案已有進行中的任務（ID: {existing['id']}），請等待完成或取消後再試",
        )

    # 防呆：檢查是否已有相同檔案的完成任務
    completed = task_manager.find_completed_task(data.filename)
    if completed and not data.force:
        raise HTTPException(
            status_code=409,
            detail=f"此檔案已有轉錄完成的任務（ID: {completed['id']}），可直接前往編輯。如需重新轉錄，請勾選「強制重新轉錄」",
        )

    task_id = str(uuid.uuid4())[:8]
    task = task_manager.create_task(
        task_id=task_id,
        filename=data.filename,
        provider=data.provider,
        model=data.model,
        language=data.language,
        prompt=data.prompt,
    )

    # 啟動背景轉錄
    asyncio.create_task(task_manager.run_task(task_id))

    return task


@router.get("/tasks")
async def list_tasks():
    """列出所有任務"""
    return task_manager.list_tasks()


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """取得任務詳情"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    return task


@router.put("/tasks/{task_id}/content")
async def save_content(task_id: str, data: dict):
    """儲存編輯後的 Markdown 內容"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    task_manager.update_content(task_id, data.get("content", ""))
    return {"status": "ok"}


@router.post("/tasks/{task_id}/refine")
async def refine_content(task_id: str):
    """AI 優化文字（SSE streaming）"""
    import json
    from sse_starlette.sse import EventSourceResponse
    from app.services.refine import refine_text_stream

    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    if not task.get("content"):
        raise HTTPException(status_code=400, detail="無內容可優化")

    text = task["content"]
    prompt = task.get("prompt", "")
    language = task.get("language", "zh")

    # 估算處理時間（粗估：每 500 字約 10 秒）
    char_count = len(text)
    estimated_seconds = max(5, int(char_count / 50))

    async def event_generator():
        yield {
            "event": "start",
            "data": json.dumps({
                "char_count": char_count,
                "estimated_seconds": estimated_seconds,
                "message": f"開始 AI 優化（約 {char_count} 字，預估 {estimated_seconds} 秒）...",
            }),
        }

        full_content = ""
        chunk_count = 0
        try:
            async for chunk in refine_text_stream(text, prompt, language):
                full_content += chunk
                chunk_count += 1
                # 每收到一段就送到前端（控制頻率，每 3 個 chunk 送一次）
                if chunk_count % 3 == 0:
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"text": chunk, "full_length": len(full_content)}),
                    }
                else:
                    yield {
                        "event": "chunk",
                        "data": json.dumps({"text": chunk}),
                    }

            # 儲存最終結果
            task_manager.update_content(task_id, full_content)

            yield {
                "event": "done",
                "data": json.dumps({"content": full_content}),
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }

    return EventSourceResponse(event_generator())


@router.get("/tasks/{task_id}/export")
async def export_task(task_id: str):
    """匯出 .md 檔案"""
    from fastapi.responses import Response

    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")

    content = task.get("content", "")
    filename = task.get("filename", "output").rsplit(".", 1)[0] + ".md"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
