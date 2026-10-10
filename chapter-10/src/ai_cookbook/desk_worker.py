# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import fcntl
from contextlib import closing, nullcontext
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from .booking_graph import build_graph
from .booking_store import BookingStore
from .desk_auth import CurrentMembers, permissions
from .desk_handle import handle
from .desk_queue import Queue
from .knowledge_index import Embeddings, KeywordIndex
from .desk_paths import STATE, SOURCES



def access_stamp(actor):
    digest = hashlib.sha256(json.dumps(permissions(actor), sort_keys=True).encode())
    paths = [STATE / "knowledge/index.json", *sorted(SOURCES.rglob("*"))]
    for path in paths:
        if path.is_symlink():
            raise ValueError("Source symlinks aren't supported.")
        if path.is_file():
            digest.update(json.dumps([str(path), hashlib.sha256(path.read_bytes()).hexdigest()]).encode())
        elif path == paths[0]:
            raise ValueError("Knowledge index is missing.")
    return digest.hexdigest()


def perform(key):
    if os.environ.get("AIC_HOME"):
        from .desk_setup import configure
        configure(os.environ["AIC_HOME"])
    queue = Queue()
    with queue.connection() as db:
        job = json.loads(db.execute("SELECT body FROM jobs WHERE id=?", (key,)).fetchone()[0])
    os.environ["AIC_JOB_ID"] = key
    os.environ["AIC_USAGE_FILE"] = str(STATE / "usage.jsonl")
    permissions(job["actor"])
    if job["release"] != os.environ["AIC_RELEASE_ID"]:
        raise RuntimeError("Job belongs to a different release.")
    stamp = access_stamp(job["actor"]) if job["kind"] == "answer" else None
    store = BookingStore(str(STATE / "bookings.sqlite"), CurrentMembers())
    embed = None
    if job["kind"] == "answer":
        embed = KeywordIndex() if os.environ.get("AIC_RETRIEVAL_METHOD") == "keyword" else Embeddings()
    with closing(embed) if embed else nullcontext():
        with SqliteSaver.from_conn_string(str(STATE / "checkpoints.sqlite")) as saver:
            graph = build_graph(store, saver)
            result = handle(job, store=store, graph=graph,
                        embed=embed,
                        current_groups=lambda actor: frozenset(permissions(actor)["groups"]))
    if stamp is not None and stamp != access_stamp(job["actor"]):
        raise PermissionError("Knowledge access changed during the request.")
    def finished(saved):
        saved.update(result=result, access_stamp=stamp,
                     state="needs_approval" if result.get("status") == "needs_approval" else "complete")
        saved.pop("approval_token", None)
        saved.pop("error", None)
    queue.edit(key, job["actor"], finished)


def run(*, once=False):
    queue = Queue()
    with (STATE / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            job = queue.take()
            if job is None:
                if once:
                    return
                time.sleep(1)
                continue
            started = time.monotonic()
            child = subprocess.Popen(
                [sys.executable, "-m", "ai_cookbook.desk_worker", job["id"]],
                pass_fds=(lock.fileno(),), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            timed_out = False
            try:
                child.wait(timeout=240)
            except subprocess.TimeoutExpired:
                timed_out = True
                child.kill()
                child.wait()
            print(json.dumps({"job": job["id"], "phase": job["phase"],
                              "attempt": job["tries"], "queue_s": round(time.time() - job["queued_at"] - (time.monotonic() - started), 3),
                              "elapsed_s": round(time.monotonic() - started, 3),
                              "exit": child.returncode, "timeout": timed_out,
                              "release": os.environ["AIC_RELEASE_ID"]}), flush=True)
            if once:
                return


if __name__ == "__main__":
    if len(sys.argv) == 2:
        try:
            perform(sys.argv[1])
        except Exception as error:
            queue = Queue()
            with queue.connection() as db:
                row = db.execute("SELECT body FROM jobs WHERE id=?", (sys.argv[1],)).fetchone()
            if row:
                actor = json.loads(row[0])["actor"]
                queue.edit(sys.argv[1], actor, lambda job: job.update(error=type(error).__name__))
            raise SystemExit(1) from None
    else:
        run()
