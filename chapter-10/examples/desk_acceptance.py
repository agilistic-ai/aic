# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json
import os
from time import monotonic, sleep
from urllib.request import Request, urlopen
from uuid import uuid4

TOKEN = os.environ["AIC_TEST_TOKEN"]
BASE = "http://127.0.0.1:8080"


def call(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = Request(BASE + path, data=data, headers={
        "Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def wait(key):
    deadline = monotonic() + 600
    while monotonic() < deadline:
        job = call("/jobs/" + key)
        if job["state"] not in {"queued", "running"}:
            return job
        sleep(1)
    raise TimeoutError("Acceptance job exceeded its deadline.")


body = {"request_key": uuid4().hex, "kind": "booking",
        "text": "Please propose a morning assessment on 2026-11-07."}
key = call("/jobs", body)["id"]
assert call("/jobs", body)["id"] == key
pending = wait(key)
assert pending["state"] == "needs_approval", pending
proposal = pending["result"]["proposal"]
print(json.dumps(proposal, indent=2))
if input("Approve this exact test booking? Type yes: ").strip() != "yes":
    raise SystemExit("Left pending; no booking approved.")
approval = {"fingerprint": pending["result"]["fingerprint"]}
call("/jobs/" + key + "/approve", approval)
call("/jobs/" + key + "/approve", approval)
completed = wait(key)
receipt = completed["result"]
assert completed["state"] == "complete" and receipt["status"] == "confirmed"
assert receipt["request_id"] == key
assert receipt["slot_id"] == proposal["slot_id"]
assert receipt["start_utc"] == proposal["start_utc"]
print("Confirmed booking:", receipt["booking_id"])
