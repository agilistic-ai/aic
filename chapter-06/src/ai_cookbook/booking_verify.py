# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

from .booking_action import Proposal


def verify(store, actor, request_id, proposal):
    proposal = Proposal.model_validate(proposal).model_dump()
    receipt = store.lookup(request_id, actor)
    expected = {"request_id": request_id, "actor": actor,
                "slot_id": proposal["slot_id"], "start_utc": proposal["start_utc"],
                "slot_version": proposal["version"], "status": "confirmed"}
    if receipt is None or any(receipt.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Booking outcome hasn't been verified.")
    return receipt
