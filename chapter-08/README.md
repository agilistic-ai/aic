# Chapter 8 — Bounded coding maintenance

This is the complete host application plus its application-owned OpenHands harness, Dockerfile, seed project, dependency lockfiles and acceptance cases. It requires a Linux Docker host for actual agent and candidate execution. It never executes a model-produced candidate on the host and never merges a patch.

From this folder, install the host application with `uv sync --locked` (Python 3.12). The host has no third-party runtime dependencies. The separate harness pins OpenHands SDK and tools to 1.51.0; `requirements.txt` is exported with hashes from its included lockfile. No dependency implementations or images are included.

Build the reviewed harness:

```sh
docker build -t aic-coder:local examples/coding/harness
docker image inspect --format '{{.Id}}' aic-coder:local
```

For repeatable image rebuilds, replace the Dockerfile's Python base tag with your reviewed base-image digest. Record the resulting image ID. Prepare the dedicated local inference service as described in the chapter:

```sh
docker network create --internal aic-coding
docker volume create aic-coding-models
docker run -d --name aic-coding-model -v aic-coding-models:/root/.ollama ollama/ollama
docker exec aic-coding-model ollama pull qwen2.5:7b
docker network connect aic-coding aic-coding-model
docker network disconnect bridge aic-coding-model
```

Model preparation and image building need separate network access. Do not attach production services to the internal worker network. Record the model digest from the prepared service with your release evidence. The local model's ability to repair this fixture is something to evaluate, not a guarantee.

Run using the full inspected `sha256:...` image ID:

```sh
uv run coding --image sha256:REPLACE_WITH_64_HEX_DIGITS --seed examples/coding/seed --output runs/coding
```

The command checks that the image exists locally, copies the seed, runs the isolated agent, checks scope, executes eight independent acceptance cases in fresh networkless workers, and writes a job manifest. It returns 0 for a test-accepted patch, 1 for a completed but rejected attempt, or 2 for an operational failure. A passing job contains `proposal.patch`; it still requires human review. Failed attempts retain available evidence. The seed remains unchanged. Output must be outside the seed directory.

The included seed deliberately fails its group-booking test. A repaired implementation must count seats, preserve cancellation and validation behavior, and leave negative overbooking visible. The agent may change only `capacity.py`. Authoritative cases and expected results live outside its writable workspace.

## Smoke verification and limits

```sh
uv run python -m unittest discover -s tests -v
AIC_CODING_SMOKE_IMAGE=sha256:YOUR_IMAGE_ID uv run python -m unittest discover -s tests -v
```

The default suite runs authored good and bad candidates, validates the generated patch with `git apply --check`, checks timeout/output limits, and runs the installed CLI with a clearly controlled Docker executable fixture. That fixture checks process integration and the arguments sent to Docker; it does not establish container isolation. Only trusted test-authored code is executed locally by those tests.

Docker and a live local model service were unavailable in the build environment. Consequently the real container/agent/acceptance end-to-end test was skipped. The opt-in test above runs that full path on a prepared host. No live model repair is claimed by the default smoke result. The OpenHands harness has its own import/configuration check in `harness_smoke.py`; run it after installing the harness dependencies.
