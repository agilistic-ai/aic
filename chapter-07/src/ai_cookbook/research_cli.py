# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Research, accepted price monitoring, and local notification export."""
import argparse
import json
import sys
from pathlib import Path

from .settings import load_settings
from .research_agent import agent_model
from .research_run import research, FIXTURE_CATALOG
from .research_watch import record_observation
from .research_notify import export_notifications


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run")
    run.add_argument("question")
    run.add_argument("--config")
    run.add_argument("--project", default=".", help="Project folder containing uv.lock")
    run.add_argument("--catalog", help="Administrator-reviewed JSON source catalog")
    run.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    run.add_argument("--output", default="runs/research")
    run.add_argument("--watch", help="Accept this run into a watch database")
    watch = commands.add_parser("watch")
    watch.add_argument("brief", help="Trusted saved brief.json from this application")
    watch.add_argument("--database", default="runs/watch.sqlite")
    export = commands.add_parser("export")
    export.add_argument("--database", default="runs/watch.sqlite")
    export.add_argument("--output", default="runs/notifications")
    args = parser.parse_args(argv)
    try:
        if args.action == "run":
            if args.mode == "live" and not args.catalog:
                raise ValueError("Live research requires a reviewed catalog.")
            catalog = (json.loads(Path(args.catalog).read_text(encoding="utf-8"))
                       if args.catalog else FIXTURE_CATALOG)
            settings = load_settings(args.config)
            model = agent_model(settings.provider, settings.name,
                                settings.timeout_seconds, settings.base_url)
            path, job = research(args.question, model, catalog, mode=args.mode,
                                 output=args.output, settings=settings, config=args.config, project=args.project)
            print(json.dumps({"brief": str(path), "status": job["brief"]["status"]}), flush=True)
            if args.watch:
                event = record_observation(args.watch, job)
                print(json.dumps({"event": event}))
        elif args.action == "watch":
            job = json.loads(Path(args.brief).read_text(encoding="utf-8"))
            print(json.dumps({"event": record_observation(args.database, job)}))
        else:
            if not Path(args.database).is_file():
                raise ValueError("No watch database exists yet.")
            export_notifications(args.database, args.output)
            print(json.dumps({"notifications": args.output}))
        return 0
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(f"Research failed: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("Research failed; no unvalidated briefing was accepted.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
