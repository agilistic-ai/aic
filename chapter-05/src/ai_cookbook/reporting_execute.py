import hashlib
import json
import sqlite3
from pathlib import Path
from time import monotonic


COLUMNS = {
    "workshops": {"id", "title", "event_date", "capacity", ""},
    "bookings": {"id", "workshop_id", "seats", "status", "contribution_cents", ""},
}
FUNCTIONS = {"sum", "count", "min", "max", "avg", "coalesce", "nullif",
             "round", "abs", "lower", "upper", "date", "strftime"}


def authorize(action, first, second, database, origin):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        permitted_database = database == "main" or (database is None and second == "")
        if permitted_database and second in COLUMNS.get(first, set()):
            return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and second in FUNCTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def execute(database, plan, *, seconds=0.5, max_rows=100):
    if plan.status != "ready":
        raise ValueError("Only a ready proposal can execute.")
    path = Path(database).resolve()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True,
                                 timeout=1, cached_statements=0)
    try:
        connection.execute("PRAGMA query_only = ON")
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 100_000)
        connection.set_authorizer(authorize)
        deadline = monotonic() + seconds
        connection.set_progress_handler(lambda: int(monotonic() >= deadline), 1000)
        cursor = connection.execute(plan.sql, plan.parameters)
        columns = [item[0] for item in cursor.description]
        if len(columns) != len(set(columns)):
            raise ValueError("Use unique result column names.")
        rows = []
        for row in cursor:
            rows.append(list(row))
            if len(rows) > max_rows:
                raise ValueError("Result exceeds the row limit; narrow the question.")
            if len(json.dumps(rows).encode("utf-8")) > 100_000:
                raise ValueError("Result exceeds the byte limit.")
    finally:
        connection.close()
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    if before != after:
        raise ValueError("Reporting snapshot changed during the request.")
    return {"snapshot_sha256": before, "columns": columns, "rows": rows}
