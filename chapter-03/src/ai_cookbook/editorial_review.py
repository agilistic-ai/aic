# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .editorial_checks import NAMES, checks
from .editorial_html import render
from .editorial_inputs import Nonempty, StrictModel, read_json
from .editorial_record import load_job, validate_job


def fingerprint(job):
    text = json.dumps(job, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save(job, path):
    validate_job(job)
    path = Path(path)
    if path.suffix != ".json":
        raise ValueError("Save the package under a new .json filename.")
    html_path = path.with_suffix(".html")
    page = render(job, fingerprint(job))
    path.parent.mkdir(parents=True, exist_ok=True)
    html_created = False
    with path.open("x", encoding="utf-8") as target:
        try:
            with html_path.open("x", encoding="utf-8") as html:
                html_created = True
                json.dump(job, target, ensure_ascii=False, indent=2)
                html.write(page)
        except Exception:
            target.close()
            path.unlink()
            if html_created:
                html_path.unlink()
            raise


class Receipt(StrictModel):
    artifact: str
    digest: str
    reviewer: Nonempty
    meaning_reviewed: bool
    language_reviewed: bool
    approved_at: Nonempty


def approve(path, name, *, expected_digest, reviewer,
            meaning_reviewed=False, language_reviewed=False):
    path = Path(path)
    job = load_job(path)
    if name not in NAMES or fingerprint(job) != expected_digest:
        raise ValueError("Check the selected version and reload the review.")
    if checks(job):
        raise ValueError("Resolve the mechanical findings first.")
    if not reviewer.strip() or meaning_reviewed is not True:
        raise ValueError("An identified reviewer must check the meaning.")
    if name == "variant" and language_reviewed is not True:
        raise ValueError("The translated version needs qualified language review.")
    receipt = {"artifact": name, "digest": expected_digest,
               "reviewer": reviewer, "meaning_reviewed": True,
               "language_reviewed": language_reviewed,
               "approved_at": datetime.now(timezone.utc).isoformat()}
    Receipt.model_validate(receipt)
    with path.with_suffix(f".{name}.approval.json").open("x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)


def export_approved(path, name, destination):
    path = Path(path)
    if name not in NAMES:
        raise ValueError("Unknown editorial version.")
    job = load_job(path)
    receipt = Receipt.model_validate(read_json(path.with_suffix(f".{name}.approval.json")))
    if (receipt.artifact != name or receipt.digest != fingerprint(job)
            or not receipt.reviewer.strip() or not receipt.meaning_reviewed
            or (name == "variant" and not receipt.language_reviewed) or checks(job)):
        raise ValueError("Approval doesn't match this package.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as target:
        target.write(job["drafts"][name])
