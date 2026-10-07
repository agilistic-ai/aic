from typing import Literal

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(Strict):
    observation_id: str
    quote: str


class Finding(Strict):
    text: str
    evidence: list[Evidence]


class Brief(Strict):
    status: Literal["supported", "missing", "conflict"]
    findings: list[Finding]
    explanation: str


def validate_brief(brief, archive):
    if not brief.explanation.strip():
        raise ValueError("Brief needs an explanation of its scope or limitation.")
    if brief.status == "missing" and brief.findings:
        raise ValueError("Missing evidence can't support findings.")
    if brief.status != "missing" and not brief.findings:
        raise ValueError("Findings are required.")
    if brief.status == "conflict" and len(brief.findings) < 2:
        raise ValueError("Show both sides of the conflict.")
    for finding in brief.findings:
        if not finding.text.strip() or not finding.evidence:
            raise ValueError("Finding has no supporting evidence.")
        for citation in finding.evidence:
            observed = archive.get(citation.observation_id)
            if (observed is None or not citation.quote.strip()
                    or citation.quote not in observed["text"]):
                raise ValueError("Citation doesn't match an observed page.")
    return brief
