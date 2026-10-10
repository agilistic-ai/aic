# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .model import generate


class QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["ready", "clarify", "unsupported"]
    interpretation: str
    sql: str | None
    parameters: list[str | int | None]
    question: str | None


SCHEMA = """
SQLite reporting snapshot. Available tables:
workshops(id TEXT PRIMARY KEY, title TEXT, event_date TEXT, capacity INTEGER)
bookings(id TEXT PRIMARY KEY, workshop_id TEXT, seats INTEGER,
         status TEXT, contribution_cents INTEGER NULL)
bookings.workshop_id refers to workshops.id.
Dates are local event calendar dates in YYYY-MM-DD form.
Upcoming means event_date >= the supplied as_of date.
Only status='confirmed' occupies seats; 'cancelled' does not.
One booking can reserve several seats. Empty workshops remain reportable.
Remaining seats = capacity minus confirmed SUM(seats), treating no bookings as 0.
Capacity belongs to the workshop, not to each joined booking row.
Contributions are voluntary donations in US cents, per booking, not per seat.
NULL contribution means unknown; report missingness alongside known totals.
There is no attendance, satisfaction, cancellation reason, or personal data.
"""


def propose(question, as_of, *, settings=None):
    if date.fromisoformat(as_of).isoformat() != as_of:
        raise ValueError("Use YYYY-MM-DD for the as-of date.")
    if not question.strip() or len(question.encode("utf-8")) > 2000:
        raise ValueError("Supply a question within 2,000 UTF-8 bytes.")
    reply = generate(
        "Propose one SQLite SELECT query, or clarify, or report unsupported. "
        "Explain the intended measure and scope in interpretation. "
        "Use ? placeholders with a matching parameters array. "
        "Use only the supplied schema. Never execute SQL. "
        "Only ready has SQL. Non-ready has empty parameters. "
        "Only clarify has a question. Prefer explicit column aliases.\n" + SCHEMA,
        json.dumps({"question": question, "as_of": as_of}),
        QueryPlan.model_json_schema(), max_output_tokens=1536, context_tokens=16384, settings=settings,
    )
    plan = QueryPlan.model_validate_json(reply.text)
    if not plan.interpretation.strip():
        raise ValueError("Missing interpretation.")
    if plan.status == "ready":
        if not plan.sql or not plan.sql.strip() or plan.question is not None:
            raise ValueError("Invalid query proposal.")
    elif plan.sql is not None or plan.parameters:
        raise ValueError("Non-ready proposal contains a query.")
    if plan.status == "clarify":
        if not plan.question or not plan.question.strip():
            raise ValueError("Missing clarification question.")
    elif plan.question is not None:
        raise ValueError("Unexpected clarification question.")
    return plan
