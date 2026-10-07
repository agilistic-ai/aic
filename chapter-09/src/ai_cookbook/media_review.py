import hashlib
import json
import os
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from .media_extract import Strict, checked_bytes, media_client


class ConfirmedFields(Strict):
    item_model: str | None
    problem: str = Field(min_length=1, max_length=1000)
    preferred_time: str | None


def approve_draft(path, fields, *, expected_digest, reviewer, questions_resolved):
    path = Path(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("The reviewed draft changed.")
    job = json.loads(raw)
    checked_bytes(job["record"]["visual"])
    checked_bytes(job["record"]["audio"])
    confirmed = ConfirmedFields.model_validate(fields)
    if not confirmed.problem.strip() or not reviewer.strip() or questions_resolved is not True:
        raise ValueError("Complete the review before approval.")
    result = {"source_draft_sha256": expected_digest, "record_id": job["record"]["id"],
              "reviewer": reviewer, "reviewed_at": datetime.now(timezone.utc).isoformat(),
              "fields": confirmed.model_dump(),
              "corrections": {key: {"proposed": job["fields"][key], "confirmed": value}
                              for key, value in confirmed.model_dump().items()
                              if value != job["fields"][key]},
              "state": "reviewed_intake"}
    destination = path.parent / f"reviewed-{uuid4().hex}.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination, result


def review_interactively(path):
    raw = Path(path).read_bytes()
    digest, job = hashlib.sha256(raw).hexdigest(), json.loads(raw)
    print("Inspect:", job["record"]["visual"]["path"])
    print("Replay:", job["record"]["audio"]["path"])
    print("Transcript:", job["transcript"])
    print(json.dumps({"candidates": job["candidates"], "questions": job["questions"]}, indent=2))
    fields = {}
    for key, value in job["fields"].items():
        entered = input(f"{key} [{value or 'unknown'}] (Enter keeps; ? means unknown): ").strip()
        fields[key] = value if not entered else None if entered == "?" else entered
    reviewer = input("Reviewer name: ").strip()
    resolved = input("Checked the media and resolved the open questions? [yes/no] ") == "yes"
    return approve_draft(path, fields, expected_digest=digest,
                         reviewer=reviewer, questions_resolved=resolved)


def speak_confirmation(text, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".partial", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with media_client() as client:
            with client.audio.speech.with_streaming_response.create(
                model=os.environ.get("AIC_SPEECH_MODEL", "gpt-4o-mini-tts"),
                voice="coral", input=text, response_format="wav"
            ) as response:
                response.stream_to_file(temporary)
        with wave.open(str(temporary), "rb") as recording:
            if recording.getnframes() <= 0:
                raise ValueError("Speech response is empty.")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
