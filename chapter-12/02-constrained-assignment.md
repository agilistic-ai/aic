# Turn Requirements into a Problem You Can Solve

**Chapter 12 — illustrative snippet, not a standalone application.**

Use this tiny exhaustive search to show why choosing the first available appointment can lose a feasible plan. Hard eligibility constraints decide which assignments are allowed; preference scores choose among complete feasible assignments.

## What the surrounding application must supply

The host supplies confirmed job-to-slot domains and preference scores. Slots are finite, nonoverlapping, and each accepts one job. This standard-library example returns a proposed assignment or `None` when exhaustive search finds none. It has no search budget and grows rapidly, so it isn't a general scheduling engine. Travel, overlapping appointments, and other real constraints need explicit modeling. Availability must be rechecked by the booking service at commit; this function reserves nothing.

## Chapter snippet

```python
def best_plan(domains, scores):
    order = sorted(domains, key=lambda job: (len(domains[job]), job))
    best, best_score = None, float("-inf")

    def visit(position, chosen, used, total):
        nonlocal best, best_score
        if position == len(order):
            if total > best_score:
                best, best_score = dict(chosen), total
            return
        job = order[position]
        for slot in sorted(set(domains[job])):
            if slot in used:
                continue
            chosen[job] = slot
            visit(position + 1, chosen, used | {slot},
                  total + scores.get((job, slot), 0))
            del chosen[job]

    visit(0, {}, set(), 0)
    return best


domains = {"flexible": ["A10", "B10"], "specialist": ["A10"]}
plan = best_plan(domains, {("flexible", "A10"): 5})
assert plan == {"specialist": "A10", "flexible": "B10"}
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
