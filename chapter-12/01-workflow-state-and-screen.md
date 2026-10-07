# Give the User a Place in the Workflow

**Chapter 12 — illustrative snippet, not a standalone application.**

Use this mapping inside a product's presentation layer so the screen describes what the backend actually knows. A proposal stays visibly unbooked, and an uncertain outcome tells the person that verification is still underway.

## What the surrounding application must supply

The host supplies a saved backend state and a trusted `can_approve` decision. The returned action names aren't endpoints, authorization, or a user interface. The server must independently validate permission and the exact proposal revision on submission. A real UI must handle accessibility and the rest of the product's states. Unsupported states raise an error rather than quietly displaying success.

## Chapter snippet

```python
def case_screen(state, *, can_approve=False):
    if state == "needs_review":
        return {
            "message": "Check the appliance details before we continue.",
            "action": "review_details",
        }
    if state == "needs_approval":
        return {
            "message": "This appointment is a proposal. It isn't booked.",
            "action": "approve_proposal" if can_approve else None,
        }
    if state in {"queued", "running"}:
        return {"message": "We're working on your saved request.",
                "action": "view_progress"}
    if state == "unresolved":
        return {"message": "The booking may have succeeded. We're checking.",
                "action": "check_status"}
    if state == "confirmed":
        return {"message": "Your appointment is confirmed.",
                "action": "view_receipt"}
    raise ValueError("Unsupported case state")
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.
