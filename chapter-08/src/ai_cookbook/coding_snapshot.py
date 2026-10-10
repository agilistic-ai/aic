# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import hashlib
from pathlib import Path


def snapshot(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Snapshot root must be a real directory.")
    files = {}
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Fixture snapshots don't admit symbolic links.")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("Unsupported workspace entry.")
        if path.stat().st_size + total > 100_000:
            raise ValueError("Fixture exceeds its artifact budget.")
        with path.open("rb") as handle:
            raw = handle.read(100_001 - total)
        total += len(raw)
        if len(files) >= 50 or total > 100_000:
            raise ValueError("Fixture exceeds its artifact budget.")
        files[path.relative_to(root).as_posix()] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "text": raw.decode("utf-8"),
        }
    return files
