"""ElevenLabs Scribe STT 服務"""

import asyncio
from pathlib import Path

from app.services.settings import get_api_key


class ElevenLabsSTT:
    async def transcribe(self, audio_path: Path, language: str, prompt: str, model: str) -> str:
        api_key = get_api_key("elevenlabs")
        if not api_key:
            raise RuntimeError("未設定 ElevenLabs API Key，請到設定頁面填入")

        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)

        # 語言代碼轉換
        lang_map = {
            "zh": "zho",
            "zh-CN": "zho",
            "en": "eng",
            "ja": "jpn",
            "ko": "kor",
        }
        language_code = lang_map.get(language, language)

        def _call():
            result = client.speech_to_text.convert(
                file=open(audio_path, "rb"),
                model_id=model,
                language_code=language_code,
            )
            # ElevenLabs 回傳結構中的文字
            if hasattr(result, "text"):
                return result.text
            return str(result)

        return await asyncio.get_event_loop().run_in_executor(None, _call)
