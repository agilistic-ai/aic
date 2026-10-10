# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import unittest
from capacity import remaining


class CapacityTests(unittest.TestCase):
    def test_single_seat(self):
        self.assertEqual(remaining(20, [{"seats": 1, "status": "confirmed"}]), 19)

    def test_group_booking(self):
        self.assertEqual(remaining(20, [{"seats": 3, "status": "confirmed"}]), 17)
