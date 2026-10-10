# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json
from pathlib import Path
import os
from .desk_paths import STATE, SOURCES

from langgraph.types import Command

from .booking_action import fingerprint
from .booking_loop import propose_booking
from .booking_verify import verify
from .knowledge_service import answer_question


def handle(job, *, store, graph, embed, current_groups):
    actor = job["actor"]
    if job["kind"] == "answer":
        index = json.loads((STATE / "knowledge/index.json").read_text(encoding="utf-8"))
        return answer_question(SOURCES, index, job["text"],
                               lambda: current_groups(actor), embed, rerank=False,
                               method=os.environ.get("AIC_RETRIEVAL_METHOD", "hybrid"))
    if job["kind"] != "booking":
        raise ValueError("Unsupported service-desk operation.")
    store.require_member(actor)
    config = {"configurable": {"thread_id": job["id"]}}
    saved = graph.get_state(config)
    state = saved.values
    if state and state["actor"] != actor:
        raise PermissionError("Job ownership doesn't match its checkpoint.")
    if job["phase"] == "plan":
        if not state:
            proposed = propose_booking(job["text"], store.list_slots)
            if proposed["status"] != "proposal":
                return proposed
            graph.invoke({"request_id": job["id"], "actor": actor,
                          "proposal": proposed["proposal"], "question": job["text"],
                          "trace": proposed["trace"]}, config)
            state = graph.get_state(config).values
        return {"status": "needs_approval", "proposal": state["proposal"],
                "fingerprint": fingerprint(actor, job["id"], state["proposal"])}
    if job["phase"] != "execute" or not state:
        raise ValueError("Execution requires a saved proposal.")
    paused = any(task.interrupts for task in saved.tasks)
    if (not paused and getattr(saved, "next", ()) == ("perform",)
            and state.get("approval_token") != job["approval_token"]):
        graph.update_state(config, {"approval_token": job["approval_token"]}, as_node="approval")
    if paused or getattr(saved, "next", None) != ():
        graph.invoke(Command(resume=job["approval_token"]) if paused else None, config)
    return verify(store, actor, job["id"], state["proposal"])
