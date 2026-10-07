"""Record the implementation actually used, independent of the working directory."""
from dataclasses import asdict
from importlib.metadata import version
import os
from pathlib import Path
import platform

from .settings import load_settings


def snapshot(project=".", config=None):
    project = Path(project).resolve()
    config = config or os.environ.get("AIC_CONFIG") or project / "config.toml"
    settings = load_settings(config)
    package = Path(__file__).resolve().parent
    record = {
        "config.toml": Path(config).read_text(encoding="utf-8"),
        "uv.lock": (project / "uv.lock").read_text(encoding="utf-8"),
        "effective_model": asdict(settings),
        "python": platform.python_version(),
        "dependencies": {name: version(name) for name in
                         ("aic-chapter-5", "openai", "ollama", "pydantic", "httpx")},
        "code": {p.name: p.read_text(encoding="utf-8") for p in sorted(package.glob("*.py"))},
    }
    return record, settings
