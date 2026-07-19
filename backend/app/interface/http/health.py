"""Liveness / readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.infrastructure.config import get_settings
from app.infrastructure.db.session import ping_db
from app.interface.http.dto import HealthResponse

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
