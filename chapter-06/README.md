# AI Cookbook — Chapter 6 application

A runnable local booking service with a bounded model decision loop, real MCP availability lookup, persistent LangGraph approval, and verified/idempotent booking. It includes shared model code and two fictional one-person UTC slots. No external appointments or notifications are sent.

Install Python 3.12 and uv separately. From this directory:

```bash
uv sync --locked
```

Copy `.env.example` to `.env`, set `AIC_API_KEY`, and select the hosted model in `config.toml`. Start a proposal:

```bash
uv run --locked --env-file .env booking start "Find an assessment on November 7, 2026 before 11:00 UTC" --config config.toml
```

For local inference, start Ollama and install the configured model, omit the environment-file option, and use `--config configs/ollama.toml`. Hosted model calls may incur charges. The MCP server is started automatically as a subprocess of the installed Python; its SDK and LangGraph are real dependencies, not bundled copies. The subprocess receives the booking database path, not the provider key.

A start may clarify/stop, or return a request ID and exact proposal fingerprint. No booking exists yet. Inspect the proposed UTC time and its fit to the request. Replace the placeholders below with the values you inspected:

```bash
uv run --locked booking show REQUEST_ID
uv run --locked booking approve REQUEST_ID --fingerprint INSPECTED_FINGERPRINT
uv run --locked booking recover REQUEST_ID
```

These commands use `runs/booking/service.sqlite` and `checkpoints.sqlite`. Pass `--directory PATH` consistently to select another independent demo service. Approval/recovery need no model key. The CLI's fixed `demo-member` identity is a demonstration, not authentication; a shared service must derive identity and permissions from trusted sessions.

The model can select only observed slots. Its loop makes at most four decisions, with per-call provider timeouts and an iteration deadline. The checkpoint retains the request, observations and model configuration, so `show` can expose the proposal's context without exposing the approval token.

Approval lasts ten minutes and binds actor, stable request ID, slot time/version and operation. Changed availability requires a new proposal; recovery doesn't choose another slot. If a response is lost after the booking commits, recover the same request ID. Repetition returns the existing receipt, even after approval expiry, and verifies it against service storage. Do not start a new request to resolve an uncertain old outcome.

If approval expired before the write, inspect the saved proposal again and run `approve` with its fingerprint. The CLI can renew approval for a failed execution node. It refuses a new approval for a finished job. `recover` on a finished job performs fresh verification and returns the same receipt. Protect both databases: checkpoint state includes approval authority.

Exit 0 means a successful proposal/status/confirmation command. A clarification or budget stop isn't a booking. Exit 2 means validation or operational failure; inspect the saved request before retrying an uncertain effect. This local service has no cancellation, payment, or email capability.

```bash
uv run --locked python -m unittest discover -s tests -v
```

The suite checks real SQLite transactions, concurrent contenders, actor/argument checks, expiry and readback. Installed CLI tests use actual OpenAI/Ollama SDKs against a loopback fixture server, the actual MCP stdio client/server, and actual LangGraph SQLite checkpoints. Recovery is tested after a real local commit followed by a deliberately lost response, and after expired approval in a persisted execution node. No live inference or external booking was performed. See `SMOKE_REPORT.md`.

## Copyright, license, and disclaimer

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

You may run, copy, modify, and redistribute these examples, including as part of commercial applications, under the [MIT License](LICENSE.txt). Keep the copyright and permission notices with copies or substantial portions. Agilistic AI LLC retains copyright; "All Rights Reserved" is subject to this license grant.

The materials come with **no warranty**. Use them at your own risk, review generated outputs and actions, and account for external service charges. Read the [full disclaimer](DISCLAIMER.md) for warranty and liability provisions. Third-party dependencies retain their own licenses and terms.
