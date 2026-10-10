# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import re
import unicodedata


NAMES = ("summary", "rewrite", "variant")


def canonical(text):
    return unicodedata.normalize("NFC", text)


def contains_literal(text, literal):
    return re.search(r"(?<!\w)" + re.escape(canonical(literal))
                     + r"(?!\w)", canonical(text)) is not None


def checks(job):
    flags = []
    if job["failure"] or job["questions"]:
        flags.append("The generation has an unresolved failure or question.")
    if set(job["drafts"]) != set(NAMES):
        flags.append("The package must contain all three versions.")
    source_text = "\n".join(job["sources"].values())
    known_numbers = set(re.findall(r"\b[0-9]+\b", source_text))
    for name in NAMES:
        text = job["drafts"].get(name, "")
        if not isinstance(text, str) or not text.strip():
            flags.append(f"{name}: empty or invalid text.")
            continue
        if len(text.split()) > job["brief"]["word_limits"][name]:
            flags.append(f"{name}: exceeds its word limit.")
        for literal in job["brief"]["required_literals"]:
            if not contains_literal(text, literal):
                flags.append(f"{name}: missing required literal {literal!r}.")
        added = set(re.findall(r"\b[0-9]+\b", text)) - known_numbers
        if added:
            flags.append(f"{name}: new numeric components {sorted(added)}.")
        if name == "variant":
            for term in job["brief"]["variant_terms"].values():
                if not contains_literal(text.casefold(), term.casefold()):
                    flags.append(f"variant: missing approved term {term!r}.")
    return flags
