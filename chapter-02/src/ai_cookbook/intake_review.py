# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json
import sqlite3
from pathlib import Path

from .intake_contract import Proposal
from .intake_validate import validate


def connect(path="runs/intake.sqlite3"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS intake (
            key TEXT PRIMARY KEY, source BLOB NOT NULL,
            source_id TEXT NOT NULL, content_hash TEXT NOT NULL,
            recipe TEXT NOT NULL, state TEXT NOT NULL,
            result TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS arrivals (
            source_id TEXT PRIMARY KEY, content_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS recipes (
            key TEXT PRIMARY KEY, manifest TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attempts (
            key TEXT NOT NULL, version INTEGER NOT NULL,
            result TEXT NOT NULL,
            finished_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (key, version)
        );
        CREATE TABLE IF NOT EXISTS reviews (
            key TEXT NOT NULL, version INTEGER NOT NULL,
            reviewer TEXT NOT NULL, reason TEXT NOT NULL,
            before_json TEXT NOT NULL, after_json TEXT NOT NULL,
            reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (key, version)
        );
    """)
    return db


def show(db, key):
    row = db.execute("SELECT * FROM intake WHERE key=?", (key,)).fetchone()
    if row is None:
        raise KeyError(key)
    return {
        "key": key, "version": row["version"],
        "source_id": row["source_id"], "recipe": row["recipe"],
        "state": row["state"],
        "source": row["source"].decode("utf-8", errors="replace"),
        "interpretation": json.loads(row["result"]),
    }


def decide(db, key, edited, *, version, reviewer, reason,
           decision="ready", confirm_multiple_dates=False,
           confirm_duplicate=False):
    if decision not in {"ready", "needs_info", "rejected"}:
        raise ValueError("Unknown review decision.")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("Identify the reviewer and explain the decision.")
    row = db.execute("SELECT * FROM intake WHERE key=?", (key,)).fetchone()
    if row is None or row["version"] != version:
        raise ValueError("Reload this case before reviewing it.")
    if row["state"] not in {"review", "needs_info"}:
        raise ValueError("This case is not awaiting review.")
    before = json.loads(row["result"])
    proposal = Proposal.model_validate(edited)
    record, problems = validate(
        row["source"].decode("utf-8"), proposal,
        set(before["reference_ids"]),
    )
    if confirm_multiple_dates:
        problems = [p for p in problems if p != "multiple_dates"]
    if before.get("duplicate_of") and not confirm_duplicate:
        problems.append("possible_duplicate")
    if decision == "ready" and problems:
        raise ValueError(f"Unresolved validation problems: {problems}")
    after = {
        **before, "state": decision, "proposal": proposal.model_dump(),
        "record": record, "problems": problems,
        "multiple_dates_confirmed": confirm_multiple_dates,
        "duplicate_confirmed": confirm_duplicate,
    }
    encoded = json.dumps(after)
    with db:
        changed = db.execute(
            "UPDATE intake SET state=?, result=?, version=version+1 "
            "WHERE key=? AND version=?",
            (decision, encoded, key, version),
        )
        if changed.rowcount != 1:
            raise ValueError("The case changed; reload it.")
        db.execute(
            "INSERT INTO reviews "
            "(key,version,reviewer,reason,before_json,after_json) "
            "VALUES (?,?,?,?,?,?)",
            (key, version + 1, reviewer, reason, row["result"], encoded),
        )
