# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import re

from pydantic import ValidationError

from .inputs import require_note
from .intake_contract import rules_baseline
from .intake_extract import normalize, propose


def validate(note, proposal, known_refs):
    record, problems = normalize(proposal)
    quote = proposal.category_quote
    if not quote or not quote.strip() or quote not in note:
        problems.append("category_evidence")
    if proposal.category == "unclear":
        problems.append("category_unclear")

    for field in ("reference", "requested_date"):
        evidence = getattr(proposal, field)
        if evidence is not None:
            if (evidence.quote not in note
                    or evidence.value not in evidence.quote):
                problems.append(f"{field}_evidence")

    reference = record["reference"]
    if proposal.category in {"status", "change"} and reference is None:
        problems.append("reference_required")
    if reference is not None and reference not in known_refs:
        problems.append("reference_unknown")

    dates = set(re.findall(r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b", note))
    if len(dates) > 1:
        problems.append("multiple_dates")
    return record, sorted(set(problems))


def process(note, known_refs, *, settings=None):
    note = require_note(note)
    proposal = rules_baseline(note)
    engine = "rules"
    if proposal is None:
        engine = "model"
        try:
            proposal = propose(note, settings=settings)
        except ValidationError:
            proposal = propose(note, repair=True, settings=settings)

    record, problems = validate(note, proposal, known_refs)
    if engine == "model":
        problems.append("human_interpretation_check")
    return {
        "state": "review" if problems else "ready",
        "engine": engine,
        "proposal": proposal.model_dump(),
        "record": record,
        "problems": problems,
    }
