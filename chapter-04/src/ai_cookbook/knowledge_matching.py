# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

from pydantic import Field

from .knowledge_answer import Structured


class VenueNeeds(Structured):
    minimum_capacity: int = Field(ge=1)
    step_free: bool
    accessible_toilet: bool


def venue_candidates(passages, catalog, needs):
    accepted = []
    for passage in passages:
        spec = catalog.get(passage["doc_id"], {})
        if spec.get("kind") != "venue" or spec.get("version") != passage["version"]:
            continue
        facts = spec.get("facts", {})
        capacity = facts.get("capacity")
        if type(capacity) is not int or capacity < needs.minimum_capacity:
            continue
        if needs.step_free and facts.get("step_free") is not True:
            continue
        if needs.accessible_toilet and facts.get("accessible_toilet") is not True:
            continue
        accepted.append(passage)
    return accepted
