import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .desk_paths import STATE


class Queue:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else STATE / "jobs.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, state TEXT, body TEXT);
                CREATE TABLE IF NOT EXISTS spending(day TEXT, actor TEXT, amount INTEGER,
                                                    PRIMARY KEY(day,actor));
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def save(self, db, job):
        db.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?)",
                   (job["id"], job["state"], json.dumps(job)))

    def submit(self, actor, request):
        key = hashlib.sha256((actor + "\0" + request["request_key"]).encode()).hexdigest()
        with self.connection() as db:
            existing = db.execute("SELECT body FROM jobs WHERE id=?", (key,)).fetchone()
            if existing:
                if json.loads(existing[0])["request"] != request:
                    raise ValueError("A request key cannot change its meaning.")
                return key
            if db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0] >= 100:
                raise RuntimeError("Queue capacity reached.")
            limits = json.loads(Path(os.environ["AIC_LIMITS_FILE"]).read_text())
            ceiling = limits["ceiling_microusd"][request["kind"]]
            cap = limits["daily_microusd"]
            if type(ceiling) is not int or type(cap) is not int or not 0 < ceiling <= cap:
                raise ValueError("Invalid spending configuration.")
            day = datetime.now(timezone.utc).date().isoformat()
            row = db.execute("SELECT amount FROM spending WHERE day=? AND actor=?",
                             (day, actor)).fetchone()
            reserved = row[0] if row else 0
            if reserved + ceiling > cap:
                raise RuntimeError("Daily allowance exhausted.")
            db.execute("INSERT OR REPLACE INTO spending VALUES (?,?,?)", (day, actor, reserved + ceiling))
            self.save(db, dict(id=key, actor=actor, request=request,
                               kind=request["kind"], text=request["text"],
                               phase="plan", state="queued", tries=0,
                               queued_at=datetime.now(timezone.utc).timestamp(),
                               release=os.environ["AIC_RELEASE_ID"]))
        return key

    def edit(self, key, actor, change):
        with self.connection() as db:
            row = db.execute("SELECT body FROM jobs WHERE id=?", (key,)).fetchone()
            if row is None or json.loads(row[0])["actor"] != actor:
                raise KeyError("Unknown job.")
            job = json.loads(row[0])
            change(job)
            self.save(db, job)
            return job

    def take(self):
        with self.connection() as db:
            row = db.execute("SELECT body FROM jobs WHERE state IN ('queued','running') ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return None
            job = json.loads(row[0])
            if job["tries"] >= 2:
                job["state"] = "unverified"
                self.save(db, job)
                return None
            job.update(state="running", tries=job["tries"] + 1)
            self.save(db, job)
            return job
