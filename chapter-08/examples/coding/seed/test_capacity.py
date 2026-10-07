import unittest
from capacity import remaining


class CapacityTests(unittest.TestCase):
    def test_single_seat(self):
        self.assertEqual(remaining(20, [{"seats": 1, "status": "confirmed"}]), 19)

    def test_group_booking(self):
        self.assertEqual(remaining(20, [{"seats": 3, "status": "confirmed"}]), 17)
