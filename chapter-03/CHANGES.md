# Changes made while assembling the Chapter 3 application

The download includes the shared model adapter, pinned dependencies, provider configurations, and the exact sample source packet and brief. The adapter already supports the context and output allowances; the manuscript's instruction to retrofit them has been removed. Selected settings now flow explicitly through either generation method.

Input files are read with a byte limit and validated before model calls. The source packet and complete editorial brief have an explicit structure. Saved packages and approval receipts are validated when read, producing controlled errors for malformed input. Later payload growth still stops the pipeline rather than silently clipping source material.

The original run wrapper always read configuration and source files from the working directory. Its replacement records the running package, selected configuration and effective endpoint, Python version, installed direct dependency versions, and lockfile. It can run from another directory with an explicit project path.

The review page now displays the fact plan the chapter asks reviewers to inspect. It also shows failure stage, generation-call usage, and revision details. Source and draft markup remains escaped. Saving refuses an existing JSON or HTML path; a non-JSON destination can no longer cause the package to be replaced by its own HTML output.

Commands now cover generation, inspection, draft extraction, corrections, approval, export, and usage comparison. A correction creates a new package with its parent fingerprint and editor's reason. It doesn't carry forward approvals or erase generation questions. The original package remains available.

The chapter preserves its five original main sections and aligns its printed modules and commands with the runnable package. HTML rendering, input/package schemas, CLI wiring, and snapshot support are supplied in the download rather than printed in full. The static AIC outline is unchanged.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
