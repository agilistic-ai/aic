# AI Cookbook — Chapter 3 application

This is the complete editorial assistant from Chapter 3. It produces a summary, an English rewrite, and a Spanish variant from the supplied workshop notes. You can compare a single-call method with a fixed four-stage workflow, inspect an HTML review page, save a correction as a new package, and export an individually approved version.

The shared Chapter 1 provider adapter is included. No earlier chapter download is required. The app never publishes or sends the resulting copy.

## Install and generate

Install Python 3.12 and uv separately, then open a terminal in the extracted `chapter-03` directory:

```bash
uv sync --locked
uv run --locked editorial --help
```

For hosted inference, copy `.env.example` to `.env` and supply your own `AIC_API_KEY`. Check the selected model in `config.toml`, then run:

```bash
uv run --locked --env-file .env editorial run examples/editorial --method single
uv run --locked --env-file .env editorial run examples/editorial --method staged
```

These calls require service access and may incur charges. For local inference, start your independently installed Ollama service and pull the model named in `configs/ollama.toml`. Use:

```bash
uv run --locked editorial run examples/editorial --method staged --config configs/ollama.toml
```

The example model names aren't a guarantee of availability on your account or computer. The local request uses a 16,384-token context and a 2,048-token output allowance; the larger context can require additional memory. The staged path makes at most four calls, and stops when a stage fails or raises questions. The single path makes one call. Neither path automatically retries.

The command prints JSON containing the saved package path and review-page path. Every generation uses a new directory under `runs/editorial/`. A zero exit status means the mechanical checks passed; approval is still required. Exit status 1 means a saved package has a generation failure, unresolved question, or mechanical finding. Input/configuration/approval errors return 2; interruption returns 130. An interrupted generation isn't resumable: start another run, which may repeat provider charges.

## Inputs and recorded configuration

The sample folder contains `sources.json` and `brief.json`. Source IDs map to nonblank text. The brief uses the exact fields illustrated in the chapter; unknown fields and invalid types are rejected before generation. Each file is read with an 8,000-byte limit, and every complete model payload, including intermediate material, must fit within 8,000 UTF-8 bytes. A growing fact plan can therefore stop a later stage. Earlier drafts remain available for inspection but can't be approved as a completed package.

`--config` selects the configuration; otherwise `AIC_CONFIG` or the project default applies. `AIC_OPENAI_BASE_URL` and `AIC_OLLAMA_HOST` override endpoints. Keep API keys in the environment. The run records the chosen config, effective endpoint, running package code, lockfile, Python version, and installed direct dependency versions. Add local model digest/runtime information to a `[run]` section when needed; the app preserves that information without discovering or verifying it.

When running from another working directory, set `--project` to the extracted download so the app can locate its lockfile and default config. `--output` chooses the parent directory for new run folders. Explicit relative paths resolve from the current working directory. The earlier invocation `python -m ai_cookbook.editorial_run FOLDER --method staged` is also supported.

## Inspect and approve

Open the generated `run.html` locally. It shows the source packet beside the drafts, the complete brief, mechanical findings, fact plan, questions, and generation-call usage. The wording comparison applies only to the English rewrite; it isn't a cross-language fidelity check.

In the commands below, replace `RUN_JSON` with the actual package path and `INSPECTED_DIGEST` with the fingerprint on the page you inspected. Don't treat a freshly fetched digest as a substitute for reviewing that version.

```bash
uv run --locked editorial show RUN_JSON
uv run --locked editorial approve RUN_JSON rewrite --expected-digest INSPECTED_DIGEST --reviewer Morgan --meaning-reviewed
uv run --locked editorial export RUN_JSON rewrite --output runs/approved_announcement.txt
```

Approval checks the whole package for mechanical findings, then records an attestation for the selected version. Approving the rewrite doesn't approve the summary or translation. After qualified review of the Spanish output, its command is:

```bash
uv run --locked editorial approve RUN_JSON variant --expected-digest INSPECTED_DIGEST --reviewer Morgan --meaning-reviewed --language-reviewed
uv run --locked editorial export RUN_JSON variant --output runs/approved_spanish.txt
```

A name and a flag record the operator's attestation; they don't authenticate a reviewer or establish language competence. Local receipts prevent accidental stale approval. They aren't tamper-proof authorization against someone who can rewrite these files.

Approval receipts and exports never overwrite existing files. Editing the package invalidates its old receipt. A missing or mismatched receipt blocks export without creating the destination. Export prepares a local text file; it does not publish it or mark it as delivered.

## Correct a draft

Copy the draft to a new text file, then edit that file:

```bash
uv run --locked editorial draft RUN_JSON rewrite --output runs/correction.txt
```

Save it as a new package, retaining the original:

```bash
uv run --locked editorial revise RUN_JSON rewrite --text-file runs/correction.txt --expected-digest INSPECTED_DIGEST --editor Morgan --reason "Restored the prior-approval condition."
```

The command prints the new package and review-page paths. Inspect the new page and use its fingerprint for a fresh approval. The revision records its parent fingerprint, editor, reason, and selected draft. It inherits the original generation metrics; no model call occurs during a manual correction. Changing one draft makes a new package, so all versions in that package require new approvals before export.

Corrections can repair a completed package's wording or mechanical findings. They can't clear a failed generation, unresolved source question, or missing version. Resolve the source/brief problem and regenerate in those cases. Preserve source versions and add a new source ID when the underlying facts change.

## Compare and evaluate

```bash
uv run --locked editorial compare SINGLE_RUN_JSON STAGED_RUN_JSON
```

Replace those placeholders with saved package paths. Comparison reports generation calls, elapsed call time, known token usage, and how many calls have unknown usage. It doesn't price the calls, judge fidelity, or include reviewer time. A failed request without usage isn't counted as free; its usage remains unknown.

Use `evals/editorial/criteria.md`, the paired review cases, and the live-generation packets for semantic evaluation. Read sources and qualifications, not just diff highlights. The HTML page shows workflow details, so for a blinded comparison give reviewers only the drafts, common sources, and brief before revealing the method. Record their correction effort separately.

## Run the smoke tests

```bash
uv run --locked python -m unittest discover -s tests -v
```

The tests use genuine installed OpenAI and Ollama SDKs against scripted loopback HTTP responses. They exercise the installed command line, file persistence, review decisions, and export with no provider credentials or model weights. See `SMOKE_REPORT.md` for the completed run and its limits. The fixture text in `tests/fixtures/` is test data, not evidence of model output or qualified translation review.

This ZIP contains application-owned code, tests, examples, and configuration/dependency metadata. It contains no third-party implementation, virtual environment, or model weights.

## Copyright, license, and disclaimer

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

You may run, copy, modify, and redistribute these examples, including as part of commercial applications, under the [MIT License](LICENSE.txt). Keep the copyright and permission notices with copies or substantial portions. Agilistic AI LLC retains copyright; "All Rights Reserved" is subject to this license grant.

The materials come with **no warranty**. Use them at your own risk, review generated outputs and actions, and account for external service charges. Read the [full disclaimer](DISCLAIMER.md) for warranty and liability provisions. Third-party dependencies retain their own licenses and terms.
