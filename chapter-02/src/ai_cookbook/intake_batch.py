# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json
import os
from contextlib import closing
from pathlib import Path

from .inputs import MAX_NOTE_BYTES
from .intake_recipe import digest, snapshot
from .intake_review import connect
from .intake_validate import process


def run(folder, *, project=".", config=None, references=None,
        database=None, retry_failed=False):
    project = Path(project).resolve()
    config = config or os.environ.get("AIC_CONFIG") or project / "config.toml"
    references = references or project / "examples/intake/references.json"
    database = database or project / "runs/intake.sqlite3"
    recipe, manifest, known_refs, settings = snapshot(project, config, references)
    paths = sorted(Path(folder).glob("*.txt"))
    if not paths:
        raise ValueError("No intake text files found.")
    failures = 0
    with closing(connect(database)) as db:
        with db:
            db.execute("INSERT OR IGNORE INTO recipes VALUES (?,?)", (recipe, manifest))
        for path in paths:
            source_id = "repair-desk:" + path.name
            try:
                with path.open("rb") as source:
                    raw = source.read(MAX_NOTE_BYTES + 1)
                if len(raw) > MAX_NOTE_BYTES:
                    raise ValueError("Input exceeds 2000 bytes; not imported.")
                content_hash = digest(raw)
                with db:
                    db.execute("INSERT OR IGNORE INTO arrivals VALUES (?,?)",
                               (source_id, content_hash))
                    previous = db.execute(
                        "SELECT content_hash FROM arrivals WHERE source_id=?", (source_id,),
                    ).fetchone()
                    if previous[0] != content_hash:
                        raise ValueError("Source ID reused with different contents.")
                    key = digest(json.dumps([recipe, source_id, content_hash]).encode())
                    db.execute(
                        "INSERT OR IGNORE INTO intake "
                        "(key,source,source_id,content_hash,recipe,state,result) "
                        "VALUES (?,?,?,?,?,'pending','{}')",
                        (key, raw, source_id, content_hash, recipe),
                    )
            except (OSError, ValueError) as error:
                print(json.dumps({"source": source_id, "state": "not_imported",
                                  "error": str(error)}))
                failures += 1
                continue
            row = db.execute("SELECT * FROM intake WHERE key=?", (key,)).fetchone()
            skipped = row["state"] != "pending" and not (
                retry_failed and row["state"] == "failed")
            if skipped:
                result = json.loads(row["result"])
            else:
                try:
                    result = process(raw.decode("utf-8"), known_refs, settings=settings)
                except Exception as error:
                    result = {"state": "failed", "error": type(error).__name__}
                duplicate = db.execute(
                    "SELECT source_id FROM arrivals "
                    "WHERE content_hash=? AND source_id<>? ORDER BY source_id LIMIT 1",
                    (content_hash, source_id),
                ).fetchone()
                if duplicate and result["state"] != "failed":
                    result["state"] = "review"
                    result["problems"].append("possible_duplicate")
                    result["duplicate_of"] = duplicate[0]
                result["reference_ids"] = sorted(known_refs)
                encoded = json.dumps(result)
                with db:
                    changed = db.execute(
                        "UPDATE intake SET state=?,result=?,version=version+1 "
                        "WHERE key=? AND version=?",
                        (result["state"], encoded, key, row["version"]),
                    )
                    if changed.rowcount != 1:
                        raise ValueError("The case changed; rerun the batch.")
                    db.execute("INSERT INTO attempts (key,version,result) VALUES (?,?,?)",
                               (key, row["version"] + 1, encoded))
            failures += int(result["state"] == "failed")
            print(json.dumps({"source": source_id, "key": key, "recipe": recipe,
                              "state": result["state"], "skipped": skipped}))
    return failures


if __name__ == "__main__":
    import sys
    from .intake_cli import main
    raise SystemExit(main(["batch", *sys.argv[1:]]))
