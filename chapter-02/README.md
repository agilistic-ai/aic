# AI Cookbook — Chapter 2 application

This is the complete repair-desk intake application. It processes a folder of short messages, stores the original input and processing history in SQLite, and provides commands to inspect and review proposed records. It includes the shared Chapter 1 model adapter; the Chapter 1 download isn't required.

A `ready` record is ready for internal routing. This application doesn't change appointments, send messages, or disclose customer records. Every model interpretation needs review. The narrow rules baseline can accept a complete `Status for R-1042?` message after validation.

## Install and try the rules path

Use Python 3.12 and uv, installed separately. From the extracted `chapter-02` directory:

```bash
uv sync --locked
uv run --locked intake batch examples/rules
uv run --locked intake list --state all
```

This example needs no provider key or model service. It uses real application rules and SQLite. It doesn't simulate model inference. The default database is `runs/intake.sqlite3`. Commands emit JSON or JSONL to standard output; errors go to standard error.

## Process the model examples

For hosted inference, copy `.env.example` to `.env` and set your own `AIC_API_KEY`. Review the provider/model settings in `config.toml`, then run:

```bash
uv run --locked --env-file .env intake batch examples/intake
```

The hosted call requires service access and may incur charges. For local inference, start an independently installed Ollama service and pull the model named in `configs/ollama.toml`, then run:

```bash
uv run --locked intake batch examples/intake --config configs/ollama.toml
```

Both configurations are examples, not a promise that a particular model is available on your account or computer. `AIC_CONFIG` supplies the config path when `--config` is omitted. `AIC_OPENAI_BASE_URL` and `AIC_OLLAMA_HOST` override endpoints. API keys stay outside configuration snapshots.

Input files must be UTF-8 `.txt` files of at most 2,000 bytes. The importer reads at most 2,001 bytes. Oversized or unreadable files produce `not_imported` output and remain in the input folder; no truncated source is stored. Accepted-size files with invalid UTF-8 or empty content are retained as failed cases. Later files still run.

## Review a case

List waiting cases and copy the full case key from the output. In the following commands, replace `CASE_KEY` with that value:

```bash
uv run --locked intake list
uv run --locked intake show CASE_KEY
uv run --locked intake review-file CASE_KEY --output runs/review.json
```

Read the complete source, including any restriction the structured fields don't express. Edit only `proposal` in `runs/review.json`; retain its key, version, and source. The review file won't overwrite an existing file. Use a fresh filename for the next case.

```bash
uv run --locked intake decide runs/review.json --reviewer Morgan --reason "Checked the source and requested date."
```

Approval revalidates the edited proposal. Add `--confirm-multiple-dates` only after resolving the date warning. A `possible_duplicate` warning independently requires `--confirm-duplicate` to accept both messages as separate work; otherwise reject the duplicate or leave it waiting. Neither flag bypasses an unknown reference, invented evidence, or unresolved date.

Use `--decision needs_info` to retain an unresolved case, or `--decision rejected` to close it without accepting it. Explain the decision in `--reason`. A new follow-up message needs its own filename; relate it to the earlier case in the review reason. A stale review file is refused. Export a fresh review file after another decision changes the case.

The operator supplies the reviewer name in this local prototype. That isn't authenticated identity. The database retains the before/after interpretation, reason, reviewer, and version for each committed decision.

## Resume, retry, and export

An unchanged rerun skips completed cases, including those awaiting review. Failed cases require an explicit retry:

```bash
uv run --locked --env-file .env intake batch examples/intake --retry-failed
uv run --locked intake list --state failed
```

The namespace is one repair desk per database. A filename identifies a message across folders. Reusing it with different bytes is refused; renaming identical text creates another arrival and a duplicate warning. The same source can have separate processing versions when its recipe changes. Run one batch worker at a time. A request interrupted before its result is committed may be sent again on resume, so provider billing isn't exactly-once.

The recipe manifest includes running package code, lockfile, model configuration, effective endpoint, reference registry, Python version, and installed direct dependency versions. Add local model weight/runtime identifiers to a `[run]` section in the config when needed; the app records them but doesn't verify or discover them. A fingerprint identifies recorded inputs to a run, not reproducible model behavior. API keys and the entire environment aren't recorded.

Copy the intended fingerprint from the batch or list output and replace `RECIPE_SHA256` below:

```bash
uv run --locked intake export-ready --recipe RECIPE_SHA256 > runs/ready.jsonl
```

The export selects only `ready` cases from that recipe and includes their original source. Don't dispatch every historical recipe. Exporting doesn't mark work as delivered or perform any downstream action.

For another inbox or location, use `--database` consistently on all commands. `batch` also accepts `--references` and `--project`. `--project` identifies the extracted download containing `uv.lock` and the default config/reference files; it does not change the working directory. Explicit relative paths resolve against the current working directory. The code fingerprint always reads the running installed package. `python -m ai_cookbook.intake_batch FOLDER` remains available for the chapter's earlier module invocation.

Exit status is 0 when the command succeeds, 1 when a batch contains failed or not-imported files, and 2 for configuration/usage/review errors. A waiting review case isn't a failed batch. Interruption returns 130. Use `intake show CASE_KEY` to inspect a failed case's error type.

## Smoke tests and interpretation evaluation

```bash
uv run --locked python -m unittest discover -s tests -v
```

The tests use actual installed OpenAI and Ollama SDKs against a loopback HTTP fixture server, then exercise the installed command line and SQLite review workflow. They need no credentials, model weights, or paid calls. The fixture scripts responses; it does not test model quality. See `SMOKE_REPORT.md` for the completed run and limits.

The labeled development and holdout cases are in `evals/intake/`. Follow `criteria.md` to compare interpretations and reviewer effort against a real configured model. These labels are provided for evaluation; they aren't claims of live-model results.

This archive contains application-owned source, tests, configuration templates, and examples. Dependency pins and `uv.lock` describe separately installed packages; no third-party implementation or model weights are bundled.
