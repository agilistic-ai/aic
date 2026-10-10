# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import fcntl
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path


def backup(state, destination, release_id, *, sources=None):
    state, destination = Path(state), Path(destination)
    with (state / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        destination.mkdir(mode=0o700, parents=True, exist_ok=False)
        for name in ("jobs.sqlite", "bookings.sqlite", "checkpoints.sqlite"):
            source = sqlite3.connect((state / name).resolve().as_uri() + "?mode=ro", uri=True)
            target = sqlite3.connect(destination / name)
            try:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                    raise RuntimeError("Backup integrity check failed.")
            finally:
                target.close()
                source.close()
        shutil.copytree(state / "knowledge", destination / "knowledge")
        if sources is not None:
            shutil.copytree(sources, destination / "sources")
        if (state / "usage.jsonl").exists():
            shutil.copy2(state / "usage.jsonl", destination / "usage.jsonl")
        hashes = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(destination.rglob("*")) if p.is_file()}
        (destination / "backup.json").write_text(json.dumps(
            {"release": release_id, "files": hashes}, indent=2))


def restore(snapshot, destination):
    """Validate and copy to a new isolated directory; never start a worker."""
    snapshot, destination = Path(snapshot).resolve(), Path(destination).resolve()
    manifest = json.loads((snapshot / "backup.json").read_text())
    files = {}
    for path in snapshot.rglob("*"):
        if path.is_symlink():
            raise ValueError("Backup symlinks aren't supported.")
        if path.is_file() and path.name != "backup.json":
            files[path.relative_to(snapshot).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if files != manifest["files"] or not {"jobs.sqlite", "bookings.sqlite", "checkpoints.sqlite", "knowledge/index.json"} <= files.keys():
        raise ValueError("Backup hashes or required files don't match.")
    for name in ("jobs.sqlite", "bookings.sqlite", "checkpoints.sqlite"):
        with sqlite3.connect((snapshot / name).as_uri() + "?mode=ro", uri=True) as db:
            if db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("Restored database failed integrity validation.")
    if destination == snapshot or snapshot in destination.parents:
        raise ValueError("Restore destination must be outside the backup.")
    shutil.copytree(snapshot, destination)
    destination.chmod(0o700)
    return {"directory": str(destination), "release": manifest["release"], "actions_resumed": False}
