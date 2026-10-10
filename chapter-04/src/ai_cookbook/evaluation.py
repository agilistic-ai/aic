# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

def evidence_coverage(passages, required):
    if not required:
        return None
    found = sum(
        any(p["doc_id"] == doc_id and quote in p["text"] for p in passages)
        for doc_id, quote in required
    )
    return found / len(required)
