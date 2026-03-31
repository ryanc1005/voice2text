"""OpenAI Whisper / GPT-4o Transcribe STT 服務"""

import asyncio
from pathlib import Path

from app.services.settings import get_api_key


class OpenAISTT:
    async def transcribe(self, audio_path: Path, language: str, prompt: str, model: str) -> str:
        api_key = get_api_key("openai")
        if not api_key:
            raise RuntimeError("未設定 OpenAI API Key，請到設定頁面填入")

        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        # 組合提示詞
        whisper_prompt = "以下是繁體中文的語音內容。" if language == "zh" else ""
        if prompt:
            whisper_prompt = f"{whisper_prompt} {prompt}".strip()

        def _call():
            with open(audio_path, "rb") as f:
                return client.audio.transcriptions.create(
                    model=model,
                    file=f,
                    language=language if language not in ("zh-CN",) else "zh",
                    prompt=whisper_prompt or None,
                    response_format="text",
                )

        # 在 executor 中執行同步 API 呼叫
        result = await asyncio.get_event_loop().run_in_executor(None, _call)
        return result if isinstance(result, str) else result.text
