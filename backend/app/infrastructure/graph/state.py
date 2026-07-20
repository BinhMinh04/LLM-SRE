"""Shared state for the analysis graph (SPEC 6.1 / decision 0011)."""

from __future__ import annotations

from typing import TypedDict

from app.domain.documents.entities import RetrievedChunk
from app.domain.incidents.ports import ProgressReporter


class GraphState(TypedDict):
    context: dict
    source_types: list[str]
    query: str
    evidence: list[RetrievedChunk]
    hypothesis: str
    critique: dict
    round: int
    draft: dict
    reporter: ProgressReporter
