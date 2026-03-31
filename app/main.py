"""Voice2Text Web 應用程式入口"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import api, pages, sse

app = FastAPI(title="Voice2Text", description="語音轉文字 Web 應用")

# 靜態檔案與模板
APP_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")

# 將 templates 注入到路由模組
pages.templates = templates

# 註冊路由
app.include_router(pages.router)
app.include_router(api.router, prefix="/api")
app.include_router(sse.router, prefix="/api")
