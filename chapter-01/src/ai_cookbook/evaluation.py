# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Live evaluation runner. Semantic judgments remain explicit reviewer work."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys
from time import perf_counter

from .inputs import read_note
from .note_to_task import create_task, metrics
from .settings import load_settings


def evaluate(cases_path, output, settings, *, stream=False):
    cases_path, output = Path(cases_path), Path(output)
    raw = cases_path.read_bytes()
    cases = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not cases or len(cases) > 50 or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Use 1–50 evaluation cases with unique identifiers.")
    # Create before the first call so a bad destination doesn't waste inference.
    output.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with output.open("x", encoding="utf-8") as handle:
        header = {"type": "run", "started_utc": datetime.now(timezone.utc).isoformat(),
                  "application": "aic-chapter-1/1.0.0", "prompt": "note-task-v1",
                  "settings": asdict(settings), "config_sha256": settings.fingerprint,
                  "case_sha256": hashlib.sha256(raw).hexdigest(), "stream": stream,
                  "dependencies": {name: version(name) for name in ("openai", "ollama", "pydantic", "httpx")}}
        handle.write(json.dumps(header) + "\n")
        handle.flush()
        for case in cases:
            started = perf_counter()
            record = {"type": "case", "id": case["id"], "review": case["review"],
                      "semantic_review": "pending", "mechanical_pass": False}
            try:
                note = case["note"] if "note" in case else read_note(cases_path.parent.parent / case["input"])
                run = create_task(note, settings=settings, stream=stream)
                record.update(task=run.task.model_dump(), usage=metrics(run),
                              mechanical_pass=run.task.due_date == case["due_date"])
            except Exception as error:
                record["error_type"] = type(error).__name__
            record["elapsed_seconds"] = round(perf_counter() - started, 4)
            failures += not record["mechanical_pass"]
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run live task evaluations; review meaning separately.")
    parser.add_argument("--cases", type=Path, default=Path("evals/tasks.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args(argv)
    try:
        failures = evaluate(args.cases, args.output, load_settings(args.config), stream=args.stream)
    except (OSError, ValueError, KeyError, TypeError):
        print("Evaluation setup failed; check configuration, cases, and the new output path.", file=sys.stderr)
        return 2
    print(f"Mechanical failures: {failures}. Semantic review is still required.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
