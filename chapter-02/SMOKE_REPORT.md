# Chapter 2 application smoke report

Tested on October 3, 2026, with Python 3.12.14 on Linux. The ZIP was extracted into a new directory and installed into a new virtual environment with `uv sync --locked --no-editable`. No Chapter 1 checkout was required. Every installed application module was checked against its archived source.

The clean installation passed all 12 smoke tests in 23.230 seconds:

```text
Ran 12 tests in 23.230s
OK
```

OpenAI 2.54.0 and Ollama 0.6.3 were the actual installed SDKs, with Pydantic 2.13.5 and HTTPX 0.28.1. Both SDKs sent HTTP requests to a local fixture server. The application pipeline, command line, validation, SQLite persistence, and review operations were real. Responses representing model output were scripted. The tests didn't replace the model adapter with a stub or bypass the SDKs.

## Verified behavior

| Smoke case | Result |
| --- | --- |
| Both provider SDKs process a mixed rules/model batch; unchanged reruns skip work; queue and ready export function | Passed |
| One schema-repair call is allowed; a second malformed result fails only its case; explicit retry retains attempt history | Passed |
| Timeouts, HTTP errors, and incomplete responses make one call; hosted refusal fails; private provider details aren't copied into results | Passed |
| Reviewer corrects a selected date; unresolved date warning blocks approval; acknowledged correction records before/after history; stale review is refused | Passed |
| Identical text under another ID is retained and needs duplicate acknowledgement; an ID/content collision preserves the first source | Passed |
| Unknown reference can't be approved; needs-info and rejection work; editing the immutable source in a review file is refused | Passed |
| Invalid UTF-8 and blank messages fail independently; oversized text isn't imported; later valid messages continue | Passed |
| An added approval field triggers schema repair; the resulting valid model interpretation still requires human review | Passed |
| A configuration revision creates a separate recipe; export filters by the selected recipe | Passed |
| Rules-only processing and help need no key; invalid registry and missing case/database errors are handled | Passed |
| A reconstructed pending checkpoint resumes without rerunning a completed case | Passed |
| An unresolved relative date survives in the proposal, stays null in the normalized record, and blocks approval | Passed |

The installed CLI ran from temporary working directories outside the project. The earlier `python -m ai_cookbook.intake_batch` entry point also passed a rules-only invocation. The five printed chapter modules parse successfully and match the application's Python syntax trees; all original main-section headings remain in order.

## Scope and limits

No live OpenAI request or live Ollama inference was performed. No credentials, local model service, or model weights were available for that check. These results establish smoke-level application behavior with controlled provider responses; they don't establish extraction quality, model availability, or local hardware suitability. Use the labeled cases and review criteria for a separate live-model evaluation.

The pending-resume check reconstructs the saved checkpoint; it doesn't kill a process mid-transaction. This is a local, single-worker prototype. Multi-worker stress, authentication, real downstream dispatch, and production-scale performance weren't tested or implemented.

After the clean run, this report was added to the final ZIP. Application source, tests, configuration, dependency lock, and examples remained byte-for-byte identical to the tested archive.
