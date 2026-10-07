import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(StrictModel):
    value: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class Proposal(StrictModel):
    category: Literal["repair", "status", "change", "unclear"]
    category_quote: str | None
    reference: Evidence | None
    requested_date: Evidence | None
    problems: list[Literal[
        "ambiguous_category", "conflicting_dates",
        "multiple_requests", "missing_context",
    ]]


def rules_baseline(note: str) -> Proposal | None:
    match = re.fullmatch(
        r"Status for (?P<ref>R-[0-9]{4})[?.]?",
        note.strip(), flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return Proposal(
        category="status", category_quote=match.group(0),
        reference=Evidence(
            value=match["ref"], quote=match.group(0),
        ),
        requested_date=None, problems=[],
    )
