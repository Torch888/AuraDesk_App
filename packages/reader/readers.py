"""信息读取模块 - 日历、快递、票务、邮件、飞书"""
from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Optional, Dict, List

from packages.shared.config import settings
from packages.shared.database import db
from packages.shared.models import (
    ReminderCreate, ReminderCategory, ReminderSource,
    ParcelTask, ParcelStatus,
    TicketEvent, TicketStatus,
    Priority,
)


# ─── 快递信息读取器 ─────────────────────────────────


class ParcelReader:
    """从快递短信/文本中提取快递信息"""

    # 常见快递公司关键词
    CARRIERS = {
        "顺丰": "顺丰",
        "SF": "顺丰",
        "中通": "中通",
        "圆通": "圆通",
        "韵达": "韵达",
        "申通": "申通",
        "百世": "百世",
        "极兔": "极兔",
        "京东": "京东",
        "德邦": "德邦",
        "EMS": "EMS",
        "邮政": "邮政",
        "菜鸟": "菜鸟",
        "丰巢": "丰巢",
    }

    # 常见取件地点关键词
    LOCATION_KEYWORDS = [
        "菜鸟驿站", "丰巢柜", "快递柜", "门卫", "前台",
        "驿站", "收发室", "快递点", "物业", "蜂巢",
    ]

    def parse_sms_text(self, text: str) -> Optional[Dict]:
        """解析快递短信文本，返回提取的信息字典"""
        result = {
            "carrier": "",
            "pickup_code": "",
            "pickup_location": "",
            "raw_text": text,
        }

        # 识别快递公司
        for keyword, carrier_name in self.CARRIERS.items():
            if keyword in text:
                result["carrier"] = carrier_name
                break

        # 提取取件码
        code_patterns = [
            r"取件码[：:\s]*(\d{4,8})",
            r"验证码[：:\s]*(\d{4,8})",
            r"提货码[：:\s]*(\d{4,8})",
            r"编号[：:\s]*(\d{4,8})",
            r"码[：:\s]*(\d{4,8})",
            r"(\d{4,8})[号\s]*取",
        ]
        for pattern in code_patterns:
            match = re.search(pattern, text)
            if match:
                result["pickup_code"] = match.group(1)
                break

        # 如果没找到取件码，尝试找纯数字码
        if not result["pickup_code"]:
            numbers = re.findall(r"\b\d{4,8}\b", text)
            if numbers:
                result["pickup_code"] = numbers[0]

        # 提取取件地点
        for loc in self.LOCATION_KEYWORDS:
            if loc in text:
                result["pickup_location"] = loc
                break

        if result.get("carrier") or result.get("pickup_code"):
            return result
        return None

    def create_from_sms(self, text: str, preferred_time: str = "18:30") -> Optional[str]:
        """从快递短信创建快递提醒"""
        parsed = self.parse_sms_text(text)
        if not parsed:
            return None

        # 构建提醒标题
        carrier = parsed["carrier"] or "快递"
        code = parsed["pickup_code"]
        location = parsed["pickup_location"] or "快递点"
        title = f"取快递 - {carrier}"
        description = f"取件码: {code}" if code else f"请到{location}取件"

        # 计算提醒时间：默认今天18:30，如果已过则明天
        now = datetime.now()
        hour, minute = map(int, preferred_time.split(":"))
        remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if remind_time <= now:
            from datetime import timedelta
            remind_time += timedelta(days=1)

        # 创建提醒
        reminder = db.create_reminder(ReminderCreate(
            title=title,
            description=description,
            category=ReminderCategory.parcel,
            start_time=remind_time,
            remind_offsets=[0],
            source=ReminderSource.sms,
        ))

        # 创建快递记录
        db.create_parcel(ParcelTask(
            carrier=parsed["carrier"],
            pickup_code=parsed["pickup_code"],
            pickup_location=parsed["pickup_location"],
            reminder_id=reminder.id,
            raw_text=text,
        ))

        return reminder.id


