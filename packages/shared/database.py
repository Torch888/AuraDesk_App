"""SQLite 数据库模块"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional, List

from packages.shared.models import (
    Reminder, ReminderCreate, ReminderStatus, ReminderCategory,
    ReminderSource, Priority,
    ParcelTask, ParcelStatus,
    TicketEvent, TicketStatus,
    UserPreference,
)


class Database:
    def __init__(self):
        self._conn: Optional[sqlite3.Connection] = None
        self._db_path: str = ""

    def init_db(self, db_path: str = ""):
        from packages.shared.config import settings
        self._db_path = db_path or settings.db_path
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'custom',
                start_time TEXT NOT NULL,
                remind_offsets TEXT DEFAULT '[-1800,-600,0]',
                priority TEXT DEFAULT 'normal',
                source TEXT DEFAULT 'manual',
                action_url TEXT,
                recurrence TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS parcels (
                id TEXT PRIMARY KEY,
                carrier TEXT,
                pickup_code TEXT,
                pickup_location TEXT,
                reminder_id TEXT,
                raw_text TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                event_name TEXT NOT NULL,
                sale_time TEXT NOT NULL,
                platform TEXT,
                ticket_url TEXT,
                city TEXT,
                priority TEXT DEFAULT 'high',
                status TEXT DEFAULT 'upcoming',
                reminder_id TEXT,
                created_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id TEXT PRIMARY KEY,
                data TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                entity_id TEXT,
                message TEXT,
                created_at TEXT
            )
        """)
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _row_to_reminder(self, row: sqlite3.Row) -> Reminder:
        return Reminder(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            category=ReminderCategory(row["category"]),
            start_time=datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M:%S"),
            remind_offsets=json.loads(row["remind_offsets"]),
            priority=Priority(row["priority"]),
            source=ReminderSource(row["source"]),
            action_url=row["action_url"],
            recurrence=row["recurrence"],
            status=ReminderStatus(row["status"]),
            created_at=datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S"),
            updated_at=datetime.strptime(row["updated_at"], "%Y-%m-%d %H:%M:%S"),
        )

    def _row_to_parcel(self, row: sqlite3.Row) -> ParcelTask:
        return ParcelTask(
            id=row["id"],
            carrier=row["carrier"] or "",
            pickup_code=row["pickup_code"] or "",
            pickup_location=row["pickup_location"] or "",
            reminder_id=row["reminder_id"] or "",
            raw_text=row["raw_text"] or "",
            status=ParcelStatus(row["status"]),
            created_at=datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S"),
        )

    def _row_to_ticket(self, row: sqlite3.Row) -> TicketEvent:
        return TicketEvent(
            id=row["id"],
            event_name=row["event_name"],
            sale_time=datetime.strptime(row["sale_time"], "%Y-%m-%d %H:%M:%S"),
            platform=row["platform"] or "",
            ticket_url=row["ticket_url"],
            city=row["city"] or "",
            priority=Priority(row["priority"]),
            status=TicketStatus(row["status"]),
            reminder_id=row["reminder_id"],
            created_at=datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S"),
        )

    # ─── Reminder CRUD ─────────────────────────────────

    def create_reminder(self, data: ReminderCreate) -> Reminder:
        from packages.shared.models import gen_id
        now = self._now()
        rid = gen_id()
        self._conn.execute(
            """INSERT INTO reminders (id, title, description, category, start_time,
               remind_offsets, priority, source, action_url, recurrence, status,
               created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rid,
                data.title,
                data.description,
                data.category.value,
                data.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                json.dumps(data.remind_offsets),
                data.priority.value,
                data.source.value,
                data.action_url,
                data.recurrence,
                ReminderStatus.pending.value,
                now,
                now,
            ),
        )
        self._conn.commit()
        return Reminder(
            id=rid,
            title=data.title,
            description=data.description,
            category=data.category,
            start_time=data.start_time,
            remind_offsets=data.remind_offsets,
            priority=data.priority,
            source=data.source,
            action_url=data.action_url,
            recurrence=data.recurrence,
            status=ReminderStatus.pending,
            created_at=datetime.strptime(now, "%Y-%m-%d %H:%M:%S"),
            updated_at=datetime.strptime(now, "%Y-%m-%d %H:%M:%S"),
        )

    def get_reminder(self, reminder_id: str) -> Optional[Reminder]:
        row = self._conn.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
        return self._row_to_reminder(row) if row else None

    def list_reminders(self, status: Optional[ReminderStatus] = None, limit: int = 100) -> List[Reminder]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM reminders WHERE status = ? ORDER BY start_time ASC LIMIT ?",
                (status.value, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM reminders ORDER BY start_time ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_reminder(r) for r in rows]

    def update_reminder(self, reminder_id: str, updates: dict):
        now = self._now()
        updates["updated_at"] = now
        if "status" in updates and isinstance(updates["status"], ReminderStatus):
            updates["status"] = updates["status"].value
        if "category" in updates and isinstance(updates["category"], ReminderCategory):
            updates["category"] = updates["category"].value
        if "priority" in updates and isinstance(updates["priority"], Priority):
            updates["priority"] = updates["priority"].value
        if "start_time" in updates and isinstance(updates["start_time"], datetime):
            updates["start_time"] = updates["start_time"].strftime("%Y-%m-%d %H:%M:%S")
        if "remind_offsets" in updates and isinstance(updates["remind_offsets"], list):
            updates["remind_offsets"] = json.dumps(updates["remind_offsets"])
        if "source" in updates and isinstance(updates["source"], ReminderSource):
            updates["source"] = updates["source"].value

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [reminder_id]
        self._conn.execute(
            f"UPDATE reminders SET {set_clause} WHERE id = ?", values
        )
        self._conn.commit()

    def update_reminder_status(self, reminder_id: str, status: ReminderStatus) -> bool:
        row = self._conn.execute(
            "UPDATE reminders SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, self._now(), reminder_id),
        )
        self._conn.commit()
        return row.rowcount > 0

    def delete_reminder(self, reminder_id: str) -> bool:
        row = self._conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self._conn.commit()
        return row.rowcount > 0

    # ─── Parcel CRUD ─────────────────────────────────

    def create_parcel(self, data: ParcelTask):
        now = self._now()
        self._conn.execute(
            """INSERT INTO parcels (id, carrier, pickup_code, pickup_location,
               reminder_id, raw_text, status, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (data.id, data.carrier, data.pickup_code, data.pickup_location,
             data.reminder_id, data.raw_text, data.status.value, now),
        )
        self._conn.commit()

    def list_parcels(self, status: Optional[ParcelStatus] = None) -> List[ParcelTask]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM parcels WHERE status = ? ORDER BY created_at DESC",
                (status.value,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM parcels ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_parcel(r) for r in rows]

    def update_parcel_status(self, parcel_id: str, status: ParcelStatus) -> bool:
        row = self._conn.execute(
            "UPDATE parcels SET status = ? WHERE id = ?",
            (status.value, parcel_id),
        )
        self._conn.commit()
        return row.rowcount > 0

    # ─── Ticket CRUD ─────────────────────────────────

    def create_ticket(self, data: TicketEvent) -> TicketEvent:
        now = self._now()
        self._conn.execute(
            """INSERT INTO tickets (id, event_name, sale_time, platform, ticket_url,
               city, priority, status, reminder_id, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                data.id,
                data.event_name,
                data.sale_time.strftime("%Y-%m-%d %H:%M:%S"),
                data.platform,
                data.ticket_url,
                data.city,
                data.priority.value,
                data.status.value,
                data.reminder_id,
                now,
            ),
        )
        self._conn.commit()
        return TicketEvent(
            id=data.id,
            event_name=data.event_name,
            sale_time=data.sale_time,
            platform=data.platform,
            ticket_url=data.ticket_url,
            city=data.city,
            priority=data.priority,
            status=data.status,
            reminder_id=data.reminder_id,
            created_at=datetime.strptime(now, "%Y-%m-%d %H:%M:%S"),
        )

    def list_tickets(self, status: Optional[TicketStatus] = None) -> List[TicketEvent]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM tickets WHERE status = ? ORDER BY sale_time ASC",
                (status.value,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM tickets ORDER BY sale_time ASC"
            ).fetchall()
        return [self._row_to_ticket(r) for r in rows]

    # ─── Preferences ─────────────────────────────────

    def get_preference(self) -> UserPreference:
        row = self._conn.execute("SELECT * FROM preferences LIMIT 1").fetchone()
        if row:
            data = json.loads(row["data"])
            return UserPreference(**data)
        return UserPreference()

    def save_preference(self, data: UserPreference):
        self._conn.execute("DELETE FROM preferences")
        self._conn.execute(
            "INSERT INTO preferences (id, data) VALUES (?, ?)",
            (data.id, data.model_dump_json()),
        )
        self._conn.commit()

    # ─── Event Log ─────────────────────────────────

    def log_event(self, event_type: str, entity_id: str = "", message: str = ""):
        self._conn.execute(
            "INSERT INTO event_log (event_type, entity_id, message, created_at) VALUES (?,?,?,?)",
            (event_type, entity_id, message, self._now()),
        )
        self._conn.commit()


db = Database()