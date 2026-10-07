"""Fingerprint the running recipe, including its effective model endpoint."""

import hashlib
import json
import platform
import re
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from .settings import load_settings


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(project, config, references):
    settings = load_settings(config)
    registry = json.loads(Path(references).read_text(encoding="utf-8"))
    if (not isinstance(registry, list)
            or any(not isinstance(ref, str) or not re.fullmatch(r"R-[0-9]{4}", ref)
                   for ref in registry)
            or len(registry) != len(set(registry))):
        raise ValueError("References must be a JSON array of unique R-0000 IDs.")
    # Read the installed package, not a possibly different checkout in cwd.
    package = Path(__file__).resolve().parent
    manifest = {
        "config.toml": Path(config).read_text(encoding="utf-8"),
        "uv.lock": (Path(project) / "uv.lock").read_text(encoding="utf-8"),
        "references": sorted(registry),
        "effective_model": asdict(settings),
        "python": platform.python_version(),
        "dependencies": {name: version(name) for name in
                         ("aic-chapter-2", "openai", "ollama", "pydantic", "httpx")},
        "code": {p.name: p.read_text(encoding="utf-8")
                 for p in sorted(package.glob("*.py"))},
    }
    encoded = json.dumps(manifest, sort_keys=True)
    return digest(encoded.encode("utf-8")), encoded, set(registry), settings
