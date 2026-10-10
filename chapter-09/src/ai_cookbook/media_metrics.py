# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Retain reported usage without inventing a shared audio/image unit."""
def measure(records, stage, reply):
    if records is None:
        return
    usage = getattr(reply, "usage", None)
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    if usage is None and hasattr(reply, "input_tokens"):
        usage = {"input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens}
    records.append({"stage": stage, "model": getattr(reply, "model", None), "usage": usage})
