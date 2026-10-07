# Use the Interface That Already Exists

**Chapter 11 — illustrative snippet, not a standalone application.**

Use this fragment when an authorized partner exposes a booking form rather than an integration API. It checks the displayed proposal before the final button, records the attempt, and preserves uncertainty if confirmation doesn't arrive.

## What the surrounding application must supply

The host supplies an authenticated Playwright page already on the agreed confirmation screen, a saved approved proposal, and an asynchronous `record_attempt` callback. That callback must recheck current authority and exact approval, then durably record the impending submission. The example labels and test ID belong to a proposed partner interface. It assumes no earlier autosaving write and a partner-side check that the proposal hasn't changed. The host must verify the observed receipt and reconcile through booking history where available. Receipt text alone isn't confirmation, and a client-reference field prevents duplicates only if the partner enforces it. No site, browser setup, navigation, or remote booking service is supplied here.

## Chapter snippet

```python
from playwright.async_api import Error as BrowserError, expect


async def submit_visible_proposal(page, approved, record_attempt):
    attempted = False
    try:
        await expect(page.get_by_role(
            "heading", name="Confirm assessment", exact=True
        )).to_be_visible()
        await expect(page.get_by_label("Appointment", exact=True)
                     ).to_have_value(approved["slot_label"])
        await expect(page.get_by_label("Customer reference", exact=True)
                     ).to_have_value(approved["customer_reference"])
        await expect(page.get_by_label("Proposal reference", exact=True)
                     ).to_have_value(approved["proposal_reference"])
        await page.get_by_label("Client reference", exact=True).fill(
            approved["request_id"]
        )
        button = page.get_by_role("button", name="Book assessment", exact=True)
        await expect(button).to_be_enabled()
        await record_attempt(approved["request_id"])
        attempted = True
        await button.click(timeout=5000)
        receipt = page.get_by_test_id("booking-receipt")
        await expect(receipt).to_be_visible(timeout=15000)
        return {"status": "observed", "text": await receipt.inner_text()}
    except (BrowserError, AssertionError):
        return {"status": "unresolved" if attempted else "stopped_before_submit"}
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.