# ─── 票务监控器 ─────────────────────────────────


class TicketMonitor:
    """票务信息监控"""

    PLATFORM_KEYWORDS = {
        "大麦": "大麦网",
        "猫眼": "猫眼",
        "秀动": "秀动",
        "永乐": "永乐票务",
        "聚橙": "聚橙网",
    }

    def parse_ticket_info(self, text: str) -> Optional[Dict]:
        """从文本中提取票务信息"""
        result = {
            "event_name": "",
            "platform": "",
            "city": "",
        }

        # 提取演唱会/活动名称
        event_patterns = [
            r"(.+?)(?:演唱会|音乐会|话剧|展览|比赛|赛事)",
            r"(.+?)(?:开票|开抢|抢票|售票)",
            r"抢(.+?)门票",
        ]
        for pattern in event_patterns:
            match = re.search(pattern, text)
            if match:
                result["event_name"] = match.group(0)
                break

        if not result["event_name"]:
            result["event_name"] = text[:30]

        # 识别平台
        for keyword, platform_name in self.PLATFORM_KEYWORDS.items():
            if keyword in text:
                result["platform"] = platform_name
                break

        # 提取城市
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "南京", "武汉", "重庆", "西安", "长沙", "天津"]
        for city in cities:
            if city in text:
                result["city"] = city
                break

        return result


# ─── 日历读取器 ─────────────────────────────────


class CalendarReader:
    """从外部日历源读取日程（支持 ICS/iCal 格式）"""

    async def sync_to_reminders(self, url: str) -> int:
        """从 ICS 日历 URL 同步事件到提醒系统"""
        import httpx
        from icalendar import Calendar

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30)
                resp.raise_for_status()
                cal = Calendar.from_ical(resp.content)
        except ImportError:
            print("[Calendar] icalendar 未安装，跳过日历同步")
            return 0
        except Exception as e:
            print(f"[Calendar] 同步失败: {e}")
            return 0

        count = 0
        now = datetime.now()
        for component in cal.walk("VEVENT"):
            try:
                summary = str(component.get("summary", "日程"))
                dtstart = component.get("dtstart")
                dtend = component.get("dtend")
                location = str(component.get("location", ""))
                description = str(component.get("description", ""))

                if not dtstart:
                    continue

                start_dt = dtstart.dt
                if hasattr(start_dt, 'tzinfo') and start_dt.tzinfo is not None:
                    start_dt = start_dt.replace(tzinfo=None)

                # 只同步未来事件
                if start_dt < now:
                    continue

                title = f"[日历] {summary}"
                desc_parts = []
                if location:
                    desc_parts.append(f"地点: {location}")
                if description:
                    desc_parts.append(description)

                db.create_reminder(ReminderCreate(
                    title=title,
                    description=" | ".join(desc_parts) if desc_parts else None,
                    category=ReminderCategory.calendar,
                    start_time=start_dt,
                    remind_offsets=[-1800, -600, 0],
                    source=ReminderSource.calendar,
                ))
                count += 1
            except Exception as e:
                print(f"[Calendar] 事件解析失败: {e}")
                continue

        return count


# ─── 邮件读取器（预留接口）─────────────────────────────────


class EmailReader:
    """从邮箱中读取重要邮件并创建提醒（预留接口）"""

    async def scan_important_emails(self) -> List[Dict]:
        """扫描未读的重要邮件"""
        # 预留：实际实现需要 IMAP 连接
        # import imaplib
        # import email
        return []


# ─── 飞书读取器（预留接口）─────────────────────────────────


class FeishuReader:
    """从飞书读取日历/消息并创建提醒（预留接口）"""

    async def sync_calendar_events(self) -> List[Dict]:
        """同步飞书日历事件"""
        # 预留：实际实现需要飞书开放平台 API
        return []


calendar_reader = CalendarReader()
parcel_reader = ParcelReader()
ticket_monitor = TicketMonitor()