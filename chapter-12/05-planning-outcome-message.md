# Choose the Next Change Deliberately

**Chapter 12 — illustrative snippet, not a standalone application.**

Use this fragment to distinguish a feasible proposal, an unfinished search, and an exhaustively established conflict. That gives a coordinator a more useful next step than a generic failure message.

## What the surrounding application must supply

The host supplies the planner's actual result, its finite eligibility domains, and an honest `search_complete` flag. The planner from `02-constrained-assignment.md` is one possible source. An empty dictionary is a feasible plan for an empty workload, so the code checks `is not None`. This isn't a general conflict-explanation engine. Display identifiers only through authorized, accessible labels, and let the responsible person review constraints; the message neither changes requirements nor authorizes booking.

## Chapter snippet

```python
def planning_message(plan, domains, *, search_complete):
    if plan is not None:
        return "A feasible proposal is ready for review. Nothing is booked yet."
    if not search_complete:
        return "The search stopped before it could settle whether a plan fits."
    blocked = sorted(job for job, choices in domains.items() if not choices)
    if blocked:
        return f"No eligible slot is available for case {blocked[0]}."
    return (
        "Each case has an option, but these cases can't all be assigned "
        "under the current constraints. Review capacity or requirements."
    )
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
