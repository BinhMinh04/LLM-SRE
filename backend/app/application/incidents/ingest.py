"""IngestIncident use case: cache-first single-call analysis (M2 baseline).

Flow: fingerprint(context) -> cache lookup within TTL. HIT copies the stored analysis for this
incident with no Analyzer call; MISS runs the Analyzer, persists the analysis, and writes the cache
row. The whole thing commits through the UnitOfWork. This class depends ONLY on domain entities,
pure rules, and ports — no framework, DB, or provider imports — so it is unit-testable with fakes and
is the exact seam M3's LangGraph analyzer swaps into (a different `Analyzer` implementation).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.domain.incidents.confidence import confidence_to_score
from app.domain.incidents.entities import Analysis, Incident
from app.domain.incidents.fingerprint import fingerprint
from app.domain.incidents.ports import (
    AnalysisCacheRepository,
    Analyzer,
    Clock,
    IncidentRepository,
    UnitOfWork,
)


@dataclass
class IngestIncident:
    incidents: IncidentRepository
    cache: AnalysisCacheRepository
    analyzer: Analyzer
    clock: Clock
    uow: UnitOfWork
    cache_ttl_seconds: int

    async def execute(self, *, source: str, context: dict) -> tuple[Incident, Analysis]:
        """Persist the incident, produce its analysis cache-first, and return both.

        Precondition: `context['service']` is present (validated at the interface boundary).
        """
        fp = fingerprint(context)
        incident = await self.incidents.add(
            Incident(
                service=context["service"],
                source=source,
                fingerprint=fp,
                context=context,
                status="analyzing",
            )
        )

        now = self.clock.now()
        cached = await self.cache.get_valid(fp, now)
        if cached is not None:
            analysis = await self.incidents.add_analysis(
                _copy_analysis(incident.id, cached, cache_state="HIT")
            )
        else:
            draft = await self.analyzer.analyze(context)
            analysis = await self.incidents.add_analysis(
                Analysis(
                    incident_id=incident.id,
                    severity=draft.severity,
                    summary=draft.summary,
                    root_cause=draft.root_cause,
                    recommended_action=draft.recommended_action,
                    confidence=confidence_to_score(draft.confidence),
                    cache_state="MISS",
                    model_id=draft.model_id,
                    evidence_chunk_ids=list(draft.evidence_chunk_ids),
                )
            )
            await self.cache.put(
                fp, analysis.id, now + timedelta(seconds=self.cache_ttl_seconds)
            )

        await self.incidents.set_status(incident.id, "analyzed")
        incident.status = "analyzed"
        await self.uow.commit()
        return incident, analysis


def _copy_analysis(incident_id, source: Analysis, *, cache_state: str) -> Analysis:
    """A fresh Analysis for `incident_id` copying a cached analysis's fields."""
    return Analysis(
        incident_id=incident_id,
        severity=source.severity,
        summary=source.summary,
        root_cause=source.root_cause,
        recommended_action=source.recommended_action,
        confidence=source.confidence,
        cache_state=cache_state,
        model_id=source.model_id,
        evidence_chunk_ids=list(source.evidence_chunk_ids),
    )
