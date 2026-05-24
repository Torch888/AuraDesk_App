"""提醒调度引擎 - 后台轮询 + 多级提醒触发"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional, List

from packages.shared.database import db
from packages.shared.models import (
    Reminder, ReminderStatus,
    NotificationMessage,
)


class Scheduler:
    """后台调度器：轮询即将到期的提醒并触发通知"""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._notify_callback: Optional[Callable] = None
        self._poll_interval = 30  # 每30秒检查一次
        self._triggered_cache: set = set()  # 已触发的 remind_key 缓存，避免重复

    def set_notify_callback(self, callback: Callable):
        """设置通知回调函数"""
        self._notify_callback = callback

    def schedule_reminder(self, reminder: Reminder):
        """将提醒纳入调度（通过数据库持久化，调度器会自动发现）"""
        print(f"[Scheduler] 已注册提醒: {reminder.title} @ {reminder.start_time}")

    async def start(self):
        """启动调度循环"""
        self._running = True
        print("[Scheduler] 调度引擎已启动")
        while self._running:
            try:
                await self._check_reminders()
            except Exception as e:
                print(f"[Scheduler] 检查异常: {e}")
            await asyncio.sleep(self._poll_interval)

    def stop(self):
        """停止调度"""
        self._running = False
        print("[Scheduler] 调度引擎已停止")

    async def _check_reminders(self):
        """检查所有待处理提醒，触发到期的"""
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 获取所有 pending 和 snoozed 状态的提醒
        pending = db.list_reminders(ReminderStatus.pending)
        snoozed = db.list_reminders(ReminderStatus.snoozed)
        all_active = pending + snoozed

        for reminder in all_active:
            try:
                start_time = reminder.start_time
                if isinstance(start_time, str):
                    start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")

                # 检查每个提前提醒偏移
                for offset_seconds in reminder.remind_offsets:
                    trigger_time = start_time + timedelta(seconds=offset_seconds)

                    # 判断是否应该触发：trigger_time 在 [now - poll_interval*2, now] 之间
                    if now - timedelta(seconds=self._poll_interval * 2) <= trigger_time <= now:
                        trigger_key = f"{reminder.id}:{offset_seconds}"
                        if trigger_key not in self._triggered_cache:
                            self._triggered_cache.add(trigger_key)
                            await self._trigger_reminder(reminder, offset_seconds, trigger_time)

                # 检查是否已过期（超过start_time 1小时仍未确认）
                if start_time < now - timedelta(hours=1) and reminder.status == ReminderStatus.pending:
                    print(f"[Scheduler] 提醒已过期: {reminder.title}")
                    db.update_reminder_status(reminder.id, ReminderStatus.failed)
            except Exception as e:
                print(f"[Scheduler] 处理提醒 {reminder.id} 异常: {e}")

    async def _trigger_reminder(self, reminder: Reminder, offset_seconds: int, trigger_time: datetime):
        """触发提醒通知"""
        # 构建通知消息
        if offset_seconds == 0:
            title = f"⏰ {reminder.title}"
            body = "现在是时候了！"
        elif offset_seconds < 0:
            minutes_before = abs(offset_seconds) // 60
            if minutes_before >= 60:
                hours_before = minutes_before // 60
                title = f"📅 提前提醒: {reminder.title}"
                body = f"{hours_before}小时后开始"
            else:
                title = f"📅 提前提醒: {reminder.title}"
                body = f"将在{minutes_before}分钟后开始"
        else:
            title = f"🔔 {reminder.title}"
            body = f"已经开始 {offset_seconds // 60} 分钟了"

        if reminder.description:
            body += f"\n详情: {reminder.description}"

        msg = NotificationMessage(
            title=title,
            body=body,
            reminder_id=reminder.id,
            action_url=reminder.action_url,
            category=reminder.category.value,
            priority=reminder.priority.value,
        )

        # 发送通知
        if self._notify_callback:
            self._notify_callback(msg)

        # 更新状态为 triggered
        if offset_seconds == 0:
            db.update_reminder_status(reminder.id, ReminderStatus.triggered)
            db.log_event("reminder_triggered", reminder.id, f"准时提醒: {reminder.title}")
        else:
            db.log_event("reminder_pre_alert", reminder.id, f"提前提醒({offset_seconds}s): {reminder.title}")


scheduler = Scheduler()