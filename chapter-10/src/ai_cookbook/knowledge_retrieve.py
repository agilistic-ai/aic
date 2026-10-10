# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import re


def terms(text):
    stop = {"the", "a", "an", "is", "are", "was", "what", "which", "can",
            "i", "we", "of", "to", "for", "on", "in", "and", "at"}
    return set(re.findall(r"\w+", text.casefold())) - stop


def retrieve(question, candidates, embed, *, method="hybrid", limit=8):
    if method not in {"keyword", "dense", "hybrid"}:
        raise ValueError("Unknown retrieval method.")
    if not candidates:
        return []
    lookup = {p["id"]: p for p in candidates}
    query_terms = terms(question)
    lexical = {p["id"]: len(query_terms & terms(p["title"] + " " + p["text"]))
               for p in candidates}
    ranks = []
    if method != "dense":
        ranks.append(sorted((key for key in lookup if lexical[key]),
                            key=lambda key: (-lexical[key], key)))
    if method != "keyword":
        vector = embed.encode([question], query=True)[0]
        scores = {p["id"]: sum(a * b for a, b in zip(vector, p["vector"], strict=True))
                  for p in candidates}
        ranks.append(sorted(lookup, key=lambda key: (-scores[key], key)))
    fused = {}
    for ranking in ranks:
        for rank, key in enumerate(ranking, 1):
            fused[key] = fused.get(key, 0) + 1 / (60 + rank)
    order = sorted(fused, key=lambda key: (-fused[key], key))
    return [lookup[key] for key in order[:limit]]
