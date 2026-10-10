# Hand Off Work Through Files

**Chapter 11 — illustrative snippet, not a standalone application.**

Use this fragment to publish complete request bytes into a partner's controlled inbox without exposing a half-written JSON file. A duplicate filename is acceptable only when its bytes match the saved request.

## What the surrounding application must supply

This depends on `encode_envelope` from `01-request-envelope.md`. The existing inbox must be on a local POSIX filesystem supporting hard links and directory synchronization; its writers must be trusted. The receiver must read only published `.json` files and keep its own durable acceptance ledger. This isn't a portable network-share or object-storage adapter. Publication does not prove acceptance or prevent a duplicate downstream booking.

## Chapter snippet

```python
import os
import tempfile
from pathlib import Path
from uuid import UUID


def publish_request(inbox, envelope):
    inbox = Path(inbox)
    identity = str(UUID(envelope["request_id"]))
    destination = inbox / f"{identity}.json"
    raw = encode_envelope(envelope)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=inbox)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if destination.read_bytes() != raw:
                raise ValueError("Request ID already has different content")
        directory = os.open(inbox, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)
    return destination
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
