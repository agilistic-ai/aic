# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import hashlib
import math
import os

from ollama import Client

from .knowledge_sources import extract


class Embeddings:
    def __init__(self):
        self.model = "nomic-embed-text:v1.5"
        self.client = Client(host=os.environ.get("AIC_OLLAMA_HOST", "http://127.0.0.1:11434"), timeout=60)
        self.digest = self.current_digest()
        self.key = f"{self.model}|{self.digest}|nomic-prefix-v1"

    def close(self):
        self.client.close()

    def current_digest(self):
        return next(m.digest for m in self.client.list().models
                    if m.model == self.model)

    def encode(self, texts, *, query=False):
        if self.current_digest() != self.digest:
            raise ValueError("Embedding model changed; restart and rebuild.")
        prefix = "search_query: " if query else "search_document: "
        response = self.client.embed(
            model=self.model, input=[prefix + t for t in texts], truncate=False,
        )
        vectors = []
        for values in response.embeddings:
            norm = math.sqrt(sum(v * v for v in values))
            if not math.isfinite(norm) or norm == 0:
                raise ValueError("Invalid embedding.")
            vectors.append([v / norm for v in values])
        if len(vectors) != len(texts):
            raise ValueError("Embedding count mismatch.")
        if len({len(v) for v in vectors}) > 1:
            raise ValueError("Embedding dimension mismatch.")
        return vectors


def build_index(root, catalog, embed):
    index = {"embedding_key": embed.key, "chunker": "600/80-v1", "documents": {}}
    for doc_id, spec in catalog.items():
        try:
            digest, units = extract(root, spec)
            passages = []
            for location, text in units:
                for start in range(0, len(text), 520):
                    end = min(start + 600, len(text))
                    piece = text[start:end]
                    if not piece.strip():
                        continue
                    identity = f"{doc_id}|{spec['version']}|{digest}|{location}|{start}"
                    passages.append({
                        "id": hashlib.sha256(identity.encode()).hexdigest()[:20],
                        "doc_id": doc_id, "version": spec["version"], "sha": digest,
                        "where": f"{location}, characters {start}:{end}", "text": piece,
                    })
            vectors = embed.encode([p["text"] for p in passages])
            for passage, vector in zip(passages, vectors, strict=True):
                passage["vector"] = vector
            index["documents"][doc_id] = {"passages": passages, "error": None}
        except Exception as error:
            index["documents"][doc_id] = {"passages": [], "error": type(error).__name__}
    return index


def save_index(index, path):
    import json
    import os
    import tempfile
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(index, handle, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class KeywordIndex:
    key = "keyword-only"

    def encode(self, texts, *, query=False):
        return [[] for _ in texts]

    def close(self):
        pass
