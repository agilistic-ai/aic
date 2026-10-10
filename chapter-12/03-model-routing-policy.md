# Spend Model Calls Where They Help

**Chapter 12 — illustrative snippet, not a standalone application.**

Use this policy sketch to select an appropriate processing route from application checks and evaluated task categories. Missing evidence and conflicts take precedence over a convenient rule match.

## What the surrounding application must supply

The host supplies validated observations and a `tested_segment` supported by evaluation evidence. The fragment doesn't measure confidence, call a model, authenticate a user, or implement its named routes. A model's self-reported confidence mustn't populate these inputs. The host implements each route's validation and review requirements. Choosing a larger model never enlarges the application's authority.

## Chapter snippet

```python
def choose_route(*, exact_rule_match, missing_required_source,
                 source_conflict, tested_segment):
    if missing_required_source:
        return "ask_for_information"
    if source_conflict:
        return "human_review"
    if exact_rule_match:
        return "rules"
    if tested_segment == "ordinary_intake":
        return "small_model_then_checks"
    if tested_segment == "complex_intake":
        return "larger_model_then_review"
    return "human_review"
```

The code block is reproduced unchanged from the chapter draft. It is supplied for study and adaptation; this directory has no installable package, CLI, or complete application.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
