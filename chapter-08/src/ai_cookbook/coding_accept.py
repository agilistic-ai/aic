import json
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

from .coding_run import bounded_command
from .coding_snapshot import snapshot


CASES = [
    (20, [{"seats": 3, "status": "confirmed"}], 17, None),
    (20, [{"seats": 2, "status": "confirmed"},
          {"seats": 3, "status": "confirmed"},
          {"seats": 4, "status": "cancelled"}], 15, None),
    (12, [], 12, None),
    (1, [{"seats": 2, "status": "confirmed"}], -1, None),
    (-1, [], None, "ValueError"),
    (True, [], None, "ValueError"),
    (20, [{"seats": 0, "status": "confirmed"}], None, "ValueError"),
    (20, [{"seats": 1, "status": "unknown"}], None, "ValueError"),
]


def scope_check(baseline, candidate):
    if set(baseline) != set(candidate):
        raise ValueError("Files were added or removed.")
    changed = {name for name in baseline if baseline[name]["sha256"] != candidate[name]["sha256"]}
    if not changed or not changed <= {"capacity.py"}:
        raise ValueError("Candidate doesn't match the permitted change area.")
    return sorted(changed)


def assess(workspace, image, baseline):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("Use the inspected local image ID.")
    workspace = Path(workspace).resolve()
    candidate = snapshot(workspace)
    changed = scope_check(baseline, candidate)
    results = []
    for capacity, bookings, value, error in CASES:
        name = "aic-check-" + uuid4().hex
        command = [
            "docker", "run", "--rm", "--pull", "never", "--name", name,
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--memory", "256m", "--cpus", "1",
            "--pids-limit", "32", "--user", f"{os.getuid()}:{os.getgid()}",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=16m",
            "--mount", f"type=bind,src={workspace},dst=/candidate,readonly",
            "--entrypoint", "python", image, "-I", "-B", "/harness/candidate_call.py",
            json.dumps([capacity, bookings]),
        ]
        try:
            observed = bounded_command(command, seconds=10, max_bytes=4096)
        finally:
            cleanup = subprocess.run(["docker", "rm", "-f", name],
                                     capture_output=True, timeout=15)
            if cleanup.returncode and b"no such container" not in cleanup.stderr.lower():
                raise RuntimeError("Acceptance worker cleanup is unverified.")
        expected = {"value": value, "error": error}
        try:
            actual = json.loads(observed["output"])
        except ValueError:
            actual = None
        passed = (observed["returncode"] == 0 and observed["stop_reason"] is None
                  and json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True))
        results.append({"input": [capacity, bookings], "expected": expected,
                        "observed": observed, "passed": passed})
    return {"changed": changed, "cases": results, "passed": all(r["passed"] for r in results),
            "candidate": candidate}
