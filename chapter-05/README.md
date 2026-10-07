# AI Cookbook — Chapter 5 application

Complete question-to-report application with SQLite execution controls and deterministic SVG charts. Shared provider code is included. Install Python 3.12 and uv separately, then work from this directory:

```bash
uv sync --locked
uv run --locked reporting init --database examples/reporting/workshops.sqlite
```

Initialization uses the trusted sample schema and refuses an existing database. It is a development operation with write access. The question path opens the chosen snapshot read-only and cannot execute writes, attach another database, or read unapproved tables.

For hosted generation, copy `.env.example` to `.env`, supply `AIC_API_KEY`, and run:

```bash
uv run --locked --env-file .env reporting ask "How many places remain at each upcoming workshop?" --database examples/reporting/workshops.sqlite --as-of 2026-11-01 --config config.toml
```

For local generation, start Ollama, install the model in `configs/ollama.toml`, omit the environment-file option, and pass that config. Hosted calls may incur charges. Example model names don't guarantee availability.

A fresh directory under `runs/reporting` contains `report.json` and, for the chapter's remaining-seat result shape, `places.svg`. The JSON retains the question, plan, query parameters, rows, snapshot hash and actual configuration/code metadata. The expected example rows are November with 15 remaining seats and December with 12. Clarify/unsupported outcomes are also saved, without executing SQL. A denied or interrupted query is an error, not an empty successful result.

Use `--output` for another reports directory. When running outside this download, use `--project` to locate its lockfile/default configuration and explicit paths for the database and schema. `--config` overrides `AIC_CONFIG`; endpoint overrides are `AIC_OPENAI_BASE_URL` and `AIC_OLLAMA_HOST`.

The operator selects an already authorized, immutable reporting snapshot. The CLI is not a shared authentication or row-permission service. A single-file hash isn't a backup or a snapshot of a changing WAL database. Keep the schema and snapshot used for evaluation. Prompt wording isn't authorization.

The as-of date must be YYYY-MM-DD. Only confirmed seats consume capacity; contributions are booking-level US cents and NULL amounts remain unknown. Safe SQL can still calculate the wrong measure. Inspect the interpretation and query, and assess meaning separately from execution and plotting success.

```bash
uv run --locked python -m unittest discover -s tests -v
```

Tests include actual SQLite authorization/limits, reference arithmetic, missing contribution amounts, and the complete installed CLI with real OpenAI and Ollama SDKs pointed at scripted local HTTP responses. The smoke run creates and inspects a real SVG chart. No live inference or model-quality evaluation was performed. See `SMOKE_REPORT.md`.

Exit 0 means successful initialization or a saved report, including clarification. Exit 2 means operational or validation failure. There is no automatic model retry, publication, or database modification in the question path. No third-party software or weights are bundled.
