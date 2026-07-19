"""Document request DTOs (the parse-first boundary)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    """`POST /api/documents` body: metadata + the raw text/markdown to index."""

    title: str
    source_type: str  # runbook | postmortem | architecture | vendor (validated at the controller)
    service: str | None = None
    tags: list[str] = Field(default_factory=list)
    content: str
