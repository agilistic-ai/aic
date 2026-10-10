# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Prepare a standalone local deployment and bind it to its recorded release."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil


def paths(home):
    home = Path(home).resolve()
    os.environ.update(AIC_HOME=str(home), AIC_STATE=str(home / "state"), AIC_SOURCES=str(home / "sources"),
                      AIC_AUTH_FILE=str(home / "auth.json"), AIC_LIMITS_FILE=str(home / "limits.json"),
                      AIC_CONFIG=str(home / "config.toml"))
    return home


def identity(home, method):
    from .settings import load_settings
    from dataclasses import asdict
    from importlib.metadata import version
    import platform
    package = Path(__file__).resolve().parent
    return {"python": platform.python_version(),
            "dependencies": {name: version(name) for name in ("aic-chapter-10", "openai", "ollama",
                "pydantic", "pypdf", "fastapi", "uvicorn", "langgraph", "langgraph-checkpoint-sqlite")},
            "code": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.glob("*.py"))},
            "configuration": asdict(load_settings(home / "config.toml")), "method": method,
            "lock": hashlib.sha256((home / "uv.lock").read_bytes()).hexdigest(),
            "limits": hashlib.sha256((home / "limits.json").read_bytes()).hexdigest()}


def configure(home):
    home = paths(home)
    release = json.loads((home / "release.json").read_text())
    current = identity(home, release["method"])
    if current != release["identity"]:
        raise ValueError("Code, model endpoint/configuration, lock or limits changed; prepare a reviewed release.")
    digest = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
    if digest != release["id"]:
        raise ValueError("Release record failed its identity check.")
    os.environ.update(AIC_RELEASE_ID=digest, AIC_RETRIEVAL_METHOD=release["method"])
    return home, release


def initialize(home, project, config=None, *, method="keyword", limits=None):
    home = Path(home).resolve()
    project = Path(project).resolve()
    home.mkdir(parents=True, mode=0o700, exist_ok=False)
    try:
        shutil.copy2(config or project / "config.toml", home / "config.toml")
        shutil.copy2(project / "uv.lock", home / "uv.lock")
        shutil.copy2(limits or project / "examples/limits.json", home / "limits.json")
        shutil.copytree(project / "examples/knowledge", home / "sources")
        actors, tokens = {}, {}
        for actor, can_book in (("member", True), ("reader", False)):
            token = secrets.token_urlsafe(32)
            token_path = home / f"{actor}.token"
            token_path.write_text(token + "\n")
            token_path.chmod(0o600)
            tokens[hashlib.sha256(token.encode()).hexdigest()] = actor
            actors[actor] = {"groups": ["members"], "can_book": can_book}
        (home / "auth.json").write_text(json.dumps({"tokens": tokens, "actors": actors}, indent=2))
        (home / "auth.json").chmod(0o600)
        paths(home)
        from .knowledge_index import Embeddings, KeywordIndex, build_index, save_index
        from .knowledge_sources import load_catalog
        from .desk_queue import Queue
        from .booking_store import BookingStore
        from .desk_auth import CurrentMembers
        from langgraph.checkpoint.sqlite import SqliteSaver
        Queue(home / "state/jobs.sqlite")
        BookingStore(home / "state/bookings.sqlite", CurrentMembers())
        with SqliteSaver.from_conn_string(str(home / "state/checkpoints.sqlite")) as saver:
            saver.setup()
        with closing(KeywordIndex() if method == "keyword" else Embeddings()) as embed:
            index = build_index(home / "sources", load_catalog(home / "sources"), embed)
            if any(item["error"] for item in index["documents"].values()):
                raise ValueError("Known fixture extraction failed; initialization rejected.")
            save_index(index, home / "state/knowledge/index.json")
        record = identity(home, method)
        digest = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        release = {"id": digest, "identity": record, "method": method,
                   "embedding_key": index["embedding_key"]}
        (home / "release.json").write_text(json.dumps(release, indent=2))
        return home, release
    except BaseException:
        shutil.rmtree(home)
        raise
