"""Request/response DTOs (the parse-first boundary) and mappers from domain entities.

Unknown input (request bodies) is parsed into typed DTOs here before reaching the application layer;
domain entities are mapped to response DTOs here on the way out. `evidence` is always empty in the
M2 baseline (RAG lands in M3). SPEC sections 6.4 / 6.5.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.documents.entities import Document
from app.domain.incidents.entities import Analysis, Incident


class IncidentIngestRequest(BaseModel):
    """`POST /api/incidents` body: a source label plus the raw incident context dict."""

    source: str = "manual"  # auto | manual | webhook
    context: dict = Field(..., description="Incident context; must contain 'service'.")


class IncidentCreatedResponse(BaseModel):
    """`POST /api/incidents` response (SPEC 6.5)."""

    incident_id: uuid.UUID
    status: str
    stream: str


class AnalysisOut(BaseModel):
    """The persisted 5-field analysis plus cache state and evidence refs."""

    severity: str
    summary: str
    root_cause: str
    recommended_action: str
    confidence: float | None
    model_id: str
    cache_state: str = Field(serialization_alias="_cache")  # HIT | MISS
    evidence: list[dict] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, analysis: Analysis) -> "AnalysisOut":
        return cls(
            severity=analysis.severity,
            summary=analysis.summary,
            root_cause=analysis.root_cause,
            recommended_action=analysis.recommended_action,
            confidence=analysis.confidence,
            model_id=analysis.model_id,
            cache_state=analysis.cache_state,
            evidence=[],
        )


class IncidentSummary(BaseModel):
    """One row in `GET /api/incidents` (incident + its analysis headline)."""

    id: uuid.UUID
    service: str
    source: str
    status: str
    fingerprint: str
    created_at: datetime
    severity: str | None = None
    summary: str | None = None

    @classmethod
    def from_domain(cls, incident: Incident, analysis: Analysis | None) -> "IncidentSummary":
        return cls(
            id=incident.id,
            service=incident.service,
            source=incident.source,
            status=incident.status,
            fingerprint=incident.fingerprint,
            created_at=incident.created_at,
            severity=analysis.severity if analysis else None,
            summary=analysis.summary if analysis else None,
        )


class IncidentDetail(BaseModel):
    """`GET /api/incidents/{id}`: incident + context + analysis + evidence."""

    id: uuid.UUID
    service: str
    source: str
    status: str
    fingerprint: str
    context: dict
    created_at: datetime
    updated_at: datetime
    analysis: AnalysisOut | None = None

    @classmethod
    def from_domain(cls, incident: Incident, analysis: Analysis | None) -> "IncidentDetail":
        return cls(
            id=incident.id,
            service=incident.service,
            source=incident.source,
            status=incident.status,
            fingerprint=incident.fingerprint,
            context=incident.context,
            created_at=incident.created_at,
            updated_at=incident.updated_at,
            analysis=AnalysisOut.from_domain(analysis) if analysis else None,
        )


class DocumentIngestRequest(BaseModel):
    """`POST /api/documents` body: metadata + the raw text/markdown to index."""

    title: str
    source_type: str  # runbook | postmortem | architecture | vendor (validated at the controller)
    service: str | None = None
    tags: list[str] = Field(default_factory=list)
    content: str


class DocumentCreatedResponse(BaseModel):
    """`POST /api/documents` response: the stored document id and how many chunks were indexed."""

    document_id: uuid.UUID
    chunks: int


class DocumentSummary(BaseModel):
    """One row in `GET /api/documents`."""

    id: uuid.UUID
    title: str
    source_type: str
    service: str | None
    tags: list[str]
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, document: Document, chunk_count: int) -> "DocumentSummary":
        return cls(
            id=document.id,
            title=document.title,
            source_type=document.source_type,
            service=document.service,
            tags=list(document.tags),
            chunk_count=chunk_count,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    app: str
    database: str  # "up" | "down"
