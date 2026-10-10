# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import ValidationError

from .booking_action import grant, fingerprint
from .booking_graph import build_graph
from .booking_loop import propose_booking
from .booking_mcp_client import reader
from .booking_store import BookingStore
from .booking_verify import verify
from .settings import load_settings


def operate(args):
    actor = "demo-member"
    args.directory.mkdir(parents=True, exist_ok=True)
    store = BookingStore(args.directory / "service.sqlite", {actor})
    with SqliteSaver.from_conn_string(str(args.directory / "checkpoints.sqlite")) as saver:
        graph = build_graph(store, saver)
        if args.action == "start":
            settings = load_settings(args.config)
            proposed = propose_booking(args.value, reader(store.path), settings=settings)
            if proposed["status"] != "proposal":
                print(json.dumps(proposed, indent=2))
                return 0
            request_id = uuid4().hex
            state = {"request_id": request_id, "actor": actor,
                     "proposal": proposed["proposal"], "question": args.value,
                     "trace": proposed["trace"], "model_configuration": asdict(settings)}
            config = {"configurable": {"thread_id": request_id}}
            result = graph.invoke(state, config)
        else:
            request_id = args.value
            config = {"configurable": {"thread_id": request_id}}
            saved = graph.get_state(config)
            state = saved.values
            if not state or state["actor"] != actor:
                raise PermissionError("Job is unavailable.")
            store.require_member(actor)
            if args.action == "show":
                display = {k: state[k] for k in ("request_id", "proposal", "question", "trace", "model_configuration") if k in state}
                display["fingerprint"] = fingerprint(actor, request_id, state["proposal"])
                display["pending_steps"] = list(saved.next)
                print(json.dumps(display, indent=2))
                return 0
            if args.action == "approve":
                if not saved.next or saved.next[0] not in {"approval", "perform"}:
                    raise ValueError("This job is not awaiting approval or renewed execution approval.")
                token = grant(store, actor, request_id, state["proposal"], args.fingerprint)
                if saved.next[0] == "approval":
                    result = graph.invoke(Command(resume=token), config)
                else:
                    graph.update_state(config, {"approval_token": token}, as_node="approval")
                    result = graph.invoke(None, config)
            elif not saved.next:
                result = {"confirmation": verify(store, actor, request_id, state["proposal"])}
            else:
                result = graph.invoke(None, config)
        display = (result["__interrupt__"][0].value if "__interrupt__" in result
                   else result.get("confirmation", {"status": "unverified"}))
        print(json.dumps({"request_id": request_id, "result": display}, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Propose, approve, and verify a fictional assessment booking.")
    parser.add_argument("action", choices=("start", "show", "approve", "recover"))
    parser.add_argument("value")
    parser.add_argument("--fingerprint")
    parser.add_argument("--directory", type=Path, default=Path("runs/booking"))
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    try:
        return operate(args)
    except ValidationError:
        message = "The model or tool response failed validation."
    except (OSError, ValueError, RuntimeError) as error:
        message = str(error)
    except Exception:
        message = "Booking operation interrupted; inspect the saved job and recover using the same request ID."
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
