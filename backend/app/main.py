"""IIM FastAPI application entrypoint.

M1 scope: app skeleton, CORS, and a DB-aware /healthz. Incident/document/stream/auth routers
land in later milestones (SPEC section 18).

FastAPI docs: https://fastapi.tiangolo.com/
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=f"{settings.app_name} API",
    description="Intelligent Incident Management - AI incident triage grounded in RAG.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"app": settings.app_name, "docs": "/docs", "health": "/healthz"}
