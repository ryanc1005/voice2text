"""API Key 與應用設定讀寫"""

import json

from app.config import (
    DEFAULT_ELEVENLABS_API_KEY,
    DEFAULT_GOOGLE_API_KEY,
    DEFAULT_GOOGLE_CREDENTIALS,
    DEFAULT_OPENAI_API_KEY,
    SETTINGS_FILE,
)

_DEFAULT_SETTINGS = {
    "openai_api_key": "",
    "google_api_key": "",
    "google_credentials": "",
    "elevenlabs_api_key": "",
    "default_provider": "openai",
    "default_model": "whisper-1",
    "default_language": "zh",
}


def get_settings() -> dict:
    """取得設定，UI 設定優先於 .env"""
    settings = dict(_DEFAULT_SETTINGS)

    # 讀取 UI 儲存的設定
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass

    return settings


def save_settings(data: dict) -> None:
    """儲存設定到 JSON"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_api_key(provider: str) -> str:
    """取得指定服務商的 API Key（UI 設定 > .env）"""
    settings = get_settings()

    env_defaults = {
        "openai": DEFAULT_OPENAI_API_KEY,
        "google": DEFAULT_GOOGLE_API_KEY,
        "elevenlabs": DEFAULT_ELEVENLABS_API_KEY,
    }
    ui_keys = {
        "openai": settings.get("openai_api_key", ""),
        "google": settings.get("google_api_key", ""),
        "elevenlabs": settings.get("elevenlabs_api_key", ""),
    }

    # UI 設定優先
    return ui_keys.get(provider, "") or env_defaults.get(provider, "")
