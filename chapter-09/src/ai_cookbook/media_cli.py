"""Prepare, inspect, and review a media intake; no appointment is booked."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from .settings import load_settings
from .media_run import intake
from .media_review import approve_draft, review_interactively, speak_confirmation


def confirmation(reviewed):
    if reviewed.get("state") != "reviewed_intake":
        raise ValueError("Spoken confirmation requires a reviewed intake.")
    return "Your intake is recorded. The next step is choosing an assessment appointment."


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("intake")
    run.add_argument("visual")
    run.add_argument("audio")
    run.add_argument("--consent", action="store_true", help="Confirm consent to the configured processing services")
    run.add_argument("--method", choices=("staged", "joint"), default="staged")
    run.add_argument("--config")
    run.add_argument("--output", default="runs/media")
    for name in ("show", "review", "approve", "speak"):
        command = commands.add_parser(name)
        command.add_argument("record")
        if name == "approve":
            command.add_argument("--fields", required=True, help="JSON file with all confirmed fields")
            command.add_argument("--digest", required=True, help="SHA-256 printed by show")
            command.add_argument("--reviewer", required=True)
            command.add_argument("--questions-resolved", action="store_true")
        if name == "speak":
            command.add_argument("--output", required=True, help="Destination WAV file")
    args = parser.parse_args(argv)
    try:
        if args.action == "intake":
            path, job = intake(args.visual, args.audio, consent=args.consent, method=args.method,
                               output=args.output, settings=load_settings(args.config))
            print(json.dumps({"draft": str(path), "state": job["state"], "fields": job["fields"],
                              "unresolved": job["unresolved"]}, ensure_ascii=False))
        elif args.action == "show":
            raw = Path(args.record).read_bytes()
            print(json.dumps({"sha256": hashlib.sha256(raw).hexdigest(), "draft": json.loads(raw)},
                             ensure_ascii=False, indent=2))
        elif args.action in {"review", "approve"}:
            if args.action == "review":
                path, result = review_interactively(args.record)
            else:
                fields = json.loads(Path(args.fields).read_text(encoding="utf-8"))
                path, result = approve_draft(args.record, fields, expected_digest=args.digest,
                    reviewer=args.reviewer, questions_resolved=args.questions_resolved)
            print(json.dumps({"reviewed": str(path), "confirmation": confirmation(result)}))
        else:
            result = json.loads(Path(args.record).read_text(encoding="utf-8"))
            text = confirmation(result)
            target = Path(args.output)
            if target.suffix.lower() != ".wav":
                raise ValueError("Speech output must have a .wav extension.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
            print(text, flush=True)
            print("Playback uses an AI-generated voice.", flush=True)
            speak_confirmation(text, target)
            print(json.dumps({"audio": str(target)}))
        return 0
    except (ValueError, PermissionError, OSError, KeyError, RuntimeError, EOFError) as exc:
        print(f"Media intake failed: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("Media processing failed; inspect the saved stage record before retrying.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
