# Learn from Corrections Without Learning the Wrong Lesson

**Chapter 12 — illustrative snippet, not a standalone application.**

Use this deterministic split to keep records with the same opaque group identifier together when preparing training, development, and held-out cases. Related examples shouldn't leak across the evaluation boundary.

## What the surrounding application must supply

Choose the grouping unit to match the actual leakage risk, and retain the source revision and correction reason. The function needs only Python's standard library. Hashing gives repeatable assignment, not anonymization, balanced coverage, or a guaranteed proportion for a small dataset. The host owns access controls and dataset storage. Once held-out failures guide tuning, that set becomes development material and a fresh independent check is needed.

## Chapter snippet

```python
from hashlib import sha256


def evaluation_split(group_id):
    raw = ("aic-evaluation-v1:" + group_id).encode("utf-8")
    bucket = int.from_bytes(sha256(raw).digest()[:8], "big") % 10
    if bucket < 2:
        return "held_out"
    if bucket < 4:
        return "development"
    return "training"
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
