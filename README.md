# Voice2Text — 語音轉文字工具

將中文語音檔（MP3、WAV、M4A 等）透過 AI 語音辨識轉為 Markdown 格式文字，並提供線上編輯與 AI 文句優化功能。

## 功能特色

- **多服務商支援**：OpenAI Whisper、Google Cloud Speech-to-Text、ElevenLabs Scribe
- **Web 介面管理**：服務商、模型、語言選擇，API Key 設定
- **音檔上傳**：拖放或點擊上傳，支援 MP3、WAV、M4A、FLAC 等格式
- **大檔案處理**：自動分段（10 分鐘 / 段，5 秒重疊），合併時去除重複
- **Markdown 編輯器**：EasyMDE 即時預覽、自動儲存、匯出 .md
- **AI 文句優化**：GPT 串流處理，即時顯示進度與預覽
- **任務管理**：防呆機制（避免重複 / 併發）、狀態追蹤、Badge 標記
- **分頁功能**：音檔列表與任務紀錄每頁 20 筆

## 技術架構

| 層級 | 技術 |
|------|------|
| 後端 | FastAPI + Jinja2 |
| 前端 | Tailwind CSS v4 (CDN) + EasyMDE (CDN) |
| 語音辨識 | OpenAI / Google / ElevenLabs API |
| 文字優化 | OpenAI GPT (AsyncOpenAI + SSE 串流) |
| 音訊處理 | ffmpeg / ffprobe |
| 套件管理 | UV |

## 快速開始

### 前置需求

- Python >= 3.11
- [UV](https://docs.astral.sh/uv/) 套件管理器
- ffmpeg（音訊處理）

### 安裝

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯 .env，填入你的 API Key
# 或稍後在 Web UI 設定頁面填入

# 安裝相依套件
uv sync
```

### 啟動

```bash
uv run uvicorn app.main:app --reload --port 8001
```

開啟瀏覽器前往 `http://localhost:8001`

## 使用方式

1. **設定 API Key**：前往「設定」頁面輸入各服務商的 API Key
2. **上傳音檔**：在首頁拖放或點擊上傳音檔
3. **選擇服務商與模型**：在轉錄設定區選擇偏好的服務商、模型、語言
4. **開始轉錄**：點擊音檔旁的「開始轉錄」按鈕
5. **編輯結果**：轉錄完成後點擊「編輯」或綠色 Badge 進入 Markdown 編輯器
6. **AI 優化**：在編輯器中使用 AI 優化功能改善文句品質
7. **匯出**：下載 .md 檔案

## 專案結構

```
voice2text/
├── app/
│   ├── main.py              # FastAPI 應用程式入口
│   ├── config.py             # 設定與路徑常數
│   ├── routes/
│   │   ├── api.py            # REST API 路由
│   │   ├── pages.py          # 頁面路由
│   │   └── sse.py            # Server-Sent Events 路由
│   ├── services/
│   │   ├── audio.py          # 音訊處理（ffmpeg）
│   │   ├── formatter.py      # Markdown 格式化
│   │   ├── refine.py         # AI 文句優化
│   │   ├── settings.py       # 設定管理
│   │   ├── tasks.py          # 任務管理
│   │   ├── transcribe.py     # 轉錄抽象層
│   │   └── providers/        # 各服務商 STT 實作
│   │       ├── openai_stt.py
│   │       ├── google_stt.py
│   │       └── elevenlabs_stt.py
│   ├── templates/            # Jinja2 模板
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── editor.html
│   │   └── settings.html
│   └── static/
│       └── js/app.js
├── sources/                  # 原始音檔（git 忽略）
├── output/                   # 轉錄輸出（git 忽略）
├── data/                     # 任務資料（git 忽略）
├── .env.example              # 環境變數範本
├── pyproject.toml            # 專案定義與相依套件
└── README.md
```

## 授權

私人專案，僅供內部使用。
