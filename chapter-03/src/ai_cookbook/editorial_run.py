from pathlib import Path
from uuid import uuid4

from .editorial import build
from .editorial_inputs import load_packet
from .editorial_recipe import snapshot
from .editorial_review import save


def run(folder, *, method="staged", project=".", config=None, output=None):
    sources, brief = load_packet(folder)
    implementation, settings = snapshot(project, config)
    job = build(sources, brief, method=method, settings=settings)
    job["implementation"] = implementation
    output = Path(output) if output else Path(project) / "runs/editorial"
    path = output / uuid4().hex / "run.json"
    save(job, path)
    return path, job


if __name__ == "__main__":
    import sys
    from .editorial_cli import main
    raise SystemExit(main(["run", *sys.argv[1:]]))
