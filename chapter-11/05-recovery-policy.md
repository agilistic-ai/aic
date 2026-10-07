# Recover Across an Ownership Boundary

**Chapter 11 — illustrative snippet, not a standalone application.**

Use this decision helper to choose the next recovery step after a remote action may have succeeded. It returns a policy decision and performs no write.

## What the surrounding application must supply

Observations must come from authenticated, authoritative read-back and comparison with the exact saved proposal. `deduplication_valid` means the partner still guarantees duplicate suppression for the original principal, identity, and body within its retention window. `approval_current` comes from the host's current authorization and approval checks. Neither value is a model's guess. The host provides durable state, scheduling, and operator review. Keep an uncertain operation unresolved when the partner can't supply adequate evidence; don't replace its request identity.

## Chapter snippet

```python
def recovery_step(observation, *, deduplication_valid, approval_current):
    if observation == "completed_match":
        return "record_confirmed"
    if observation == "completed_mismatch":
        return "hold_for_review"
    if observation == "running":
        return "schedule_readback"
    if observation == "rejected_without_action":
        return "record_rejected"
    if observation == "not_found" and deduplication_valid and approval_current:
        return "retry_saved_request"
    return "keep_unresolved"
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.
