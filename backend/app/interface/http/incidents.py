"""Incident HTTP controller (SPEC section 6.4).

Parses requests into DTOs, delegates to the ingest use case (writes) or the repository (reads), and
maps domain entities back to response DTOs. No business rules or persistence details live here.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.incidents.ingest import IngestIncident
from app.domain.incidents.ports import IncidentRepository
from app.interface.http.deps import get_incident_repository, get_ingest_incident
from app.interface.http.dto import (
    IncidentCreatedResponse,
    IncidentDetail,
    IncidentIngestRequest,
    IncidentSummary,
)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.post("", response_model=IncidentCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    body: IncidentIngestRequest,
    ingest: IngestIncident = Depends(get_ingest_incident),
) -> IncidentCreatedResponse:
    """Ingest one incident context and analyze it (cache-first). Returns the incident id."""
    if not body.context.get("service"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="context.service is required",
        )
    incident, _ = await ingest.execute(source=body.source, context=body.context)
    return IncidentCreatedResponse(
        incident_id=incident.id,
        status=incident.status,
        stream=f"/api/incidents/{incident.id}/stream",
    )


@router.get("", response_model=list[IncidentSummary])
async def list_incidents(
    repo: IncidentRepository = Depends(get_incident_repository),
    service: str | None = None,
    severity: str | None = None,
    incident_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[IncidentSummary]:
    """List incidents (newest first), optionally filtered by service / severity / status."""
    rows = await repo.list(
        service=service,
        severity=severity,
        status=incident_status,
        limit=limit,
        offset=offset,
    )
    return [IncidentSummary.from_domain(incident, analysis) for incident, analysis in rows]


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: uuid.UUID,
    repo: IncidentRepository = Depends(get_incident_repository),
) -> IncidentDetail:
    """Return one incident with its context and analysis."""
    incident = await repo.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="incident not found")
    analysis = await repo.latest_analysis(incident_id)
    return IncidentDetail.from_domain(incident, analysis)
