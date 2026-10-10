# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Validate saved package structure without changing its fingerprint."""
from typing import Any, Literal
from pydantic import Field

from .editorial import FactPlan
from .editorial_inputs import Brief, StrictModel, read_json, validate_inputs

Name = Literal["summary", "rewrite", "variant"]


class Call(StrictModel):
    stage: str
    seconds: float = Field(ge=0)
    model: str | None
    input_tokens: int | None = Field(ge=0)
    output_tokens: int | None = Field(ge=0)


class Job(StrictModel):
    sources: dict[str, str]
    brief: Brief
    method: Literal["single", "staged"]
    fact_plan: FactPlan | None
    drafts: dict[Name, str]
    questions: list[str]
    calls: list[Call]
    failure: str | None
    failure_stage: str | None = None
    implementation: dict[str, Any] = Field(default_factory=dict)
    revision_of: str | None = None
    revision: dict[str, str] | None = None


def validate_job(job):
    Job.model_validate(job)
    validate_inputs(job["sources"], job["brief"])
    return job


def load_job(path):
    return validate_job(read_json(path, max_bytes=2_000_000))
