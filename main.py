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
    db.init_db()
    db.log_event("app_start", message="提醒助手启动")
    scheduler.set_notify_callback(notifier.send)
    asyncio.create_task(scheduler.start())
    yield
    scheduler.stop()
    db.log_event("app_stop", message="提醒助手停止")
    db.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from apps.api.routers.reminders import router as reminders_router
app.include_router(reminders_router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


def run():
    uvicorn.run(
        "apps.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()