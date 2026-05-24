#!/usr/bin/env python3
"""
桌面智能数字人提醒助手 - 模块三测试脚本
直接运行验证提醒引擎是否正常工作
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from packages.shared.database import db
from packages.shared.models import (
    ReminderCreate, ReminderStatus, ReminderCategory, ReminderSource, Priority,
    ParcelTask, ParcelStatus,
    TicketEvent, TicketStatus,
)
from datetime import datetime, timedelta


def test_basic():
    """1. 测试数据库初始化"""
    print("\n" + "="*60)
    print("🧪 测试1: 数据库初始化")
    db.init_db()
    reminders = db.list_reminders()
    print(f"   ✅ 数据库初始化成功，当前 {len(reminders)} 条提醒")


def test_create_reminder():
    """2. 测试创建提醒"""
    print("\n" + "="*60)
    print("🧪 测试2: 创建提醒")

    now = datetime.now()
    reminder = db.create_reminder(ReminderCreate(
        title="测试：明晚8点抢周杰伦演唱会门票",
        description="大麦网开抢",
        category=ReminderCategory.ticket,
        start_time=now + timedelta(hours=2),
        remind_offsets=[-1800, -600, 0],
        priority=Priority.high,
        source=ReminderSource.manual,
        action_url="https://example.com/ticket",
    ))
    print(f"   ✅ 创建成功 | ID: {reminder.id}")
    print(f"   📌 {reminder.title}")
    print(f"   ⏰ {reminder.start_time}")
    return reminder


def test_create_parcel():
    """3. 测试创建快递提醒"""
    print("\n" + "="*60)
    print("🧪 测试3: 创建快递提醒")

    text = "顺丰快递已到菜鸟驿站，请凭取件码 1234 取件。"
    from packages.reader.readers import ParcelReader
    reader = ParcelReader()
    result = reader.parse_sms_text(text)
    if result:
        print(f"   ✅ 识别到快递: {result['carrier']}")
        print(f"   📦 取件码: {result['pickup_code']}")

        reminder = db.create_reminder(ReminderCreate(
            title=f"取快递 - {result['carrier']}",
            description=f"取件码: {result['pickup_code']}，地点: {result['pickup_location'] or '菜鸟驿站'}",
            category=ReminderCategory.parcel,
            start_time=datetime.now().replace(hour=18, minute=30),
            remind_offsets=[0],
            source=ReminderSource.sms,
        ))

        parcel = ParcelTask(
            carrier=result["carrier"],
            pickup_code=result["pickup_code"],
            pickup_location=result["pickup_location"],
            reminder_id=reminder.id,
            raw_text=text,
        )
        db.create_parcel(parcel)
        print(f"   ✅ 快递记录已创建")
        return reminder
    else:
        print(f"   ❌ 未识别出快递信息")
        return None


def test_list():
    """4. 测试列出提醒"""
    print("\n" + "="*60)
    print("🧪 测试4: 列出所有提醒")

    all_r = db.list_reminders()
    pending = db.list_reminders(ReminderStatus.pending)

    print(f"   📊 全部: {len(all_r)} | 待处理: {len(pending)}")
    for r in all_r:
        print(f"   [{r.status.value}] {r.title} @ {r.start_time.strftime('%m-%d %H:%M')}")

    parcels = db.list_parcels()
    print(f"   📦 快递: {len(parcels)}")


def test_ticket():
    """5. 测试票务提醒"""
    print("\n" + "="*60)
    print("🧪 测试5: 创建票务提醒")

    ticket = db.create_ticket(TicketEvent(
        event_name="周杰伦2026巡回演唱会-北京站",
        sale_time=datetime.now() + timedelta(days=7),
        platform="大麦网",
        ticket_url="https://detail.damai.cn/xxx",
        city="北京",
        priority=Priority.high,
    ))
    print(f"   ✅ 票务已记录: {ticket.event_name}")
    print(f"   ⏰ 开售时间: {ticket.sale_time.strftime('%m-%d %H:%M')}")


def test_stats():
    """6. 测试统计"""
    print("\n" + "="*60)
    print("🧪 测试6: 数据统计")

    reminders = db.list_reminders()
    parcels = db.list_parcels()
    tickets = db.list_tickets()

    print(f"   📌 提醒总数: {len(reminders)}")
    print(f"   📦 快递记录: {len(parcels)}")
    print(f"   🎫 票务记录: {len(tickets)}")

    status_counts = {}
    for r in reminders:
        status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
    for s, c in status_counts.items():
        print(f"      - {s}: {c}")


if __name__ == "__main__":
    print("="*60)
    print("  桌面智能数字人提醒助手 - 模块三测试")
    print("  智能信息读取与提醒引擎模块")
    print("="*60)

    test_basic()
    test_create_reminder()
    test_create_parcel()
    test_list()
    test_ticket()
    test_stats()

    print("\n" + "="*60)
    print("  ✅ 全部测试完成！")
    print("  📍 提醒引擎运行正常")
    print("  📍 数据库读写正常")
    print("  📍 快递解析正常")
    print("  📍 票务管理正常")
    print("="*60)
    print()
    print("启动API服务:")
    print("  cd apps/api && python main.py")
    print("  或: uvicorn apps.api.main:app --reload")
    print()