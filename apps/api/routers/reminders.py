"""提醒管理 API 路由"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.shared.database import db
from packages.shared.models import (
    ReminderCreate,
    ReminderUpdate,
    ReminderStatus,
    ReminderCategory,
    ParcelTask,
    ParcelStatus,
    TicketEvent,
    TicketStatus,
    UserPreference,
    AgentParseResult,
)
from packages.llm.engine import llm_engine
from packages.reader.readers import CalendarReader, ParcelReader, TicketMonitor

router = APIRouter(prefix="/api", tags=["reminders"])

calendar_reader = CalendarReader()
parcel_reader = ParcelReader()
ticket_monitor = TicketMonitor()


class AgentMessage(BaseModel):
    text: str


# ─── Reminder CRUD ─────────────────────────────────


@router.post("/reminders")
async def create_reminder(data: ReminderCreate):
    """创建提醒"""
    reminder = db.create_reminder(data)
    from packages.scheduler.engine import scheduler
    scheduler.schedule_reminder(reminder)
    return {"ok": True, "reminder": reminder.model_dump(mode="json")}


@router.get("/reminders")
async def list_reminders(status: Optional[str] = None, limit: int = 100):
    """获取提醒列表"""
    s = ReminderStatus(status) if status else None
    reminders = db.list_reminders(s, limit)
    return {"ok": True, "reminders": [r.model_dump(mode="json") for r in reminders]}


@router.get("/reminders/today")
async def get_today_reminders():
    """获取今日提醒"""
    all_reminders = db.list_reminders()
    today = datetime.now().date()
    today_list = [r for r in all_reminders if r.start_time.date() == today]
    return {"ok": True, "reminders": [r.model_dump(mode="json") for r in today_list]}


@router.get("/reminders/{reminder_id}")
async def get_reminder(reminder_id: str):
    """获取单个提醒详情"""
    r = db.get_reminder(reminder_id)
    if not r:
        raise HTTPException(404, "提醒不存在")
    return {"ok": True, "reminder": r.model_dump(mode="json")}


@router.patch("/reminders/{reminder_id}")
async def update_reminder(reminder_id: str, data: ReminderUpdate):
    """更新提醒"""
    updates = data.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "没有需要更新的字段")
    if not db.get_reminder(reminder_id):
        raise HTTPException(404, "提醒不存在")
    db.update_reminder(reminder_id, updates)
    return {"ok": True, "message": "已更新"}


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """删除提醒"""
    if not db.delete_reminder(reminder_id):
        raise HTTPException(404, "提醒不存在")
    return {"ok": True, "message": "已删除"}


@router.post("/reminders/{reminder_id}/ack")
async def acknowledge_reminder(reminder_id: str):
    """确认提醒（用户已处理）"""
    ok = db.update_reminder_status(reminder_id, ReminderStatus.acknowledged)
    if not ok:
        raise HTTPException(404, "提醒不存在")
    db.log_event("reminder_acknowledged", reminder_id, "用户已确认")
    return {"ok": True, "message": "已确认"}


@router.post("/reminders/{reminder_id}/snooze")
async def snooze_reminder(reminder_id: str, minutes: int = 10):
    """稍后提醒"""
    r = db.get_reminder(reminder_id)
    if not r:
        raise HTTPException(404, "提醒不存在")
    new_time = datetime.now() + timedelta(minutes=minutes)
    db.update_reminder(reminder_id, {
        "status": ReminderStatus.snoozed.value,
        "start_time": new_time.isoformat(),
    })
    db.log_event("reminder_snoozed", reminder_id, f"稍后{minutes}分钟提醒")
    return {"ok": True, "message": f"已设置为{minutes}分钟后提醒"}


# ─── LLM Agent ─────────────────────────────────


@router.post("/agent/message")
async def agent_message(data: AgentMessage):
    """AI 自然语言解析 - 用户说一句话，自动创建提醒"""
    result = await llm_engine.parse_reminder(data.text)
    if not result:
        return {"ok": False, "message": "无法理解您的意思，请重新描述", "intent": "unknown"}

    if result.intent == "create_reminder" and result.title:
        try:
            start_time = datetime.strptime(result.start_time, "%Y-%m-%d %H:%M")
        except Exception:
            start_time = datetime.now()

        reminder = db.create_reminder(ReminderCreate(
            title=result.title,
            description=result.description,
            category=result.category,
            start_time=start_time,
            remind_offsets=result.remind_offsets,
            priority=result.priority,
            source="llm",
            action_url=result.action_url,
        ))
        from packages.scheduler.engine import scheduler
        scheduler.schedule_reminder(reminder)
        return {
            "ok": True,
            "message": f"已创建提醒：{result.title}",
            "reminder": reminder.model_dump(mode="json"),
        }

    if result.intent == "query":
        reminders = db.list_reminders()
        return {
            "ok": True,
            "message": f"当前共有 {len(reminders)} 条提醒",
            "intent": "query",
            "reminders": [r.model_dump(mode="json") for r in reminders],
        }

    return {"ok": False, "message": f"识别到意图: {result.intent}，暂不支持此操作", "intent": result.intent}


# ─── Parcel 快递管理 ─────────────────────────────────


@router.post("/parcels/parse")
async def parse_parcel(text: str, preferred_time: str = "18:30"):
    """解析快递短信文本，自动创建取件提醒"""
    reminder_id = parcel_reader.create_from_sms(text, preferred_time)
    if not reminder_id:
        raise HTTPException(400, "未能从文本中识别快递信息，请确保包含快递公司和取件码")
    return {"ok": True, "reminder_id": reminder_id, "message": "已创建取件提醒"}


@router.get("/parcels")
async def list_parcels(status: Optional[str] = None):
    """获取快递列表"""
    s = ParcelStatus(status) if status else None
    parcels = db.list_parcels(s)
    return {"ok": True, "parcels": [p.model_dump(mode="json") for p in parcels]}


@router.post("/parcels/{parcel_id}/picked-up")
async def mark_picked_up(parcel_id: str):
    """标记快递已取件"""
    ok = db.update_parcel_status(parcel_id, ParcelStatus.picked_up)
    if not ok:
        raise HTTPException(404, "快递记录不存在")
    return {"ok": True, "message": "已标记为已取件"}


# ─── Ticket 票务管理 ─────────────────────────────────


@router.post("/tickets")
async def create_ticket(data: TicketEvent):
    """添加票务提醒"""
    ticket = db.create_ticket(data)
    return {"ok": True, "ticket": ticket.model_dump(mode="json")}


@router.get("/tickets")
async def list_tickets(status: Optional[str] = None):
    """获取票务列表"""
    s = TicketStatus(status) if status else None
    tickets = db.list_tickets(s)
    return {"ok": True, "tickets": [t.model_dump(mode="json") for t in tickets]}


# ─── Calendar Sync 日历同步 ─────────────────────────────────


@router.post("/calendar/sync")
async def sync_calendar(url: str):
    """从 ICS 日历 URL 同步事件"""
    count = await calendar_reader.sync_to_reminders(url)
    return {"ok": True, "synced": count, "message": f"已同步 {count} 个日程事件"}


# ─── Preference 用户偏好 ─────────────────────────────────


@router.get("/preferences")
async def get_preferences():
    """获取用户偏好设置"""
    pref = db.get_preference()
    return {"ok": True, "preferences": pref.model_dump(mode="json")}


@router.put("/preferences")
async def save_preferences(data: UserPreference):
    """保存用户偏好设置"""
    db.save_preference(data)
    return {"ok": True, "message": "已保存"}


# ─── Stats 统计 ─────────────────────────────────


@router.get("/stats")
async def get_stats():
    """获取数据统计概览"""
    reminders = db.list_reminders()
    parcels = db.list_parcels()
    tickets = db.list_tickets()

    today = datetime.now().date()
    return {
        "ok": True,
        "stats": {
            "total_reminders": len(reminders),
            "total_parcels": len(parcels),
            "total_tickets": len(tickets),
            "pending_reminders": len([r for r in reminders if r.status == ReminderStatus.pending]),
            "triggered_reminders": len([r for r in reminders if r.status == ReminderStatus.triggered]),
            "today_reminders": len([r for r in reminders if r.start_time.date() == today]),
            "pending_parcels": len([p for p in parcels if p.status == ParcelStatus.pending]),
            "upcoming_tickets": len([t for t in tickets if t.status == TicketStatus.upcoming]),
        },
    }