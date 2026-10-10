# Intake acceptance criteria

The source is the authority for interpretation. Check the proposed category against the whole message, including negation and restrictions. Evidence must quote the source exactly and support the assigned meaning. Literal occurrence alone isn't semantic proof.

Normalize references only by the explicit R-0000 rule. A status or change request needs a known reference; a new repair doesn't. Registry membership isn't proof of the sender's identity. Accept a normalized date only when the source explicitly requests a complete, valid ISO date. Preserve unresolved date wording in the proposal.

Only the complete rules grammar can produce `ready` automatically. Every model proposal must enter review. Unresolved validation problems prevent approval; multiple dates and matching-content warnings each require their own explicit acknowledgement. A reviewer may retain `needs_info` or reject a request. Keep the source, attempts, and before/after review history.

`development.jsonl` contains examples for prompt adjustment. Keep `holdout.jsonl` separate until evaluation. For ambiguous messages, the review note explains acceptable alternatives; matching a single category label isn't the whole assessment.

Run each example as its own uniquely named `.txt` file, then inspect `intake show KEY` against its label. Record the model/configuration fingerprint, correct fields, unresolved cases, and elapsed reviewer time. Compare with the rules-only baseline on the same sources. Changing a prompt after seeing holdout mistakes turns those cases into development data; add fresh holdouts.

The included automated smoke suite tests application controls with scripted HTTP responses. It doesn't measure these semantic acceptance criteria against a live model.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](../../LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](../../DISCLAIMER.md).
