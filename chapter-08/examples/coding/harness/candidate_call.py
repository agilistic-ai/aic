# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import importlib.util
import json
import sys


capacity, bookings = json.loads(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate", "/candidate/capacity.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    result = {"value": module.remaining(capacity, bookings), "error": None}
except ValueError:
    result = {"value": None, "error": "ValueError"}
print(json.dumps(result, allow_nan=False))
