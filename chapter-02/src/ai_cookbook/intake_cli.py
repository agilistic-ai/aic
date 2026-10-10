# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Batch intake, inspect its queue, and record versioned review decisions."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

from pydantic import Field, ValidationError

from .intake_batch import run
from .intake_contract import Proposal, StrictModel
from .intake_review import connect, decide, show


class ReviewFile(StrictModel):
    key: str = Field(pattern=r"^[a-f0-9]{64}$")
    version: int = Field(ge=1)
    source: str
    proposal: Proposal


def emit(value):
    print(json.dumps(value, ensure_ascii=False))


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    batch = commands.add_parser("batch", help="Process *.txt files; retain all decisions.")
    batch.add_argument("folder", type=Path)
    batch.add_argument("--project", type=Path, default=Path("."),
                       help="Download folder containing uv.lock and default configuration.")
    batch.add_argument("--config", type=Path)
    batch.add_argument("--references", type=Path)
    batch.add_argument("--database", type=Path)
    batch.add_argument("--retry-failed", action="store_true")
    listing = commands.add_parser("list", help="List waiting cases, or choose a state.")
    listing.add_argument("--state", choices=("all", "pending", "failed", "review",
                                            "needs_info", "ready", "rejected"))
    listing.add_argument("--recipe")
    showing = commands.add_parser("show", help="Read a case and its source.")
    showing.add_argument("key")
    editing = commands.add_parser("review-file", help="Create a version-bound editable proposal.")
    editing.add_argument("key")
    editing.add_argument("--output", type=Path, required=True)
    reviewing = commands.add_parser("decide", help="Submit an edited review file.")
    reviewing.add_argument("file", type=Path)
    reviewing.add_argument("--reviewer", required=True)
    reviewing.add_argument("--reason", required=True)
    reviewing.add_argument("--decision", choices=("ready", "needs_info", "rejected"), default="ready")
    reviewing.add_argument("--confirm-multiple-dates", action="store_true")
    reviewing.add_argument("--confirm-duplicate", action="store_true")
    exporting = commands.add_parser("export-ready", help="Emit ready cases for ONE recipe as JSONL.")
    exporting.add_argument("--recipe", required=True)
    for sub in (listing, showing, editing, reviewing, exporting):
        sub.add_argument("--database", type=Path, default=Path("runs/intake.sqlite3"))
    return cli


def operate(args):
    if args.command == "batch":
        return 1 if run(args.folder, project=args.project, config=args.config,
                        references=args.references, database=args.database,
                        retry_failed=args.retry_failed) else 0
    # A typo in a read/review command must not silently create a new database.
    if not args.database.is_file():
        raise ValueError("Database not found; run a batch first or check --database.")
    with closing(connect(args.database)) as db:
        if args.command == "list":
            for row in db.execute("SELECT * FROM intake ORDER BY source_id, recipe"):
                if args.recipe and row["recipe"] != args.recipe:
                    continue
                states = {args.state} if args.state else {"review", "needs_info"}
                if args.state != "all" and row["state"] not in states:
                    continue
                result = json.loads(row["result"])
                emit({name: row[name] for name in
                      ("key", "source_id", "recipe", "state", "version")} |
                     {"problems": result.get("problems", []), "error": result.get("error")})
        elif args.command in {"show", "review-file"}:
            case = show(db, args.key)
            if args.command == "show":
                emit(case)
            else:
                if case["state"] not in {"review", "needs_info"}:
                    raise ValueError("This case is not awaiting review.")
                edited = ReviewFile(key=case["key"], version=case["version"],
                                    source=case["source"],
                                    proposal=Proposal.model_validate(case["interpretation"]["proposal"]))
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.open("x", encoding="utf-8") as output:
                    output.write(edited.model_dump_json(indent=2) + "\n")
                emit({"review_file": str(args.output), "key": case["key"], "version": case["version"]})
        elif args.command == "decide":
            edited = ReviewFile.model_validate_json(args.file.read_text(encoding="utf-8"))
            case = show(db, edited.key)
            if edited.source != case["source"]:
                raise ValueError("The source is read-only; edit only the proposal.")
            decide(db, edited.key, edited.proposal.model_dump(), version=edited.version,
                   reviewer=args.reviewer, reason=args.reason, decision=args.decision,
                   confirm_multiple_dates=args.confirm_multiple_dates,
                   confirm_duplicate=args.confirm_duplicate)
            emit(show(db, edited.key))
        elif args.command == "export-ready":
            if not db.execute("SELECT 1 FROM recipes WHERE key=?", (args.recipe,)).fetchone():
                raise ValueError("Unknown recipe; copy its fingerprint from the batch output.")
            for row in db.execute("SELECT key FROM intake WHERE state='ready' AND recipe=? "
                                  "ORDER BY source_id", (args.recipe,)):
                # Include the source: structured columns don't capture every restriction.
                emit(show(db, row["key"]))
    return 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return operate(args)
    except ValidationError:
        message = "Review file doesn't match the schema; check its fields and types."
    except KeyError:
        message = "Case not found; copy its key from the queue."
    except (OSError, ValueError) as error:
        message = str(error)
    except sqlite3.Error:
        message = "Database operation failed; check the path and run only one batch worker."
    except KeyboardInterrupt:
        print("Interrupted; rerun to resume pending cases.", file=sys.stderr)
        return 130
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
