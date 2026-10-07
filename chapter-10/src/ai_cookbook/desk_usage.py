"""Protected usage ledger; never stores prompts, answers or credentials."""
import json
import os
from datetime import datetime, timezone
from uuid import uuid4


def emit(event):
    path = os.environ.get("AIC_USAGE_FILE")
    if path:
        event.update(job=os.environ.get("AIC_JOB_ID"), at=datetime.now(timezone.utc).isoformat())
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def started():
    identity = uuid4().hex
    emit({"call": identity, "status": "started", "usage": None})
    return identity


def finished(identity, reply):
    emit({"call": identity, "status": "completed" if reply else "failed",
          "usage": None if reply is None else {
              "model": reply.model, "provider": reply.provider,
              "input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens,
              "elapsed_seconds": reply.elapsed_seconds}})
