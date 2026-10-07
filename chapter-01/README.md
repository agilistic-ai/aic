# AI Cookbook — Chapter 1 application

This application turns one supplied note into a validated task record. It prepares a proposal; it doesn't send messages, create calendar events, reserve rooms, or write to a task service.

The source package is complete. It includes the CLI, reusable Python API, hosted and local adapters, sample inputs, evaluation cases, and smoke tests. Python, third-party dependencies, the Ollama service, and model weights are installed separately and aren't included in this archive.

## Install

Use Python 3.12 and uv. From this directory:

```sh
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

The smoke suite requires no provider credentials or model. It starts a temporary loopback HTTP server and exercises the installed application through the real OpenAI and Ollama SDKs. Those responses are deterministic fixtures, not inference. The suite normally takes about half a minute.

`pyproject.toml` declares the application and direct dependencies. `uv.lock` records the resolved dependency set. `httpx[socks]` supplies the transport extra needed when a SOCKS proxy is configured. No dependencies are vendored here.

You can also install the package with `python -m pip install .` in a virtual environment. The uv path is the reference procedure because it uses the complete lockfile.

## Hosted model

Copy `.env.example` to `.env` and set your own `AIC_API_KEY`. The default `config.toml` selects the previously established GPT-4.1 mini snapshot; access to that model must be available on your account.

```sh
uv run --locked --env-file .env python -m ai_cookbook.note_to_task --input examples/room_request.txt --usage
```

The installed `note-to-task` command is equivalent:

```sh
uv run --locked --env-file .env note-to-task --input examples/room_request.txt --usage
```

Success writes one JSON object to stdout. `--usage` writes a separate JSON metadata record to stderr. The example's deadline is `2026-11-06`; its details must preserve the instruction not to reserve anything. `examples/room_request.expected.json` shows an acceptable answer, not a promise of exact model wording.

Hosted runs send the note to the configured provider and may incur charges. The application requests `store=False`, but that flag is not a general provider-retention guarantee. Its API key is read only when a hosted request is made, so help and local execution work without it.

## Local model

Install and start Ollama separately, then obtain the configured model:

```sh
ollama pull qwen2.5:7b
uv run --locked python -m ai_cookbook.note_to_task --config configs/ollama.toml --input examples/room_request.txt --usage
```

The local endpoint defaults to loopback. `AIC_OLLAMA_HOST` can select an operator-controlled alternative. Set `NO_PROXY` appropriately if a system proxy intercepts loopback requests. Evaluate model quality and latency on your hardware; this archive doesn't contain a model or hardware benchmark.

## Reuse from Python

```python
from ai_cookbook.note_to_task import note_to_task
from ai_cookbook.settings import load_settings

task = note_to_task(
    "Ask Morgan how many people the room holds. No deadline is set.",
    settings=load_settings("configs/ollama.toml"),
)
print(task.model_dump())
```

`note_to_task` returns a validated `Task`. `create_task` returns a `TaskRun` containing that task and the provider's usage metadata. Both use the same validation as the CLI. The shared `generate` adapter accepts the original instructions/note/schema contract, with optional output and context allowances for later recipes.

## Streaming and failures

Add `--stream` to receive the provider response as a stream. The application buffers it and prints only the completed, validated task. A missing terminal event, refusal, truncated output, or validation failure produces no task on stdout. This mode demonstrates safe stream handling; it isn't a token-by-token display.

The input must be nonempty UTF-8 text no longer than 2,000 bytes. The task has exactly `title`, `details`, and `due_date`. A deadline must be a real ISO calendar date explicitly present in the note. Missing or unresolved dates should be `null`. These mechanical checks don't prove the model preserved the note's meaning; review the result before using it.

Exit codes are 0 for a validated result, 2 for configuration/input-file setup errors, 3 for provider or completion failures, and 4 for input/result validation failures. Errors go to stderr without printing provider response bodies or tracebacks. No failed response is silently converted into a plausible task.

The configured timeout is a network timeout, not a hard whole-process deadline. Hosted automatic retries are disabled, and the application adds no retry loop. Failed requests can still consume provider resources. Missing usage is unknown, never assumed to be zero.

`AIC_CONFIG` selects the default configuration path. `--config` overrides it. `AIC_OPENAI_BASE_URL` is an operator-controlled endpoint override, principally for compatible gateways and the local smoke server; never take it from note text. Hosted endpoints require HTTPS except for loopback test endpoints. Actual keys never belong in source files or this archive.

## Evaluate a real model

Run the supplied six-case evaluation set after configuring one of the real providers. Choose a new output filename for each run:

```sh
uv run --locked --env-file .env evaluate-tasks --output runs/hosted-evaluation.jsonl
uv run --locked evaluate-tasks --config configs/ollama.toml --output runs/local-evaluation.jsonl
```

Each run records configuration and dependency identities, returned tasks, latency, and available token counts. Outputs are private working data because they can repeat input content. The runner refuses to overwrite an earlier run.

`mechanical_pass` checks that parsing succeeded and the deadline matches the case. `semantic_review` remains `pending`: review the case's written criterion against the actual result. A zero process exit code isn't a claim that every model interpretation is correct. Do not substitute fixture smoke results for live evaluation results.

## Package layout

`src/ai_cookbook/` contains the application. `examples/` contains the sample notes and acceptable reference output. `configs/` contains the local-provider configuration. `tests/` contains the deterministic application smoke suite. `evals/` contains the live-model cases. `SMOKE_REPORT.md` records what was actually exercised for this release, and `CHANGES.md` explains the relationship to the earlier chapter.
