"""AI 文字優化 — 使用 GPT 潤飾轉錄結果"""

import asyncio
from collections.abc import AsyncGenerator

from app.services.settings import get_api_key


def _build_messages(text: str, prompt: str, language: str) -> tuple[str, list[dict]]:
    """組合 system prompt 和 user messages"""
    lang_name = {"zh": "繁體中文", "zh-CN": "簡體中文", "en": "English", "ja": "日本語", "ko": "한국어"}.get(
        language, "繁體中文"
    )

    system_prompt = f"""你是專業的文字編輯，負責優化語音轉錄的文字。請用{lang_name}輸出。

你的任務：
1. 修正語音辨識可能產生的錯字和語句不通順之處
2. 加入適當的標點符號和段落分隔
3. 保持原始語意不變，不要添加或刪除內容
4. 如果有專業術語，根據上下文修正為正確用詞
5. 輸出格式為 Markdown

注意：
- 保持說話者的原始語氣和風格
- 不要過度修飾或改寫
- 維持 Markdown 格式的標題和結構"""

    user_content = text
    if prompt:
        user_content = f"活動背景資訊：{prompt}\n\n---\n\n以下是需要優化的轉錄文字：\n\n{text}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    return system_prompt, messages


async def refine_text(text: str, prompt: str = "", language: str = "zh") -> str:
    """使用 GPT 優化轉錄文字（一次性回傳）"""
    api_key = get_api_key("openai")
    if not api_key:
        raise RuntimeError("AI 優化需要 OpenAI API Key，請到設定頁面填入")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    _, messages = _build_messages(text, prompt, language)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=16000,
    )
    return response.choices[0].message.content


async def refine_text_stream(text: str, prompt: str = "", language: str = "zh") -> AsyncGenerator[str, None]:
    """使用 GPT 優化轉錄文字（async streaming 逐字回傳）"""
    api_key = get_api_key("openai")
    if not api_key:
        raise RuntimeError("AI 優化需要 OpenAI API Key，請到設定頁面填入")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    _, messages = _build_messages(text, prompt, language)

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=16000,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
