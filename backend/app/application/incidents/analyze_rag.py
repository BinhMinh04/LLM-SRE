"""IngestIncidentWithRag use case: cache-first analysis grounded in retrieved knowledge (M3 slice 2).

On a cache MISS it builds a retrieval query from the incident context, embeds it, retrieves top-K
doc chunks (service-filtered), and passes them to the analyzer so the diagnosis cites
`[source_type: title]`. Retrieved chunk ids are persisted on the analysis. With no matching documents
(empty evidence) it behaves like the M2 single-call baseline. Depends only on domain ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.application.incidents.ingest import _copy_analysis
from app.domain.documents.ports import Embedder, Retriever
from app.domain.incidents.confidence import confidence_to_score
from app.domain.incidents.entities import Analysis, Incident
from app.domain.incidents.fingerprint import fingerprint
from app.domain.incidents.prompts import build_retrieval_query
from app.domain.incidents.ports import AnalysisCacheRepository, Analyzer, IncidentRepository
from app.domain.shared import Clock, UnitOfWork


@dataclass
class IngestIncidentWithRag:
    incidents: IncidentRepository
    cache: AnalysisCacheRepository
    analyzer: Analyzer
    embedder: Embedder
    retriever: Retriever
    clock: Clock
    uow: UnitOfWork
    cache_ttl_seconds: int
    top_k: int = 6
    min_similarity: float = 0.0

    async def execute(self, *, source: str, context: dict) -> tuple[Incident, Analysis]:
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
            evidence = await self._retrieve(context)
            draft = await self.analyzer.analyze(context, evidence=evidence)
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
                    evidence_chunk_ids=[chunk.id for chunk in evidence],
                )
            )
            await self.cache.put(fp, analysis.id, now + timedelta(seconds=self.cache_ttl_seconds))

        await self.incidents.set_status(incident.id, "analyzed")
        incident.status = "analyzed"
        await self.uow.commit()
        return incident, analysis

    async def _retrieve(self, context: dict):
        query = build_retrieval_query(context)
        if not query:
            return []
        query_embedding = await self.embedder.embed_query(query)
        return await self.retriever.search(
            query_embedding=query_embedding,
            service=context.get("service"),
            top_k=self.top_k,
            min_similarity=self.min_similarity,
        )
