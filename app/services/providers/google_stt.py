"""Google Cloud Speech-to-Text STT 服務"""

import asyncio
from pathlib import Path

from app.services.settings import get_api_key


class GoogleSTT:
    async def transcribe(self, audio_path: Path, language: str, prompt: str, model: str) -> str:
        api_key = get_api_key("google")
        if not api_key:
            raise RuntimeError("未設定 Google API Key，請到設定頁面填入")

        from google.cloud import speech_v1 as speech

        client = speech.SpeechClient()

        # 語言代碼轉換
        lang_map = {
            "zh": "zh-TW",
            "zh-CN": "zh-CN",
            "en": "en-US",
            "ja": "ja-JP",
            "ko": "ko-KR",
        }
        language_code = lang_map.get(language, language)

        def _call():
            audio_content = audio_path.read_bytes()
            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                language_code=language_code,
                model=model,
                enable_automatic_punctuation=True,
            )
            response = client.recognize(config=config, audio=audio)
            texts = [r.alternatives[0].transcript for r in response.results if r.alternatives]
            return " ".join(texts)

        return await asyncio.get_event_loop().run_in_executor(None, _call)
