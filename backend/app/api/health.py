"""Liveness / readiness endpoint."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.db import ping_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse, tags=["health"])
async def healthz() -> HealthResponse:
    """Liveness + DB readiness. Returns 'degraded' if the DB ping fails."""
    settings = get_settings()
    try:
        await ping_db()
        db_state = "up"
    except Exception:
        db_state = "down"
    return HealthResponse(
        status="ok" if db_state == "up" else "degraded",
        app=settings.app_name,
        database=db_state,
    )
