# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Validate small UTF-8 source packets and briefs before making a model call."""
import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Nonempty = Annotated[str, Field(min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class WordLimits(StrictModel):
    summary: int = Field(ge=1)
    rewrite: int = Field(ge=1)
    variant: int = Field(ge=1)


class StyleExample(StrictModel):
    source: Nonempty
    rewrite: Nonempty


class Brief(StrictModel):
    purpose: Nonempty
    audience: Nonempty
    tone: Nonempty
    variant_language: Nonempty
    word_limits: WordLimits
    required_literals: list[Nonempty]
    must_keep: list[Nonempty] = Field(min_length=1)
    variant_terms: dict[Nonempty, Nonempty]
    style_example: StyleExample


def read_json(path, *, max_bytes=8000):
    with Path(path).open("rb") as source:
        raw = source.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"JSON file exceeds {max_bytes} bytes.")
    return json.loads(raw.decode("utf-8"))


def validate_inputs(sources, brief):
    if (not isinstance(sources, dict) or not sources
            or any(not isinstance(k, str) or not k.strip()
                   or not isinstance(v, str) or not v.strip() for k, v in sources.items())):
        raise ValueError("Sources must be a nonempty object of source IDs and text.")
    brief = Brief.model_validate(brief).model_dump()
    for value in (brief["purpose"], brief["audience"], brief["tone"], brief["variant_language"],
                  *brief["required_literals"], *brief["must_keep"],
                  *brief["variant_terms"].keys(), *brief["variant_terms"].values(),
                  *brief["style_example"].values()):
        if not value.strip():
            raise ValueError("Brief text must not be blank.")
    if len(json.dumps({"sources": sources, "brief": brief}, ensure_ascii=False).encode("utf-8")) > 8000:
        raise ValueError("The source packet and brief exceed the 8000-byte payload limit.")
    return dict(sources), brief


def load_packet(folder):
    folder = Path(folder)
    return validate_inputs(read_json(folder / "sources.json"), read_json(folder / "brief.json"))
