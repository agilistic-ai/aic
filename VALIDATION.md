# Repository validation

## Copyright and licensing update — October 10, 2026

Added the MIT License and a warranty/liability disclaimer to the repository root, all twelve chapter directories, and Chapter 8's separately usable harness and seed directories. Added notices to the 139 Python files, authored configuration and SQL/HTML examples, Dockerfiles, dependency requirement listings, and repository documentation. Chapters 11–12 remain Markdown-only snippet guides.

All 139 Python files compile and have the same abstract syntax trees as the October 7 import, excluding source locations. All eleven Chapter 11–12 code blocks are unchanged. The 29 TOML files retain their original settings and dependencies, with only license metadata added to the eleven project manifests. All eleven lockfiles and all 32 JSON, JSONL, and plain-text example fixtures remain byte-for-byte unchanged. Local Markdown links and `git diff --check` pass.

Reinstalled all ten application packages with `uv sync --locked --no-editable` on Linux/Python 3.12.14 and reran each existing `unittest` suite. **123 tests passed, 2 optional tests were skipped, and 0 failed.** Per-chapter counts match the import table below. The skipped checks still require the optional real browser and Docker/model-service setup; no live model or paid service testing is claimed.

Each of the ten installed packages reports `License-Expression: MIT` and includes exact copies of `LICENSE.txt` and `DISCLAIMER.md`. Both Dockerfiles now copy these notices into their images; their COPY source paths were verified, but images were not rebuilt. The Chapter 8 seed, including its notices, remains within the existing snapshot size and file-count limits. No application logic or dependency pins changed.

The archive checksums in `SOURCE_ARCHIVES.md` identify the original inputs. They are not checksums for this updated repository.

## Original repository import — October 7, 2026

Checked October 7, 2026 on Linux with Python 3.12.14.

Each Chapter 1–10 project was installed into its own fresh virtual environment using `uv sync --locked --no-editable`. Its installed Python then ran `-m unittest discover -s tests -v`. No application source or dependency pins needed changing. Two transient dependency-download failures succeeded on retry with the same locked versions.

| Chapter | Passed | Skipped | Result |
| --- | ---: | ---: | --- |
| 01 | 9 | 0 | Pass |
| 02 | 12 | 0 | Pass |
| 03 | 12 | 0 | Pass |
| 04 | 22 | 0 | Pass |
| 05 | 6 | 0 | Pass |
| 06 | 15 | 0 | Pass |
| 07 | 11 | 1 | Pass |
| 08 | 11 | 1 | Pass |
| 09 | 11 | 0 | Pass |
| 10 | 14 | 0 | Pass |

**Total: 123 passed, 2 skipped, 0 failures.**

The skipped checks were Chapter 7's opt-in real-browser test and Chapter 8's opt-in Docker/model-service end-to-end test. Their required runtimes weren't prepared for this import. The ordinary suites use scripted local provider responses, real application code, and the installed provider SDKs. They do not establish live model quality, remote account access, or production readiness. No paid inference or real external booking was performed. The original chapter `SMOKE_REPORT.md` files retain the earlier release evidence and limits.

The archive contents were compared byte-for-byte against the repository. Application code, tests, configuration, examples, and lockfiles are unchanged. The Chapter 2–3 READMEs only replace their old extracted-folder names with their repository directory names. All eleven Chapter 11–12 code blocks match the draft sources exactly and remain inside Markdown files. Those directories contain no installable package or runnable application.

Python syntax and supplied JSON, JSONL, and TOML were checked. Repository navigation links resolve locally. The publication tree excludes virtual environments, bytecode, runtime records, actual `.env` files, and generated token files. A targeted credential-pattern scan found no private keys or recognizable provider/GitHub access tokens. The empty `.env.example` templates and explicit smoke-only dummy keys remain as teaching fixtures.

To repeat a chapter's ordinary checks, enter its directory and run:

```sh
uv sync --locked --no-editable
uv run --locked --no-sync python -m unittest discover -s tests -v
```

Follow the individual README for optional runtime checks and live-model evaluation. Chapter 11–12 snippets were syntax-checked, not assembled or advertised as full applications.

---

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

Licensed under the [MIT License](LICENSE.txt). Provided without warranty; use at your own risk. See the [disclaimer](DISCLAIMER.md).
