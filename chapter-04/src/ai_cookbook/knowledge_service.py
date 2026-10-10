# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import hashlib

from .knowledge_answer import Answer, compose, select
from .knowledge_retrieve import retrieve
from .knowledge_sources import load_catalog, source_bytes


def eligible(root, index, groups):
    passages = []
    for doc_id, spec in load_catalog(root).items():
        if not set(spec["groups"]).intersection(groups):
            continue
        try:
            _, raw = source_bytes(root, spec)
        except (OSError, ValueError):
            continue
        digest = hashlib.sha256(raw).hexdigest()
        cached = index["documents"].get(doc_id, {})
        for passage in cached.get("passages", []):
            if passage["version"] == spec["version"] and passage["sha"] == digest:
                passages.append({**passage, "title": spec["title"]})
    return passages


def present(answer, passages):
    cited = {c.passage_id for claim in answer.claims for c in claim.evidence}
    result = answer.model_dump()
    result["sources"] = [
        {key: p[key] for key in ("id", "doc_id", "title", "version", "where")}
        for p in passages if p["id"] in cited
    ]
    if answer.status == "missing":
        result["message"] = (
            "I couldn't find supporting information in the sources "
            "available for this question."
        )
    return result


def answer_question(root, index, question, get_groups, embed, *,
                    method="hybrid", rerank=False, settings=None):
    if not question.strip() or len(question.encode("utf-8")) > 1000:
        raise ValueError("Supply a question within 1,000 UTF-8 bytes.")
    if method != "keyword" and index["embedding_key"] != embed.key:
        raise ValueError("Embedding configuration changed; rebuild the index.")

    def current():
        return eligible(root, index, get_groups())

    def remains_available(selected):
        available = {p["id"] for p in current()}
        return all(p["id"] in available for p in selected)

    def missing():
        return present(Answer(status="missing", claims=[], question=None), [])

    found = retrieve(question, current(), embed, method=method)
    if not remains_available(found):
        return missing()
    context = select(question, found, rerank=rerank, settings=settings)
    if not remains_available(context):
        return missing()
    answer = compose(question, context, settings=settings)
    if not remains_available(context):
        return missing()
    return present(answer, context)


from .knowledge_matching import VenueNeeds, venue_candidates

def match_venues(root, index, question, get_groups, embed, needs, *,
                    method="hybrid", rerank=False, settings=None):
    if not question.strip() or len(question.encode("utf-8")) > 1000:
        raise ValueError("Supply a question within 1,000 UTF-8 bytes.")
    if method != "keyword" and index["embedding_key"] != embed.key:
        raise ValueError("Embedding configuration changed; rebuild the index.")

    def current():
        passages = eligible(root, index, get_groups())
        return venue_candidates(passages, load_catalog(root), needs)

    def remains_available(selected):
        available = {p["id"] for p in current()}
        return all(p["id"] in available for p in selected)

    def missing():
        return present(Answer(status="missing", claims=[], question=None), [])

    found = retrieve(question, current(), embed, method=method)
    if not remains_available(found):
        return missing()
    context = select(question, found, rerank=rerank, settings=settings)
    if not remains_available(context):
        return missing()
    answer = compose(question, context, settings=settings)
    if not remains_available(context):
        return missing()
    return present(answer, context)
