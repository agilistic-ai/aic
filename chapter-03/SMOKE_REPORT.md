# Chapter 3 application smoke report

Tested on October 3, 2026, using Python 3.12.14 on Linux. The application ZIP was extracted into a new directory and installed into a new virtual environment with `uv sync --locked --no-editable`. Every installed application module matched its archived source. No earlier chapter checkout was needed.

All 12 tests passed from the clean installation:

```text
Ran 12 tests in 36.174s
OK
```

The tests used the actual OpenAI 2.54.0 and Ollama 0.6.3 SDKs, with Pydantic 2.13.5 and HTTPX 0.28.1. Both SDKs sent requests to a local HTTP fixture server. The pipeline, validation, command line, saved packages, review receipts, and exports were real application behavior. Model responses were scripted test data. No adapter or SDK was replaced with a stub.

## Verified behavior

| Smoke case | Result |
| --- | --- |
| Both providers and both generation methods produce complete packages, review HTML, and exact approved exports; staged calls retain original sources | Passed |
| Export requires approval; stale fingerprints, repeated approval writes, repeated export destinations, and changed packages are refused | Passed |
| Spanish output requires its own meaning and language-review attestations | Passed |
| A correction creates a new package, records its parent, retains the original, and requires new approval | Passed |
| Malformed JSON and an unrecognized approval field cause one failed call without retry; returned usage remains recorded | Passed |
| Timeouts, HTTP failures, incomplete output, and hosted refusal stop with one call and unknown usage where appropriate | Passed |
| Editorial questions, unsupported fact quotations, and excessive intermediate-payload growth stop later stages | Passed |
| Translation failure preserves earlier drafts, records its stage, and blocks package approval | Passed |
| Mechanical checks catch altered literals, numeric components, missing terminology, and length violations; a meaning shift can pass those checks but remains unapproved | Passed |
| Source/draft markup is escaped; package and HTML collisions don't overwrite existing files; a non-JSON package destination is refused | Passed |
| Invalid source/brief JSON, UTF-8, types, blanks, and oversized input are refused before model calls; help needs no key | Passed |
| Method comparison reports one versus four calls, preserves unknown usage, and makes no automatic fidelity claim | Passed |

Tests invoked the installed command line from temporary working directories outside the project. The earlier `python -m ai_cookbook.editorial_run` invocation separately passed a complete single-call generation against the fixture server.

All four printed Python modules in the revised chapter parse and match the packaged modules' syntax trees. The chapter retains its five main-section headings and contains no hyperlinks. Review HTML was checked structurally for escaped markup and required content; this wasn't a browser visual-regression test.

## Limits

No live hosted inference or live Ollama model run was performed. Provider credentials and a running local model weren't available for that check. These tests establish smoke-level application behavior with controlled responses, not extraction quality, writing quality, model availability, or qualified Spanish review. The separate evaluation cases support that later work.

The receipt system is a local prototype for preventing accidental stale approval. It isn't authenticated, tamper-proof approval infrastructure. Crash/power-loss recovery, concurrent writers, production-scale performance, and external publication weren't tested or implemented.

After the clean run, this report was added to the final ZIP. Source, tests, examples, configuration, and dependency metadata remained byte-for-byte identical to the tested archive. The ZIP contains no installed dependencies or model weights.
