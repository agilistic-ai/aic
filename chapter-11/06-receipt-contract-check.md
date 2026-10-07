# Prove the Contract, Then Survive Its Changes

**Chapter 11 — illustrative snippet, not a standalone application.**

Use this small controlled exercise to check that the local receipt validator rejects a plausible receipt for someone else's request.

## What the surrounding application must supply

This depends on `check_receipt` from `03-remote-api-and-receipts.md` and the saved envelope and digest from `01-request-envelope.md`. It is a local assertion example, not a partner simulator or an integration test suite. It doesn't prove the remote service honors retry keys, retains requests for the agreed window, or preserves its contract across upgrades. Those checks require the actual partner's test environment and agreed fixtures.

## Chapter snippet

```python
def exercise_receipt_binding(envelope, digest):
    receipt = {
        "contract": envelope["contract"],
        "request_id": envelope["request_id"],
        "operation": envelope["operation"],
        "body_sha256": digest,
        "status": "accepted",
    }
    assert check_receipt(receipt, envelope, digest)["status"] == "accepted"
    wrong = dict(receipt, request_id="some-other-request")
    try:
        check_receipt(wrong, envelope, digest)
    except ValueError:
        pass
    else:
        raise AssertionError("Accepted somebody else's receipt")
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.
