"""AuraDesk 智能提醒助手 - API 入口"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from packages.shared.config import settings
from packages.shared.database import db
from packages.shared.notification import notifier
from packages.shared.models import NotificationMessage
from packages.scheduler.engine import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    db.init_db()
    db.log_event("app_start", message="AuraDesk 提醒助手启动")
    scheduler.set_notify_callback(notifier.send)
    asyncio.create_task(scheduler.start())
    print(f"\n{'='*50}")
    print(f"  🚀 {settings.app_name} v{settings.version}")
    print(f"  📍 API 文档: http://127.0.0.1:8000/docs")
    print(f"  📊 健康检查: http://127.0.0.1:8000/health")
    print(f"{'='*50}\n")
    yield
    scheduler.stop()
    db.log_event("app_stop", message="AuraDesk 提醒助手停止")
    db.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="桌面智能数字人提醒助手 - 智能信息读取与提醒引擎",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from apps.api.routers.reminders import router as reminders_router
app.include_router(reminders_router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": __import__("datetime").datetime.now().isoformat()}


def run():
    """启动函数"""
    uvicorn.run(
        "apps.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()