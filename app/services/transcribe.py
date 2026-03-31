"""多模型 STT 統一介面與轉錄協調"""

from pathlib import Path

from app.services.providers.openai_stt import OpenAISTT
from app.services.providers.google_stt import GoogleSTT
from app.services.providers.elevenlabs_stt import ElevenLabsSTT


class STTProvider:
    """STT 服務商抽象基底"""

    async def transcribe(self, audio_path: Path, language: str, prompt: str, model: str) -> str:
        raise NotImplementedError


def get_provider(provider_name: str) -> STTProvider:
    """根據名稱取得對應的 STT provider"""
    providers = {
        "openai": OpenAISTT,
        "google": GoogleSTT,
        "elevenlabs": ElevenLabsSTT,
    }
    cls = providers.get(provider_name)
    if not cls:
        raise ValueError(f"不支援的服務商：{provider_name}")
    return cls()


def merge_segments(segments: list[str]) -> str:
    """合併分段轉錄結果，處理重疊區域去重"""
    if not segments:
        return ""
    if len(segments) == 1:
        return segments[0]

    result = segments[0]
    for i in range(1, len(segments)):
        next_text = segments[i]
        # 嘗試找重疊文字並去重
        overlap = _find_overlap(result, next_text)
        if overlap:
            next_text = next_text[len(overlap):]
        result += next_text

    return result


def _find_overlap(prev: str, next_: str, max_check: int = 100) -> str:
    """找出前段結尾與後段開頭的重疊文字"""
    # 取前段最後 max_check 字元與後段開頭比對
    tail = prev[-max_check:] if len(prev) > max_check else prev

    best = ""
    for length in range(5, min(len(tail), len(next_)) + 1):
        if tail.endswith(next_[:length]):
            best = next_[:length]

    return best
