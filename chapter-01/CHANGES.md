# Chapter 1 companion assembly — 1.0.0

The recovered Chapter 1 contract was a UTF-8 note-to-task application with title, details, and due_date; a Python API and module CLI; a 2,000-byte input limit; Python 3.12/uv setup; and hosted OpenAI plus local Ollama execution. The original room-request example and provider configurations were also recovered. Later chapter files establish the shared generate/ModelReply interfaces.

The full earlier Chapter 1 prose and exact original implementation blocks could not be recovered. Therefore AIC_Chapter_1_Reconstructed.md is a complete replacement chapter aligned to this source release, not a line-by-line edit of an available original. The locked AIC.docx outline was not modified.

This assembly supplies the missing installable project, configuration loader, complete adapters, task validator, CLI, examples, evaluation runner, and application-level smoke suite. It retains the established public interfaces and model choices. Optional token allowances are already exposed for compatibility with later recipes.

Configuration and credentials are loaded at request time rather than import time. Input size is checked before generation. Streamed text is withheld until a terminal response passes validation. Failures produce explicit nonzero exits and no success JSON. Usage metadata excludes the generated text.

A real SDK import initially failed in an environment with a configured SOCKS proxy because socksio was missing. The package now declares httpx with its socks extra, and that dependency is captured in uv.lock. The real SDKs subsequently passed the fixture HTTP smoke suite.

No model weights, third-party source packages, credentials, virtual environment, or private user inputs are distributed in the source archive.
