"""音檔資訊與 ffmpeg 分段處理"""

import json
import subprocess
from pathlib import Path

from app.config import CHUNKS_DIR, CHUNK_DURATION_SECONDS, CHUNK_OVERLAP_SECONDS


async def get_audio_info(path: Path) -> dict:
    """使用 ffprobe 取得音檔資訊"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))
        size = path.stat().st_size

        return {
            "name": path.name,
            "path": str(path),
            "size": size,
            "size_display": _format_size(size),
            "duration": duration,
            "duration_display": _format_duration(duration),
        }
    except Exception:
        size = path.stat().st_size
        return {
            "name": path.name,
            "path": str(path),
            "size": size,
            "size_display": _format_size(size),
            "duration": 0,
            "duration_display": "未知",
        }


def get_duration(path: Path) -> float:
    """取得音檔時長（秒）"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return float(result.stdout.strip())


def split_audio(path: Path) -> list[Path]:
    """用 ffmpeg 將音檔分段，回傳分段檔案路徑列表"""
    duration = get_duration(path)
    chunk_duration = CHUNK_DURATION_SECONDS
    overlap = CHUNK_OVERLAP_SECONDS

    chunks = []
    start = 0
    index = 0

    while start < duration:
        chunk_path = CHUNKS_DIR / f"{path.stem}_chunk_{index:03d}.mp3"
        # 加上 overlap 避免斷句
        actual_duration = chunk_duration + overlap if start + chunk_duration < duration else duration - start

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(path),
                "-ss", str(start),
                "-t", str(actual_duration),
                "-c", "copy",
                str(chunk_path),
            ],
            capture_output=True,
            timeout=60,
        )

        if chunk_path.exists() and chunk_path.stat().st_size > 0:
            chunks.append(chunk_path)

        start += chunk_duration
        index += 1

    return chunks


def cleanup_chunks(chunks: list[Path]) -> None:
    """清除暫存分段檔案"""
    for chunk in chunks:
        try:
            chunk.unlink(missing_ok=True)
        except OSError:
            pass


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "未知"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
