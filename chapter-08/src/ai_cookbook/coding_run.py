# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json
import os
import re
import signal
import subprocess
import threading
from pathlib import Path
from uuid import uuid4


def bounded_command(arguments, *, seconds, max_bytes=100_000):
    process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=True)
    expired = threading.Event()

    def timeout():
        expired.set()
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    timer = threading.Timer(seconds, timeout)
    timer.start()
    captured = bytearray()
    reason = None
    try:
        while chunk := process.stdout.read1(4096):
            remaining = max_bytes - len(captured)
            captured.extend(chunk[:remaining])
            if len(chunk) > remaining:
                reason = "output_limit"
                os.killpg(process.pid, signal.SIGKILL)
                break
        process.wait()
        if expired.is_set():
            reason = "timeout"
        return {"returncode": process.returncode, "stop_reason": reason,
                "output": captured.decode("utf-8", errors="replace")}
    finally:
        timer.cancel()
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        process.stdout.close()


def launch(workspace, image, evidence):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("Use the inspected local image ID.")
    workspace, evidence = Path(workspace).resolve(), Path(evidence)
    evidence.mkdir(parents=True, exist_ok=False)
    name = "aic-code-" + uuid4().hex
    command = [
        "docker", "run", "--rm", "--pull", "never", "--name", name,
        "--network", "aic-coding", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--cpus", "2", "--memory", "2g",
        "--pids-limit", "128", "--user", f"{os.getuid()}:{os.getgid()}",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
        "--mount", f"type=bind,src={workspace},dst=/work",
        "-e", "AIC_CODING_MODEL=openai/qwen2.5:7b",
        "-e", "AIC_CODING_BASE_URL=http://aic-coding-model:11434/v1",
        "-e", "AIC_CODING_TOKEN=local", image,
    ]
    try:
        result = bounded_command(command, seconds=600)
    finally:
        cleanup = subprocess.run(["docker", "rm", "-f", name],
                                 capture_output=True, timeout=15)
        if cleanup.returncode and b"no such container" not in cleanup.stderr.lower():
            raise RuntimeError("Worker cleanup couldn't be verified.")
    (evidence / "agent-run.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
