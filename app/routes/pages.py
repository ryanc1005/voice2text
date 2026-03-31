"""Jinja2 頁面路由"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates: Jinja2Templates = None  # 由 main.py 注入


@router.get("/")
async def index(request: Request):
    """主頁：檔案列表與轉錄控制"""
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/editor/{task_id}")
async def editor(request: Request, task_id: str):
    """編輯頁：Markdown 編輯器與預覽"""
    return templates.TemplateResponse(request=request, name="editor.html", context={"task_id": task_id})


@router.get("/settings")
async def settings(request: Request):
    """設定頁：API Keys 與偏好"""
    return templates.TemplateResponse(request=request, name="settings.html")
