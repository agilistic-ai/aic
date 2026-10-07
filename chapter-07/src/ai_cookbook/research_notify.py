import json
import os
import sqlite3
import tempfile
from pathlib import Path


def export_notifications(database, folder="runs/notifications"):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(database)
    try:
        rows = db.execute("SELECT id, payload FROM outbox WHERE delivered = 0 ORDER BY id").fetchall()
        for identity, payload in rows:
            text = json.dumps(json.loads(payload), ensure_ascii=False, indent=2)
            destination = folder / f"{identity}.json"
            if destination.exists():
                if destination.read_text(encoding="utf-8") != text:
                    raise ValueError("Existing notification differs from the outbox.")
            else:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                                 dir=folder, delete=False) as handle:
                    handle.write(text)
                    temporary = Path(handle.name)
                try:
                    os.replace(temporary, destination)
                finally:
                    temporary.unlink(missing_ok=True)
            with db:
                db.execute("UPDATE outbox SET delivered = 1 WHERE id = ?", (identity,))
    finally:
        db.close()
