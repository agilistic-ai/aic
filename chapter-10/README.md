# Chapter 10 — Small service desk

This standalone application includes the corrected Chapter 4 knowledge components and Chapter 6 booking components. It exposes authenticated HTTP jobs, an exclusive worker supervisor, approval and recovery, protected usage records, and backup/restore commands. Python 3.12 on Linux is required (`fcntl` supplies the worker lock).

Install from this folder with `uv sync --locked`. Set `AIC_API_KEY` for hosted inference. For text inference through an already running Ollama service, select `--config configs/ollama.toml` when initializing. The same model endpoint environment must be supplied when starting the API and worker. No model, container image, or third-party implementation is in this ZIP.

## Local setup

```sh
uv run desk --home runs/desk init
uv run desk --home runs/desk serve
```

In a second terminal, from the same folder:

```sh
uv run desk --home runs/desk worker
```

`init` requires a new destination. It prepares source fixtures and databases, generates separate random bearer tokens for `member` and `reader`, and writes a release record. Tokens are in `runs/desk/member.token` and `runs/desk/reader.token`, with restrictive filesystem permissions. The member can book; the reader can only ask questions. Neither has access to the organizers-only document. Treat the whole deployment directory as protected application data.

The default keyword index needs no embedding service. To use Chapter 4's hybrid retrieval, initialize a different directory with `--method hybrid` after installing the `nomic-embed-text:v1.5` model in Ollama. `AIC_OLLAMA_HOST` selects that service. The index records the embedding digest and checks it at use. This option still uses the selected text model for generated answers.

The supplied `examples/limits.json` is a fixture allowance, not a verified provider price calculation. Pass a reviewed `--limits limits.json` for real use. Its integer ceilings must cover both attempts and the complete permitted planning loop. The queue reserves the whole allowance without refunds; it is not a billing-meter integration. Configure provider-side spending limits separately.

## Use the application

```sh
uv run desk --home runs/desk request answer "What does the November notice say about the accessible toilet?"
uv run desk --home runs/desk request booking "Propose a morning assessment on 2026-11-07 UTC."
uv run desk --home runs/desk status JOB_ID
```

The client prints its request key before sending. Retry a lost submission with the same body and `--request-key` value. An ID returned by the server identifies one actor-bound job. Use `--token-file runs/desk/reader.token` to exercise the second identity, and `--url` if using a different API port. The local server binds only to loopback.

A booking job stops at `needs_approval`. Inspect its exact proposal, then deliberately submit the displayed fingerprint:

```sh
uv run desk --home runs/desk approve JOB_ID --fingerprint DISPLAYED_SHA256
uv run desk --home runs/desk status JOB_ID
```

Repeated submission or approval does not create a second booking. Approval is separate from the initial request. A failed execution can reach `unverified`; this does not mean no booking happened. Inspect the original job and authoritative receipt. For an expired approval, approve that same job and fingerprint again after review. The graph accepts the renewed token at the failed execution step and keeps the original request identity. Never create a replacement request just to retry an uncertain booking.

The supervisor permits two attempts per phase, bounds a child to 240 seconds, and holds a lock that survives in the child if its parent dies. `worker --once` runs at most one attempt under that same lock, which is useful for deterministic operational checks. Do not run the private child entry point yourself.

Completed answers are withheld after permission or source changes. Bookings recheck current membership at commit and read-back. To change authorization, replace `auth.json` atomically using the protected operator workflow; token possession does not preserve revoked access.

## Evidence and releases

Ordinary worker logs contain job identifiers, timings and outcomes. `state/usage.jsonl` retains model/usage metadata without prompt or answer content. A started call without a completion has unknown usage. Failure does not refund the reserved allowance. Source documents, checkpoint state and job results remain protected data.

The release record binds installed code, Python/direct dependency versions, the lockfile, model configuration/endpoint, retrieval method and limits. Local commands refuse to start with a changed record, and each child rechecks it before performing work. Authorization changes remain independent. For deployments, also retain the built image ID and actual local model digests; a mutable model tag is not a pinned weight artifact. Drain paused and pending jobs before changing release identity.

## Backup and isolated restoration

Stop the API and supervisor and ensure their children have exited. Then:

```sh
uv run desk --home runs/desk backup backups/desk-001 --maintenance-confirmed
uv run desk restore backups/desk-001 restored/desk-001
```

Backup captures the three SQLite databases, index, source snapshot and available usage ledger. Restore verifies hashes and SQLite integrity, copies into a new directory, and **does not start or resume actions**. It does not restore credentials or revoked authorization. Keep release artifacts separately. Do not replace a current booking ledger with an older snapshot without reconciling later real actions.

The worker lock detects a surviving worker, but it cannot enforce that the API has stopped. That is why a maintenance pause is required. A backup without its final manifest is incomplete.

## Container deployment

The root Dockerfile and hashed `requirements.txt` provide the book's deployment build. Docker itself is external. Review/pin the Python base-image digest, then build with `docker build -t aic-desk:local .`. Run API and worker from the same image, mounting protected state at `/state`, sources read-only at `/data/knowledge`, and the operator's config/authorization/limits files read-only. Supply `AIC_AUTH_FILE`, `AIC_LIMITS_FILE`, `AIC_RELEASE_ID`, and the model credentials through deployment configuration. Set `AIC_RETRIEVAL_METHOD=keyword` for a keyword index or `hybrid` for a hybrid index. Start the worker with `python -m ai_cookbook.desk_worker`. The API image command runs Uvicorn. Both containers need the same state mount, owned by user 10001.

`AIC_STATE` and `AIC_SOURCES` override the default mounted paths when needed. Use resource limits and a read-only root filesystem. Publish on host loopback initially; an external deployment needs an appropriately configured TLS gateway. Container build/launch was not tested here because Docker was unavailable.

## Smoke verification

```sh
uv run python -m unittest discover -s tests -v
```

The clean-install suite starts the real Uvicorn/FastAPI API and actual worker subprocesses. Genuine provider SDK requests go to a scripted local HTTP service. Tests cover duplicate requests/approvals, cross-user denial, renewed approval after expiry, bounded failed attempts, saved-answer revocation, real LangGraph recovery after commit but before checkpoint, protected usage records, and restoration of the original receipt. No live inference or external booking service is claimed. Bookings use the chapter's real local SQLite service. See SMOKE_REPORT.md for results.
