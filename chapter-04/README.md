# AI Cookbook — Chapter 4 application

Complete document search, evidence answering and venue matching. Shared provider code is included; no earlier chapter download is required. Install Python 3.12 and uv separately, then run these commands from the extracted directory:

```bash
uv sync --locked
uv run --locked knowledge index examples/knowledge --method keyword
uv run --locked knowledge search examples/knowledge "November access" --method keyword
```

That keyword path requires no model service. For dense/hybrid retrieval, start Ollama separately, run `ollama pull nomic-embed-text:v1.5`, and rebuild without `--method keyword`. The embedding host defaults to loopback and can be set with `AIC_OLLAMA_HOST`. A changed model digest requires rebuilding the index.

For hosted answers, copy `.env.example` to `.env`, supply your `AIC_API_KEY`, and run:

```bash
uv run --locked --env-file .env knowledge ask examples/knowledge "Is the November workshop accessible?" --config config.toml
```

For local generation omit the environment-file option and select `--config configs/ollama.toml`; its model must be installed separately. `--rerank` adds a model call. `--method keyword` requires no embedding service at query time. Hosted calls may incur charges; configuration examples don't guarantee model availability.

The CLI uses the chapter's fixed demonstration `members` identity. It is a local operator tool, not an authenticated shared service. The service API accepts a trusted identity callback and rechecks current permission and source hashes before model stages and return. It never takes groups from a question. The index contains source text and needs appropriate protection.

For venue matching, create a requirements JSON file containing `{"minimum_capacity":20,"step_free":true,"accessible_toilet":true}`. Use `knowledge match examples/knowledge "cozy room" --needs needs.json --config config.toml`. Only permitted, current catalog entries with `kind: "venue"` and verified qualifying `facts` are considered. The initial workshop collection has no qualifying venues, so `missing` is expected. Unknown facilities never qualify.

Use `--index PATH` consistently for another index. Explicit paths are relative to the current directory. Update a source and version before rebuilding; old chunks become ineligible immediately when either differs. Remove the catalog entry before deleting a document. Failed replacement extraction never restores old chunks. This prototype assumes one index writer.

Exit 0 means successful execution, not verified answer meaning. Indexing returns 1 for per-document failures, while retaining successful documents. Invalid requests or model responses return 2. `missing` is a successful neutral result. An exact citation proves text occurrence, not claim correctness.

```bash
uv run --locked python -m unittest discover -s tests -v
```

Control tests cover extraction, permission revocation during requests, stale sources, citations and matching. The installed CLI smoke test exercises genuine Ollama list/embedding/chat and OpenAI Responses SDK calls against a loopback server, including indexing, reranking and answer validation. No live model or embedding-quality evaluation was performed. See `SMOKE_REPORT.md`.

The chapter's `evidence_coverage` helper is included in `ai_cookbook.evaluation`. Label required document/span pairs before live evaluation and assess evidence coverage separately from answer fidelity. The archive contains no third-party software or model weights.
