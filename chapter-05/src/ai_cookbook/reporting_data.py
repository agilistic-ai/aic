# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import sqlite3
from pathlib import Path


def initialize(database, schema):
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    with database.open("xb"):
        pass
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(Path(schema).read_text(encoding="utf-8"))
        connection.commit()
    except Exception:
        connection.close()
        database.unlink()
        raise
    finally:
        connection.close()
