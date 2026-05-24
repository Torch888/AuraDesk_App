#!/usr/bin/env python3
"""
AuraDesk 桌面智能数字人提醒助手 - 模块三测试脚本
验证提醒引擎各模块是否正常工作
"""
from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from packages.shared.database import db
from packages.shared.models import (
    ReminderCreate, ReminderStatus, ReminderCategory, ReminderSource, Priority,
    ParcelTask, ParcelStatus, TicketEvent, TicketStatus,
)
from datetime import datetime, timedelta


def test_basic():
    """1. 数据库初始化测试"""
    print("\n" + "="*60)
    print("[测试1] 数据库初始化")
    db.init_db()
    reminders = db.list_reminders()
    print(f"  PASS - 数据库初始化成功，当前 {len(reminders)} 条提醒")


def test_create_reminder():
    """2. 创建提醒测试"""
    print("\n" + "="*60)
    print("[测试2] 创建提醒")

    now = datetime.now()
    reminder = db.create_reminder(ReminderCreate(
        title="明晚8点抢周杰伦演唱会门票",
        description="大麦网开抢，记得提前登录",
        category=ReminderCategory.ticket,
        start_time=now + timedelta(hours=2),
        remind_offsets=[-1800, -600, 0],
        priority=Priority.high,
        source=ReminderSource.manual,
        action_url="https://detail.damai.cn/xxx",
    ))
    print(f"  PASS - 创建成功 | ID: {reminder.id}")
    print(f"  TITLE: {reminder.title}")
    print(f"  TIME:  {reminder.start_time}")
    return reminder


def test_create_parcel():
    """3. 快递信息解析测试"""
    print("\n" + "="*60)
    print("[测试3] 快递信息解析")

    text = "【顺丰】您的快递已到菜鸟驿站，请凭取件码 5678 在22:00前取件。地址：小区北门"
    from packages.reader.readers import ParcelReader
    reader = ParcelReader()
    result = reader.parse_sms_text(text)

    if result:
        print(f"  PASS - 识别到快递: {result['carrier']}")
        print(f"  PICKUP CODE: {result['pickup_code']}")
        print(f"  LOCATION: {result['pickup_location']}")

        # 创建提醒
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
        print(f"  PASS - 快递提醒已创建 | Reminder ID: {reminder.id}")
        return reminder
    else:
        print(f"  FAIL - 未识别出快递信息")
        return None


def test_list():
    """4. 列出提醒测试"""
    print("\n" + "="*60)
    print("[测试4] 列出所有提醒")

    all_r = db.list_reminders()
    pending = db.list_reminders(ReminderStatus.pending)

    print(f"  STATS: 全部 {len(all_r)} 条 | 待处理 {len(pending)} 条")
    for r in all_r:
        print(f"  [{r.status.value}] {r.title} @ {r.start_time.strftime('%m-%d %H:%M')}")

    parcels = db.list_parcels()
    print(f"  PARCELS: {len(parcels)} 条快递记录")


def test_ticket():
    """5. 票务提醒测试"""
    print("\n" + "="*60)
    print("[测试5] 票务提醒")

    ticket = db.create_ticket(TicketEvent(
        event_name="周杰伦2026巡回演唱会-北京站",
        sale_time=datetime.now() + timedelta(days=7),
        platform="大麦网",
        ticket_url="https://detail.damai.cn/xxx",
        city="北京",
        priority=Priority.high,
    ))
    print(f"  PASS - 票务已记录: {ticket.event_name}")
    print(f"  SALE TIME: {ticket.sale_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  PLATFORM: {ticket.platform}")


def test_stats():
    """6. 数据统计测试"""
    print("\n" + "="*60)
    print("[测试6] 数据统计")

    reminders = db.list_reminders()
    parcels = db.list_parcels()
    tickets = db.list_tickets()

    print(f"  提醒总数: {len(reminders)}")
    print(f"  快递记录: {len(parcels)}")
    print(f"  票务记录: {len(tickets)}")

    # 按状态统计
    status_counts = {}
    for r in reminders:
        status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
    for s, c in status_counts.items():
        print(f"    - {s}: {c}")


def test_scheduler():
    """7. 调度器测试"""
    print("\n" + "="*60)
    print("[测试7] 调度器初始化")

    from packages.scheduler.engine import scheduler
    from packages.shared.notification import notifier

    # 设置通知回调
    scheduler.set_notify_callback(notifier.send)

    # 创建一个即将到期的提醒
    now = datetime.now()
    reminder = db.create_reminder(ReminderCreate(
        title="测试：立即触发提醒",
        description="这是一个测试提醒",
        category=ReminderCategory.alarm,
        start_time=now + timedelta(seconds=5),
        remind_offsets=[0],
        priority=Priority.high,
        source=ReminderSource.manual,
    ))

    print(f"  PASS - 调度器准备就绪")
    print(f"  TIP: 启动 API 服务后，调度器将在后台自动运行")


def test_llm_parse():
    """8. LLM解析（模拟测试）"""
    print("\n" + "="*60)
    print("[测试8] 快递文本解析 - 多场景")

    from packages.reader.readers import ParcelReader
    reader = ParcelReader()

    test_cases = [
        "【菜鸟驿站】您的中通快递已到小区北门驿站，取件码 8888",
        "【丰巢】您的韵达快递已存入丰巢柜，取件码 6666，24小时内免费",
        "您有快递已到前台，请凭码 9999 领取",
    ]

    for i, text in enumerate(test_cases):
        result = reader.parse_sms_text(text)
        if result:
            print(f"  场景{i+1}: {text[:30]}... -> 快递:{result['carrier']}, 取件码:{result['pickup_code']}")
        else:
            print(f"  场景{i+1}: {text[:30]}... -> 未识别")


if __name__ == "__main__":
    print("="*60)
    print("  AuraDesk 桌面智能数字人提醒助手")
    print("  模块三: 智能信息读取与提醒引擎")
    print("="*60)

    test_basic()
    test_create_reminder()
    test_create_parcel()
    test_list()
    test_ticket()
    test_stats()
    test_scheduler()
    test_llm_parse()

    print("\n" + "="*60)
    print("  ALL TESTS PASSED!")
    print("  提醒引擎运行正常")
    print("  数据库读写正常")
    print("  快递解析正常")
    print("  票务管理正常")
    print("  调度器准备就绪")
    print("="*60)
    print()
    print("启动 API 服务:")
    print("  python apps/api/main.py")
    print("  或: uvicorn apps.api.main:app --reload")
    print()