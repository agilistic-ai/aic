# Call a Remote Application and Follow the Job

**Chapter 11 — illustrative snippet, not a standalone application.**

Use these fragments to make one remote submission attempt and check that a returned receipt belongs to the saved operation. An unexpected response stays unresolved so recovery can inspect the same identity.

## What the surrounding application must supply

The host supplies an authenticated HTTPX client with an operator-configured partner base URL, the saved envelope, and its digest. `encode_envelope` comes from `01-request-envelope.md`. The proposed partner must actually implement principal-bound duplicate suppression for `POST /jobs` and status lookup at `GET /requests/{request_id}`. Persist the impending attempt before the call. A scheduler, bounded response handling, polling, and operation-specific result validation remain host responsibilities. An `accepted` receipt is not a completed assessment or confirmed booking; a timeout is not evidence that nothing happened.

## Chapter snippet

```python
import httpx


def check_receipt(data, envelope, digest):
    expected = {
        "contract": envelope["contract"],
        "request_id": envelope["request_id"],
        "operation": envelope["operation"],
        "body_sha256": digest,
    }
    if not isinstance(data, dict):
        raise ValueError("Receipt must be an object")
    if any(data.get(key) != value for key, value in expected.items()):
        raise ValueError("Receipt doesn't match the saved request")
    if data.get("status") not in {"accepted", "running", "completed", "rejected"}:
        raise ValueError("Unknown remote state")
    return data


def submit_once(client, envelope, digest):
    try:
        response = client.post(
            "/jobs", content=encode_envelope(envelope),
            headers={"Content-Type": "application/json",
                     "Idempotency-Key": envelope["request_id"]},
            timeout=httpx.Timeout(15.0, connect=5.0),
            follow_redirects=False,
        )
        if response.status_code not in {200, 202}:
            return {"status": "unresolved", "http_status": response.status_code}
        return check_receipt(response.json(), envelope, digest)
    except (httpx.RequestError, ValueError):
        return {"status": "unresolved"}
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
