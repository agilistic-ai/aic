# Chapter 7 — Research and price monitoring

Python 3.12 and `uv` are required. From this folder, install the locked dependencies with `uv sync --locked`. For dynamic pages, install Chromium separately with `uv run playwright install chromium`. Browser binaries are not included. Run rendering as a non-root user on a host that supports Chromium's sandbox; the application does not disable it.

Set `AIC_API_KEY` for hosted inference. Configuration comes from `config.toml`, `AIC_CONFIG`, or `--config`. For a running Ollama service and an installed tool-capable model, use `--config configs/ollama.toml`. `AIC_OPENAI_BASE_URL` and `AIC_OLLAMA_HOST` select compatible service endpoints. No model is downloaded automatically. The local agent requests a 32,768-token context.

In one terminal, serve only the included fixtures:

```sh
uv run python -m http.server 8765 --bind 127.0.0.1 --directory examples/research/site
```

In a second terminal, from the application folder:

```sh
uv run research run "What is Riverside Hall's published Saturday morning hire price and what conditions apply?" --watch runs/watch.sqlite
uv run research export --database runs/watch.sqlite --output runs/notifications
```

The first accepted run establishes the baseline. Change both fixture prices from 80.00 to 70.00 and rerun to generate one local notification. Changing only a headline produces no price event. A conflict leaves the baseline untouched. `run` prints the saved brief path before watch acceptance, so an acceptance failure still has inspectable evidence. Run identifiers deduplicate repeated processing.

To process an already saved application-owned brief or retry export:

```sh
uv run research watch runs/research/RUN_ID/brief.json --database runs/watch.sqlite
uv run research export --database runs/watch.sqlite
```

Replace RUN_ID with the printed identifier. Serialize runs and use one export worker. Export means a local JSON file, not email delivery. The price extractor is specific to the fixture's wording and watch definition. Files supplied to `watch` are trusted application records, not an authenticated upload format.

For reviewed external sources use `--mode live --catalog catalog.json`. Catalog keys are source identifiers; each entry has `title`, `url`, and `ready_selector`. Live entries require HTTPS, block redirects, and need worker-level egress policy. The browser allows only the exact selected URL. No arbitrary internet search service or unattended external notification channel is included.

`--output` chooses the research folder. `--project` identifies the folder containing `uv.lock` when launching elsewhere. Every accepted briefing preserves captured observations, model usage metadata, effective model configuration, dependencies, and application source. No API key is placed in the snapshot.

## Smoke verification

```sh
uv run python -m unittest discover -s tests -v
AIC_BROWSER_SMOKE=1 uv run python -m unittest discover -s tests -v
```

The default suite exercises the actual LangChain agent and both provider integrations against scripted HTTP tool-call responses. A local site serves static pages for those tests; SQLite monitoring and filesystem notification export are real. It checks a changed price, duplicate processing, citation rejection, and baseline preservation. These are transport/integration tests, not evidence of live model quality.

Browser rendering has a separate opt-in test against the included JavaScript fixture. Chromium installation failed in the build environment, so that test was not run there. Live hosted/Ollama inference and external websites were not tested. See SMOKE_REPORT.md for the exact clean-install result.
