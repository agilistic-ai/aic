# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

"""Explicit configuration; importing the application never needs a key."""

import hashlib
import json
import math
import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    provider: str
    name: str
    timeout_seconds: float
    base_url: str

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def load_settings(path=None):
    path = Path(path or os.environ.get("AIC_CONFIG", "config.toml"))
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        model = document["model"]
        if set(model) != {"provider", "name", "timeout_seconds"}:
            raise ValueError
        provider, name, timeout = model["provider"], model["name"], model["timeout_seconds"]
        if provider not in {"openai", "ollama"} or not isinstance(name, str) or not name.strip():
            raise ValueError
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError
        endpoint = (os.environ.get("AIC_OPENAI_BASE_URL", "https://api.openai.com/v1")
                    if provider == "openai" else
                    os.environ.get("AIC_OLLAMA_HOST", "http://127.0.0.1:11434"))
        url = urlsplit(endpoint)
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username
                or url.password or url.query or url.fragment):
            raise ValueError
        if provider == "openai" and url.scheme != "https" and url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError
        return Settings(provider, name.strip(), float(timeout), endpoint)
    except (OSError, ValueError, KeyError, TypeError):
        raise ConfigurationError("Check the model configuration file and endpoint settings.") from None
