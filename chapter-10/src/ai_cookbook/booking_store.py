import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path


class BookingStore:
    def __init__(self, path, members):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.members = members
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS slots (
                    id TEXT PRIMARY KEY, start_utc TEXT NOT NULL,
                    version INTEGER NOT NULL, available INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    token TEXT PRIMARY KEY, request_id TEXT NOT NULL,
                    actor TEXT NOT NULL, digest TEXT NOT NULL,
                    expires REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bookings (
                    request_id TEXT PRIMARY KEY, actor TEXT NOT NULL,
                    digest TEXT NOT NULL, receipt TEXT NOT NULL
                );
            """)
            db.executemany("INSERT OR IGNORE INTO slots VALUES (?, ?, 1, 1)", [
                ("s1", "2026-11-07T10:00:00+00:00"),
                ("s2", "2026-11-07T10:30:00+00:00"),
            ])

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def require_member(self, actor):
        if actor not in self.members:
            raise PermissionError("Booking access is unavailable.")

    def list_slots(self, day):
        date.fromisoformat(day)
        with self.connection() as db:
            rows = db.execute(
                "SELECT id, start_utc, version FROM slots "
                "WHERE available = 1 AND substr(start_utc, 1, 10) = ? "
                "ORDER BY start_utc LIMIT 20", (day,)
            ).fetchall()
        return [dict(row) for row in rows]

    def lookup(self, request_id, actor):
        self.require_member(actor)
        with self.connection() as db:
            row = db.execute(
                "SELECT receipt FROM bookings WHERE request_id = ? AND actor = ?",
                (request_id, actor),
            ).fetchone()
        return None if row is None else json.loads(row["receipt"])
