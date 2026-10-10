# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import sqlite3
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

from ai_cookbook.reporting_data import initialize
from ai_cookbook.reporting_execute import execute
from ai_cookbook.reporting_plan import QueryPlan


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "snapshot.sqlite"
        initialize(self.database, ROOT / "examples/reporting/schema.sql")

    def plan(self, sql, parameters=None):
        return QueryPlan(status="ready", interpretation="Controlled test query.",
                         sql=sql, parameters=parameters or [], question=None)

    def test_reference_result(self):
        sql = (ROOT / "examples/reporting/remaining.sql").read_text()
        result = execute(self.database, self.plan(sql, ["2026-11-01"]))
        self.assertEqual(result["rows"], [
            ["november", "November repair workshop", 15],
            ["december", "December repair workshop", 12],
        ])

    def test_prohibited_operations(self):
        statements = ["DELETE FROM bookings", "PRAGMA table_info(workshops)",
                      "ATTACH DATABASE ':memory:' AS extra", "SELECT sqlite_version()"]
        for sql in statements:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError):
                execute(self.database, self.plan(sql))

    def test_limits(self):
        with self.assertRaises(ValueError):
            execute(self.database, self.plan("SELECT id FROM workshops"), max_rows=1)
        tables = ", ".join(f"bookings AS b{i}" for i in range(8))
        with self.assertRaises(sqlite3.OperationalError):
            execute(self.database, self.plan("SELECT COUNT(*) FROM " + tables), seconds=0)

    def test_valid_sql_can_be_wrong(self):
        result = execute(self.database, self.plan(
            "SELECT COUNT(*) AS occupied FROM bookings "
            "WHERE workshop_id = ? AND status = 'confirmed'", ["november"]))
        self.assertEqual(result["rows"], [[2]])
        self.assertNotEqual(result["rows"], [[5]])
