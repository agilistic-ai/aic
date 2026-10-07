import json
from pathlib import Path
from .research_recipe import snapshot
from time import perf_counter
from uuid import uuid4

from .research_agent import make_agent
from .research_brief import Brief, validate_brief
from .research_tools import Sources


FIXTURE_CATALOG = {
    "venue": {"title": "Riverside Hall Saturday hire tariff",
              "url": "http://127.0.0.1:8765/venue.html",
              "ready_selector": "body[data-ready='true']"},
    "offer": {"title": "Riverside Hall Saturday special offer",
              "url": "http://127.0.0.1:8765/offer.html",
              "ready_selector": "body[data-ready='true']"},
}


def research(question, model, catalog, *, mode="fixture", output="runs/research",
             settings=None, config=None, project="."):
    if not question.strip() or len(question.encode()) > 2000:
        raise ValueError("Supply a short research question.")
    sources = Sources(catalog, mode)
    agent = make_agent(model, sources.tools())
    started = perf_counter()
    result = agent.invoke({"messages": [{"role": "user", "content": question}]},
                          config={"recursion_limit": 32})
    brief = Brief.model_validate(result["structured_response"])
    validate_brief(brief, sources.archive)
    run_id = uuid4().hex
    job = {"run_id": run_id, "question": question, "mode": mode,
           "brief": brief.model_dump(), "observations": sources.archive,
           "tool_calls": sources.calls,
           "usage": [m.usage_metadata for m in result["messages"]
                     if getattr(m, "usage_metadata", None)],
           "recipe": snapshot(project, config)[0] if settings else None, "elapsed_seconds": perf_counter() - started}
    folder = Path(output) / run_id
    folder.mkdir(parents=True)
    path = folder / "brief.json"
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, job
