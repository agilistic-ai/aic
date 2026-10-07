# Agree on What Crosses the Boundary

**Chapter 11 — illustrative snippet, not a standalone application.**

Use this fragment to give a reviewed assessment request a stable identity and a digest of its exact encoded body. Save both before delivery, and reuse them when reconciling or retrying the same operation.

## What the surrounding application must supply

The host supplies the authenticated actor, case identifier, source revision, and reviewed evidence. Python's standard library supplies the imports. The receiver must authenticate the connection and authorize the named actor; a digest isn't authentication. The proposed `aic.exchange.v1` protocol describes this example, not an existing vendor API. This fragment doesn't provide durable storage or permission to disclose evidence to a partner.

## Chapter snippet

```python
import hashlib
import json
from uuid import uuid4


def encode_envelope(envelope):
    return json.dumps(
        envelope, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def assessment_request(actor, case_id, revision, evidence):
    envelope = {
        "contract": "aic.exchange.v1",
        "request_id": str(uuid4()),
        "actor": actor,
        "operation": "assess",
        "payload": {
            "case_id": case_id,
            "source_revision": revision,
            "evidence": evidence,
        },
    }
    digest = hashlib.sha256(encode_envelope(envelope)).hexdigest()
    return envelope, digest
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.
