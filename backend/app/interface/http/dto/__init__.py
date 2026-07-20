"""HTTP DTOs, organized by direction:

- `request/`  — inbound request models, one module per resource.
- `response/` — outbound response schemas (pure), one module per resource.
- `mappers/`  — domain entity -> response DTO functions, one module per resource.

Top-level names are re-exported so callers can `from app.interface.http.dto import IncidentDetail`
or `from app.interface.http.dto import mappers`.
"""

from app.interface.http.dto import mappers
from app.interface.http.dto.request import DocumentIngestRequest, IncidentIngestRequest
from app.interface.http.dto.response import (
    AnalysisOut,
    DocumentCreatedResponse,
    DocumentSummary,
    HealthResponse,
    IncidentCreatedResponse,
    IncidentDetail,
    IncidentSummary,
)

__all__ = [
    "mappers",
    "IncidentIngestRequest",
    "DocumentIngestRequest",
    "IncidentCreatedResponse",
    "AnalysisOut",
    "IncidentSummary",
    "IncidentDetail",
    "DocumentCreatedResponse",
    "DocumentSummary",
    "HealthResponse",
]
