# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import hashlib
import json
import time
from uuid import uuid4

from pydantic import Field

from .booking_loop import Strict


class Proposal(Strict):
    slot_id: str
    start_utc: str
    version: int = Field(ge=1)


def fingerprint(actor, request_id, proposal):
    proposal = Proposal.model_validate(proposal).model_dump()
    payload = {"operation": "reserve_assessment_v1", "actor": actor,
               "request_id": request_id, "proposal": proposal}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def grant(store, actor, request_id, proposal, observed_digest, *, now=None):
    store.require_member(actor)
    digest = fingerprint(actor, request_id, proposal)
    if digest != observed_digest:
        raise ValueError("The reviewed proposal changed.")
    token = uuid4().hex
    expires = (time.time() if now is None else now) + 600
    with store.connection() as db:
        db.execute("INSERT INTO approvals VALUES (?, ?, ?, ?, ?)",
                   (token, request_id, actor, digest, expires))
    return token


def commit(store, actor, request_id, proposal, token, *, now=None):
    store.require_member(actor)
    digest = fingerprint(actor, request_id, proposal)
    now = time.time() if now is None else now
    with store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT * FROM bookings WHERE request_id = ?",
                           (request_id,)).fetchone()
        if prior is not None:
            if prior["actor"] != actor or prior["digest"] != digest:
                raise ValueError("Request identifier was reused with different arguments.")
            return json.loads(prior["receipt"])
        approval = db.execute("SELECT * FROM approvals WHERE token = ?", (token,)).fetchone()
        if (approval is None or approval["actor"] != actor
                or approval["request_id"] != request_id or approval["digest"] != digest
                or approval["expires"] <= now):
            raise PermissionError("Approval is absent, changed, or expired.")
        slot = db.execute("SELECT * FROM slots WHERE id = ?",
                          (proposal["slot_id"],)).fetchone()
        if (slot is None or not slot["available"] or slot["version"] != proposal["version"]
                or slot["start_utc"] != proposal["start_utc"]):
            raise ValueError("Appointment changed; obtain a new proposal and approval.")
        db.execute("UPDATE slots SET available = 0, version = version + 1 WHERE id = ?",
                   (proposal["slot_id"],))
        receipt = {"booking_id": uuid4().hex, "request_id": request_id,
                   "actor": actor, "slot_id": proposal["slot_id"],
                   "start_utc": proposal["start_utc"], "slot_version": proposal["version"],
                   "status": "confirmed"}
        db.execute("INSERT INTO bookings VALUES (?, ?, ?, ?)",
                   (request_id, actor, digest, json.dumps(receipt)))
        db.execute("DELETE FROM approvals WHERE token = ?", (token,))
    return receipt
