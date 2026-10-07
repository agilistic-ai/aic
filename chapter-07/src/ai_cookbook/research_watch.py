import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from .research_brief import Brief, validate_brief


WATCH = "riverside-saturday-three-hours-usd-v1"
PRICE = re.compile(r"Saturday morning hire: USD (\d{1,6})\.(\d{2}) for three hours\.")


def observed_price(job):
    brief = validate_brief(Brief.model_validate(job["brief"]), job["observations"])
    if brief.status != "supported":
        raise ValueError("No accepted price observation.")
    values, sources, observed = set(), set(), []
    for record in job["observations"].values():
        if record["source_id"] not in {"venue", "offer"}:
            continue
        matches = PRICE.findall(record["text"])
        if matches:
            sources.add(record["source_id"])
            values.update(int(whole) * 100 + int(cents) for whole, cents in matches)
            observed.append(datetime.fromisoformat(record["observed_at"]).timestamp())
    if sources != {"venue", "offer"} or len(values) != 1:
        raise ValueError("Price coverage is missing or conflicting.")
    return values.pop(), max(observed)


def record_observation(database, job):
    price, observed_at = observed_price(job)
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(database, timeout=2)
    try:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS watches (
                id TEXT PRIMARY KEY, price INTEGER, observed REAL, sequence INTEGER
            );
            CREATE TABLE IF NOT EXISTS processed (run_id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS outbox (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, delivered INTEGER DEFAULT 0
            );
        """)
        with db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM processed WHERE run_id = ?", (job["run_id"],)).fetchone():
                return None
            db.execute("INSERT INTO processed VALUES (?)", (job["run_id"],))
            prior = db.execute("SELECT price, observed, sequence FROM watches WHERE id = ?",
                               (WATCH,)).fetchone()
            if prior is not None and observed_at <= prior[1]:
                return None
            sequence = 0 if prior is None else prior[2]
            event = None
            if prior is not None and price != prior[0]:
                sequence += 1
                identity = hashlib.sha256(f"{WATCH}:{sequence}".encode()).hexdigest()[:20]
                event = {"event_id": identity, "watch": WATCH, "run_id": job["run_id"],
                         "previous_cents": prior[0], "current_cents": price, "currency": "USD"}
                db.execute("INSERT INTO outbox (id, payload) VALUES (?, ?)",
                           (identity, json.dumps(event)))
            db.execute("INSERT OR REPLACE INTO watches VALUES (?, ?, ?, ?)",
                       (WATCH, price, observed_at, sequence))
            return event
    finally:
        db.close()
