# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import hashlib
import json
import os
from pathlib import Path


def directory():
    return json.loads(Path(os.environ["AIC_AUTH_FILE"]).read_text())


def authenticate(token):
    actor = directory()["tokens"].get(hashlib.sha256(token.encode()).hexdigest())
    if actor is None:
        raise PermissionError("Invalid credential.")
    permissions(actor)
    return actor


def permissions(actor):
    record = directory()["actors"].get(actor)
    if record is None:
        raise PermissionError("Access revoked.")
    return record


class CurrentMembers:
    def __contains__(self, actor):
        return permissions(actor).get("can_book") is True
