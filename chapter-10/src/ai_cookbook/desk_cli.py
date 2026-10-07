"""Initialize and operate the small service desk."""
import argparse
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default="runs/desk")
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project", default=".")
    init.add_argument("--config")
    init.add_argument("--method", choices=("keyword", "hybrid"), default="keyword")
    init.add_argument("--limits", help="Reviewed allowance configuration; default is a fixture example")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8080)
    worker = sub.add_parser("worker")
    worker.add_argument("--once", action="store_true", help="Process at most one attempt under the worker lock")
    for name in ("request", "status", "approve"):
        p = sub.add_parser(name)
        p.add_argument("--url", default="http://127.0.0.1:8080")
        p.add_argument("--token-file")
        if name == "request":
            p.add_argument("kind", choices=("answer", "booking"));p.add_argument("text")
            p.add_argument("--request-key", default=None)
        else:
            p.add_argument("job_id")
        if name == "approve":
            p.add_argument("--fingerprint", required=True, help="Exact fingerprint displayed for the reviewed proposal")
    backup = sub.add_parser("backup")
    backup.add_argument("destination")
    backup.add_argument("--maintenance-confirmed", action="store_true", help="API and worker, including children, are stopped")
    restore = sub.add_parser("restore")
    restore.add_argument("snapshot");restore.add_argument("destination")
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            from .desk_setup import initialize
            home, release = initialize(args.home, args.project, args.config, method=args.method, limits=args.limits)
            print(json.dumps({"home": str(home), "release": release["id"],
                              "member_token_file": str(home / "member.token"),
                              "reader_token_file": str(home / "reader.token")}))
        elif args.action == "restore":
            from .desk_backup import restore
            result = restore(args.snapshot, args.destination)
            print(json.dumps(result))
        elif args.action in {"request", "status", "approve"}:
            token = Path(args.token_file or Path(args.home) / "member.token").read_text().strip()
            if args.action == "request":
                key = args.request_key or uuid4().hex
                # Print before networking so a lost submission response doesn't lose its retry key.
                print(json.dumps({"request_key": key}), flush=True)
                endpoint, body = "/jobs", {"request_key": key, "kind": args.kind, "text": args.text}
            elif args.action == "approve":
                endpoint, body = f"/jobs/{args.job_id}/approve", {"fingerprint": args.fingerprint}
            else:
                endpoint, body = f"/jobs/{args.job_id}", None
            from urllib.parse import urlsplit
            url = urlsplit(args.url)
            if (url.scheme not in {"https", "http"} or url.username or url.password or url.query or url.fragment
                    or (url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"})):
                raise ValueError("Use HTTPS or a loopback HTTP service address.")
            request = Request(args.url.rstrip("/") + endpoint,
                              data=None if body is None else json.dumps(body).encode(),
                              headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
            with urlopen(request, timeout=15) as response:
                print(json.dumps(json.load(response), ensure_ascii=False))
        else:
            from .desk_setup import configure
            home, release = configure(args.home)
            if args.action == "serve":
                import uvicorn
                uvicorn.run("ai_cookbook.desk_api:app", host="127.0.0.1", port=args.port, workers=1, access_log=False)
            elif args.action == "worker":
                from .desk_worker import run
                run(once=args.once)
            else:
                if not args.maintenance_confirmed:
                    raise ValueError("Confirm the API and worker are stopped before taking a combined backup.")
                from .desk_backup import backup
                backup(home / "state", args.destination, release["id"], sources=home / "sources")
                print(json.dumps({"backup": str(Path(args.destination).resolve()), "release": release["id"]}))
        return 0
    except HTTPError as exc:
        print(f"Service desk rejected the request (HTTP {exc.code}).", file=sys.stderr)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Service desk failed: {exc}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
