"""Outbound response DTOs, one module per resource."""

from app.interface.http.dto.response.document import DocumentCreatedResponse, DocumentSummary
from app.interface.http.dto.response.health import HealthResponse
from app.interface.http.dto.response.incident import (
    AnalysisOut,
    IncidentCreatedResponse,
    IncidentDetail,
    IncidentSummary,
)

__all__ = [
    "IncidentCreatedResponse",
    "AnalysisOut",
    "IncidentSummary",
    "IncidentDetail",
    "DocumentCreatedResponse",
    "DocumentSummary",
    "HealthResponse",
]
