"""数据模型定义"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


def gen_id() -> str:
    return uuid.uuid4().hex[:16]


# ─── 枚举 ─────────────────────────────────


class ReminderStatus(str, Enum):
    pending = "pending"
    triggered = "triggered"
    acknowledged = "acknowledged"
    snoozed = "snoozed"
    dismissed = "dismissed"
    failed = "failed"


class ReminderCategory(str, Enum):
    alarm = "alarm"
    meeting = "meeting"
    parcel = "parcel"
    ticket = "ticket"
    travel = "travel"
    bill = "bill"
    calendar = "calendar"
    email = "email"
    feishu = "feishu"
    custom = "custom"


class ReminderSource(str, Enum):
    manual = "manual"
    llm = "llm"
    sms = "sms"
    calendar = "calendar"
    email = "email"
    feishu = "feishu"


class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class ParcelStatus(str, Enum):
    pending = "pending"
    picked_up = "picked_up"
    expired = "expired"


class TicketStatus(str, Enum):
    upcoming = "upcoming"
    reminding = "reminding"
    on_sale = "on_sale"
    expired = "expired"
    cancelled = "cancelled"


# ─── 提醒模型 ─────────────────────────────────


class ReminderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: ReminderCategory = ReminderCategory.custom
    start_time: datetime
    remind_offsets: List[int] = [-1800, -600, 0]  # 提前30分钟、10分钟、准时
    priority: Priority = Priority.normal
    source: ReminderSource = ReminderSource.manual
    action_url: Optional[str] = None
    recurrence: Optional[str] = None  # daily/weekly/monthly/yearly


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ReminderCategory] = None
    start_time: Optional[datetime] = None
    remind_offsets: Optional[List[int]] = None
    priority: Optional[Priority] = None
    action_url: Optional[str] = None
    status: Optional[ReminderStatus] = None


class Reminder(BaseModel):
    id: str = Field(default_factory=gen_id)
    title: str
    description: Optional[str] = None
    category: ReminderCategory = ReminderCategory.custom
    start_time: datetime
    remind_offsets: List[int] = [-1800, -600, 0]
    priority: Priority = Priority.normal
    source: ReminderSource = ReminderSource.manual
    action_url: Optional[str] = None
    recurrence: Optional[str] = None
    status: ReminderStatus = ReminderStatus.pending
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }


# ─── 快递模型 ─────────────────────────────────


class ParcelTask(BaseModel):
    id: str = Field(default_factory=gen_id)
    carrier: str = ""  # 快递公司
    pickup_code: str = ""  # 取件码
    pickup_location: str = ""  # 取件地点
    reminder_id: str = ""
    raw_text: str = ""
    status: ParcelStatus = ParcelStatus.pending
    created_at: datetime = Field(default_factory=datetime.now)


# ─── 票务模型 ─────────────────────────────────


class TicketEvent(BaseModel):
    id: str = Field(default_factory=gen_id)
    event_name: str
    sale_time: datetime
    platform: str = ""
    ticket_url: Optional[str] = None
    city: str = ""
    priority: Priority = Priority.high
    status: TicketStatus = TicketStatus.upcoming
    reminder_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


# ─── 用户偏好 ─────────────────────────────────


class UserPreference(BaseModel):
    id: str = Field(default_factory=gen_id)
    default_parcel_time: str = "18:30"
    default_remind_offsets: List[int] = [-1800, -600, 0]
    quiet_hours_start: Optional[str] = None  # 免打扰开始
    quiet_hours_end: Optional[str] = None  # 免打扰结束
    voice_enabled: bool = True
    popup_enabled: bool = True
    daily_summary_time: str = "08:00"  # 每日总结时间


# ─── LLM Agent 解析结果 ─────────────────────────────────


class AgentParseResult(BaseModel):
    intent: str = "create_reminder"
    title: Optional[str] = None
    description: Optional[str] = None
    category: ReminderCategory = ReminderCategory.custom
    start_time: str = ""  # ISO格式
    remind_offsets: List[int] = [-1800, -600, 0]
    priority: Priority = Priority.normal
    action_url: Optional[str] = None


# ─── 通知消息 ─────────────────────────────────


class NotificationMessage(BaseModel):
    title: str
    body: str
    reminder_id: str = ""
    action_url: Optional[str] = None
    category: str = "reminder"
    priority: str = "normal"