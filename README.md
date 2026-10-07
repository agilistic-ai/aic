# AI Cookbook — companion code

Companion examples for *AI Cookbook* by Josh Judd.

Chapters 1–10 each contain a separate, complete example project. Chapters 11–12 contain explanatory Markdown guides with code snippets. Those two chapters explore integration and product design; they aren't packaged applications.

## Choose a chapter

| Chapter | Example | Contents |
| --- | --- | --- |
| [01](chapter-01/README.md) | Turn a note into a task | Standalone project; `note-to-task` CLI |
| [02](chapter-02/README.md) | Repair-desk intake and review | Standalone project; `intake` CLI |
| [03](chapter-03/README.md) | Source-grounded editorial assistant | Standalone project; `editorial` CLI |
| [04](chapter-04/README.md) | Document search and evidence-based answers | Standalone project; `knowledge` CLI |
| [05](chapter-05/README.md) | Question-to-report with controlled SQL | Standalone project; `reporting` CLI |
| [06](chapter-06/README.md) | Approval and verified booking | Standalone project; `booking` CLI |
| [07](chapter-07/README.md) | Research and price monitoring | Standalone project; `research` CLI |
| [08](chapter-08/README.md) | Bounded coding maintenance | Standalone project; `coding` CLI |
| [09](chapter-09/README.md) | Media intake and review | Standalone project; `media` CLI |
| [10](chapter-10/README.md) | Small service desk | Standalone project; `desk` CLI |
| [11](chapter-11/README.md) | Connect applications you don't control | Markdown snippet guides only |
| [12](chapter-12/README.md) | Design the application people will use | Markdown snippet guides only |

## Run one project

Clone or download this repository, choose a chapter, and follow its README. Each application has its own Python environment and lockfile. Don't install all chapters into one environment: they deliberately carry independent versions of the `ai_cookbook` package so a chapter can be used by itself.

Use Python 3.12 and an independently installed `uv`. For example, from the repository root:

```sh
cd chapter-01
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked note-to-task --help
```

The smoke suite uses scripted local responses and needs no provider credentials. To process your own note with a real model, follow Chapter 1's hosted or Ollama setup. Real model calls need the corresponding service and may incur charges. Dependencies, model weights, browser binaries, and container images are installed separately.

Chapter 8's real coding-agent path requires a prepared Linux Docker host and local model service. Chapter 10 requires Linux for its worker lock. The chapter READMEs describe other setup requirements and the difference between a useful local example and a deployed service.

## What has been checked

See [VALIDATION.md](VALIDATION.md) for the repository import checks and current smoke results. Each application also retains its original `SMOKE_REPORT.md`, including what wasn't exercised. Scripted provider responses check application behavior; they don't establish model accuracy or live-service compatibility.

The code and lockfiles came from the completed chapter application archives. [SOURCE_ARCHIVES.md](SOURCE_ARCHIVES.md) records their names and checksums. The repository adds navigation and snippet explanations; it doesn't include the book manuscript or illustrations.

Keep real credentials and working records out of Git. The `.env.example` files are templates; each chapter's `runs/` folder is private working data. The examples intentionally distinguish a proposed result from an approved or verified action—keep those boundaries when adapting them.
