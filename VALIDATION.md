# Repository validation

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
