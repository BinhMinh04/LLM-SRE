"""Health check response schema."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    app: str
    database: str  # "up" | "down"
