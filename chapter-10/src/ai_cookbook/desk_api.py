import os
from typing import Literal
from time import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .booking_action import grant
from .desk_paths import STATE
from .booking_store import BookingStore
from .desk_auth import CurrentMembers, authenticate
from .desk_queue import Queue
from .desk_worker import access_stamp

app = FastAPI()
queue = Queue()
store = BookingStore(STATE / "bookings.sqlite", CurrentMembers())
bearer = HTTPBearer()


async def rejected(request, error):
    codes = {ValueError: 400, PermissionError: 403, KeyError: 404, RuntimeError: 503}
    return JSONResponse({"detail": "Request could not be completed."},
                        status_code=next(code for kind, code in codes.items() if isinstance(error, kind)))


for error_type in (ValueError, PermissionError, KeyError, RuntimeError):
    app.add_exception_handler(error_type, rejected)


def actor(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return authenticate(credentials.credentials)
    except PermissionError:
        raise HTTPException(403, "Access denied.") from None


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_key: str = Field(pattern=r"^[0-9a-f]{32}$")
    kind: Literal["answer", "booking"]
    text: str = Field(min_length=1, max_length=1000)


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@app.post("/jobs")
def submit(body: Request, who=Depends(actor)):
    if not body.text.strip() or len(body.text.encode()) > 1000:
        raise HTTPException(422, "Request exceeds the byte limit.")
    if body.kind == "booking":
        store.require_member(who)
    return {"id": queue.submit(who, body.model_dump())}


@app.get("/jobs/{job_id}")
def read(job_id: str, who=Depends(actor)):
    job = queue.edit(job_id, who, lambda job: None)
    if job["kind"] == "booking":
        store.require_member(who)
    result = job.get("result") if (job["state"] in {"complete", "needs_approval"}
        or (job["kind"] == "booking" and job["state"] == "unverified")) else None
    if job["kind"] == "answer" and result is not None:
        if job.get("access_stamp") != access_stamp(who):
            return {"id": job_id, "state": "refresh_required", "result": None}
    return {"id": job_id, "state": job["state"], "result": result}


@app.post("/jobs/{job_id}/approve")
def approve(job_id: str, body: Approval, who=Depends(actor)):
    store.require_member(who)
    def change(job):
        if job["release"] != os.environ["AIC_RELEASE_ID"]:
            raise ValueError("Approval requires the job's recorded release.")
        result = job.get("result") or {}
        expected = job.get("approved_fingerprint", result.get("fingerprint"))
        if job["kind"] != "booking" or expected != body.fingerprint:
            raise ValueError("Approval doesn't match the saved proposal.")
        if job["phase"] == "execute" and job["state"] != "unverified":
            return
        if job["state"] not in {"needs_approval", "unverified"}:
            raise ValueError("No proposal is awaiting approval.")
        job["approval_token"] = grant(store, who, job_id, result["proposal"],
                                       body.fingerprint)
        job.update(phase="execute", state="queued", tries=0,
                   approved_fingerprint=body.fingerprint, queued_at=time())
    queue.edit(job_id, who, change)
    return {"id": job_id}
