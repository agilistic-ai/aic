# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Deployment-owned paths; set before importing API/worker modules."""
import os
from pathlib import Path
STATE = Path(os.environ.get("AIC_STATE", "/state")).resolve()
SOURCES = Path(os.environ.get("AIC_SOURCES", "/data/knowledge")).resolve()
