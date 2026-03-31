"""應用程式設定管理"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 路徑設定
BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_DIR = BASE_DIR / "sources"
OUTPUT_DIR = BASE_DIR / "output"
CHUNKS_DIR = BASE_DIR / "chunks"
DATA_DIR = BASE_DIR / "data"
TASKS_DIR = DATA_DIR / "tasks"
SETTINGS_FILE = DATA_DIR / "settings.json"

# 確保目錄存在
for d in [OUTPUT_DIR, CHUNKS_DIR, DATA_DIR, TASKS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 音檔分段設定
CHUNK_DURATION_SECONDS = 600  # 每段 10 分鐘
CHUNK_OVERLAP_SECONDS = 5    # 段間重疊 5 秒

# 從環境變數載入預設 API Keys
DEFAULT_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
DEFAULT_GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
DEFAULT_ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# 支援的服務商與模型
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": [
            {"id": "whisper-1", "name": "Whisper V2"},
            {"id": "gpt-4o-transcribe", "name": "GPT-4o Transcribe"},
            {"id": "gpt-4o-mini-transcribe", "name": "GPT-4o Mini Transcribe"},
        ],
        "max_file_size": 25 * 1024 * 1024,  # 25 MB
    },
    "google": {
        "name": "Google Cloud",
        "models": [
            {"id": "latest_long", "name": "Latest Long"},
            {"id": "latest_short", "name": "Latest Short"},
            {"id": "chirp_2", "name": "Chirp 2"},
        ],
        "max_file_size": 10 * 1024 * 1024,  # 10 MB（串流模式）
    },
    "elevenlabs": {
        "name": "ElevenLabs",
        "models": [
            {"id": "scribe_v2", "name": "Scribe V2"},
        ],
        "max_file_size": None,  # 無明確限制
    },
}

# 支援的語言
LANGUAGES = [
    {"code": "zh", "name": "繁體中文"},
    {"code": "zh-CN", "name": "簡體中文"},
    {"code": "en", "name": "English"},
    {"code": "ja", "name": "日本語"},
    {"code": "ko", "name": "한국어"},
]
