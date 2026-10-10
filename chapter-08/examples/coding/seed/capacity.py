# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

def remaining(capacity, bookings):
    if type(capacity) is not int or capacity < 0:
        raise ValueError("Capacity must be a nonnegative integer.")
    for booking in bookings:
        if type(booking["seats"]) is not int or booking["seats"] <= 0:
            raise ValueError("Seats must be a positive integer.")
        if booking["status"] not in {"confirmed", "cancelled"}:
            raise ValueError("Unknown booking status.")
    occupied = sum(1 for booking in bookings if booking["status"] == "confirmed")
    return capacity - occupied
