"""非同步任務管理"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.config import PROVIDERS, SOURCES_DIR, TASKS_DIR


class TaskManager:
    """管理轉錄任務的建立、執行與狀態追蹤"""

    # 類別層級共享狀態（單一進程）
    _tasks: dict[str, dict] = {}
    _event_queues: dict[str, list[asyncio.Queue]] = {}

    def create_task(
        self,
        task_id: str,
        filename: str,
        provider: str,
        model: str,
        language: str,
        prompt: str,
    ) -> dict:
        task = {
            "id": task_id,
            "filename": filename,
            "provider": provider,
            "model": model,
            "language": language,
            "prompt": prompt,
            "status": "pending",
            "progress": 0,
            "content": "",
            "chunk_results": {},
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._tasks[task_id] = task
        self._save_task(task_id)
        return task

    def get_task(self, task_id: str) -> dict | None:
        if task_id in self._tasks:
            return self._tasks[task_id]
        # 嘗試從檔案載入
        task_file = TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            task = json.loads(task_file.read_text(encoding="utf-8"))
            self._tasks[task_id] = task
            return task
        return None

    def list_tasks(self) -> list[dict]:
        # 載入所有任務檔案
        for f in TASKS_DIR.glob("*.json"):
            tid = f.stem
            if tid not in self._tasks:
                try:
                    self._tasks[tid] = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
        tasks = sorted(self._tasks.values(), key=lambda t: t.get("created_at", ""), reverse=True)
        return tasks

    def find_active_task(self, filename: str) -> dict | None:
        """查找指定檔案是否有正在處理中或等待中的任務"""
        self.list_tasks()  # 確保載入所有任務
        for task in self._tasks.values():
            if task["filename"] == filename and task["status"] in ("pending", "processing"):
                return task
        return None

    def find_completed_task(self, filename: str) -> dict | None:
        """查找指定檔案最近一筆完成的任務"""
        self.list_tasks()
        completed = [
            t for t in self._tasks.values()
            if t["filename"] == filename and t["status"] == "completed"
        ]
        if not completed:
            return None
        return max(completed, key=lambda t: t.get("created_at", ""))

    def update_content(self, task_id: str, content: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task["content"] = content
            task["updated_at"] = datetime.now().isoformat()
            self._save_task(task_id)

    async def run_task(self, task_id: str) -> None:
        """執行轉錄任務（背景協程）"""
        task = self._tasks.get(task_id)
        if not task:
            return

        task["status"] = "processing"
        task["progress"] = 0
        self._save_task(task_id)
        await self._emit(task_id, "progress", {"progress": 0, "message": "開始處理..."})

        try:
            filepath = SOURCES_DIR / task["filename"]
            provider_name = task["provider"]
            model = task["model"]
            language = task["language"]
            prompt = task["prompt"]

            from app.services.audio import cleanup_chunks, split_audio
            from app.services.transcribe import get_provider, merge_segments

            provider = get_provider(provider_name)
            max_size = PROVIDERS.get(provider_name, {}).get("max_file_size")

            file_size = filepath.stat().st_size

            # 判斷是否需要分段
            if max_size and file_size > max_size * 0.95:
                await self._emit(task_id, "progress", {"progress": 5, "message": "正在分段音檔..."})
                chunks = split_audio(filepath)

                if not chunks:
                    raise RuntimeError("音檔分段失敗")

                segments = []
                for i, chunk_path in enumerate(chunks):
                    # 跳過已完成的分段（斷點續傳）
                    chunk_key = str(i)
                    if chunk_key in task.get("chunk_results", {}):
                        segments.append(task["chunk_results"][chunk_key])
                        continue

                    progress = int(10 + (80 * i / len(chunks)))
                    await self._emit(task_id, "chunk_start", {
                        "progress": progress,
                        "message": f"轉錄分段 {i + 1}/{len(chunks)}...",
                        "chunk": i + 1,
                        "total_chunks": len(chunks),
                    })

                    text = await provider.transcribe(
                        audio_path=chunk_path,
                        language=language,
                        prompt=prompt,
                        model=model,
                    )
                    segments.append(text)

                    # 儲存分段結果（斷點續傳）
                    task["chunk_results"][chunk_key] = text
                    self._save_task(task_id)

                cleanup_chunks(chunks)
                full_text = merge_segments(segments)
            else:
                # 小檔案直接轉錄
                duration_info = ""
                if file_size < 1024:
                    # 極短檔案警告
                    await self._emit(task_id, "progress", {"progress": 5, "message": "檔案極小，嘗試轉錄..."})

                await self._emit(task_id, "progress", {"progress": 10, "message": "正在轉錄..."})
                full_text = await provider.transcribe(
                    audio_path=filepath,
                    language=language,
                    prompt=prompt,
                    model=model,
                )

            # 格式化為 Markdown
            await self._emit(task_id, "progress", {"progress": 95, "message": "格式化中..."})
            from app.services.formatter import format_as_markdown
            markdown = format_as_markdown(task["filename"], full_text, prompt)

            task["content"] = markdown
            task["status"] = "completed"
            task["progress"] = 100
            task["updated_at"] = datetime.now().isoformat()
            self._save_task(task_id)

            await self._emit(task_id, "done", {"progress": 100, "message": "完成！"})

        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            task["updated_at"] = datetime.now().isoformat()
            self._save_task(task_id)
            await self._emit(task_id, "error", {"message": f"轉錄失敗：{e}"})

    def subscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """訂閱任務事件（SSE 連線建立時呼叫）"""
        if task_id not in self._event_queues:
            self._event_queues[task_id] = []
        self._event_queues[task_id].append(queue)

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """取消訂閱（SSE 連線結束時呼叫）"""
        if task_id in self._event_queues:
            try:
                self._event_queues[task_id].remove(queue)
            except ValueError:
                pass
            if not self._event_queues[task_id]:
                del self._event_queues[task_id]

    async def _emit(self, task_id: str, event_type: str, data: dict) -> None:
        """發送事件到所有監聽者"""
        if task_id in self._event_queues:
            for queue in self._event_queues[task_id]:
                await queue.put({"type": event_type, "data": data})

    def _save_task(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task_file = TASKS_DIR / f"{task_id}.json"
            task_file.write_text(
                json.dumps(task, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
