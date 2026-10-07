import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .reporting_execute import execute
from .reporting_plan import propose
from .reporting_recipe import snapshot


def chart_remaining(result, path, as_of):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if result["columns"] != ["workshop_id", "workshop", "remaining_seats"]:
        return None
    rows = result["rows"]
    if not rows or len(rows) > 20:
        return None
    ids = [row[0] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Chart requires one row per workshop.")
    if any(not isinstance(row[1], str) or type(row[2]) is not int for row in rows):
        raise ValueError("Unexpected chart values.")
    with plt.rc_context({"text.parse_math": False}):
        figure, axis = plt.subplots(figsize=(7, max(2.5, len(rows) * 0.45)))
        axis.barh([f"{r[1]} ({r[0]})" for r in rows], [r[2] for r in rows], color="0.45")
        axis.axvline(0, color="black", linewidth=0.8)
        axis.set_xlabel("Remaining seats")
        axis.set_title(f"Reported remaining seats (reference date {as_of})")
        figure.tight_layout()
        figure.savefig(path, format="svg")
        plt.close(figure)
    return str(path)


def report(database, question, as_of, output="runs/reporting", *, project=".", config=None):
    implementation, settings = snapshot(project, config)
    plan = propose(question, as_of, settings=settings)
    job = {"question": question, "as_of": as_of, "plan": plan.model_dump(),
           "created_at": datetime.now(timezone.utc).isoformat(),
           "configuration": implementation, "chart": None}
    if plan.status == "ready":
        job["result"] = execute(database, plan)
    folder = Path(output) / uuid4().hex
    folder.mkdir(parents=True)
    if plan.status == "ready":
        job["chart"] = chart_remaining(job["result"], folder / "places.svg", as_of)
    (folder / "report.json").write_text(
        json.dumps(job, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    return {"report": str(folder / "report.json"), **job}
