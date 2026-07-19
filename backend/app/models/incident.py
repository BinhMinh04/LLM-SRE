"""Incident, Analysis, and AnalysisCache tables (SPEC section 8)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow_column


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # auto | manual | webhook
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)  # raw incident context dict
    status: Mapped[str] = mapped_column(Text, nullable=False, default="new")
    # new | analyzing | analyzed | ticketed | resolved
    created_at: Mapped[datetime] = utcnow_column()
    updated_at: Mapped[datetime] = utcnow_column()


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cache_state: Mapped[str] = mapped_column(Text, nullable=False)  # HIT | MISS
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default="{}"
    )
    created_at: Mapped[datetime] = utcnow_column()


class AnalysisCache(Base):
    __tablename__ = "analysis_cache"

    fingerprint: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # CACHE_TTL_SECONDS from now
