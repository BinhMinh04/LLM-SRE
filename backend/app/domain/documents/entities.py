"""Knowledge-document domain entities and value objects (plain dataclasses, no ORM coupling)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

# The four indexed knowledge sources (SPEC 7.1 / docs/product/rag.md).
SOURCE_TYPES = ("runbook", "postmortem", "architecture", "vendor")


@dataclass
class Document:
    """One knowledge document (its chunks + embeddings live in doc_chunks)."""

    title: str
    source_type: str  # runbook | postmortem | architecture | vendor
    service: str | None = None
    tags: list[str] = field(default_factory=list)
    id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class EmbeddedChunk:
    """A chunk ready to persist: position, text, and its embedding vector."""

    index: int
    content: str
    embedding: list[float]


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by similarity search, with its parent document title and similarity."""

    id: uuid.UUID
    document_id: uuid.UUID
    source_type: str
    service: str | None
    title: str
    content: str
    similarity: float


@dataclass(frozen=True)
class EvidenceRef:
    """A lightweight reference to a chunk that backed an analysis (for the API response)."""

    chunk_id: uuid.UUID
    source_type: str
    title: str
