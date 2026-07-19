"""Unit tests for the LangGraph GraphAnalyzer (US-003) with a scripted ChatModel — no DB, no network.

Verifies the node flow (triage -> retrieve -> diagnose -> critic -> synthesize), model tiering, the
critic corrective loop, and that retrieved evidence ids land on the draft.
"""

import uuid

import pytest

from app.domain.documents.entities import RetrievedChunk
from app.infrastructure.graph.analyzer import GraphAnalyzer

pytestmark = pytest.mark.asyncio

_CTX = {
    "service": "GCM",
    "sample_logs": [{"message": "java.lang.OutOfMemoryError: Java heap space"}],
    "recent_deploy": {"version": "1.8.0"},
}

_SYNTH = (
    '{"severity":"critical","summary":"GCM OOM","root_cause":"heap regression '
    '[runbook: GCM OOM Runbook]","recommended_action":"roll back","confidence":"high"}'
)


class _ScriptedChat:
    """Routes by the node's system prompt; records (node, tier). Critic need_more is scripted."""

    def __init__(self, critic_need_more=(False,)):
        self.calls: list[tuple[str, str]] = []
        self._critic_seq = list(critic_need_more)
        self._critic_i = 0

    async def complete(self, system: str, user: str, *, tier: str = "main") -> str:
        if system.startswith("You are the triage"):
            self.calls.append(("triage", tier))
            return '{"source_types": ["runbook"], "query": "gcm oom heap"}'
        if system.startswith("You are the diagnosis"):
            self.calls.append(("diagnose", tier))
            return "heap regression after 1.8.0 [runbook: GCM OOM Runbook]"
        if system.startswith("You are the critic"):
            need_more = self._critic_seq[min(self._critic_i, len(self._critic_seq) - 1)]
            self._critic_i += 1
            self.calls.append(("critic", tier))
            return f'{{"grounded": true, "confidence": "high", "need_more": {str(need_more).lower()}, "note": "ok"}}'
        self.calls.append(("synthesize", tier))
        return _SYNTH


class _Embedder:
    async def embed_documents(self, texts):
        return [[0.1] * 4 for _ in texts]

    async def embed_query(self, text):
        return [0.1] * 4


class _Retriever:
    def __init__(self, chunk):
        self.chunk = chunk
        self.calls = 0

    async def search(self, *, query_embedding, service, source_type=None, top_k=6, min_similarity=0.0):
        self.calls += 1
        return [self.chunk]


def _chunk():
    return RetrievedChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        source_type="runbook",
        service="GCM",
        title="GCM OOM Runbook",
        content="Roll back and raise memory.",
        similarity=0.9,
    )


async def test_graph_flow_and_tiering():
    chat, chunk = _ScriptedChat(), _chunk()
    graph = GraphAnalyzer(chat, _Embedder(), _Retriever(chunk), model_label="graph:test")

    draft = await graph.analyze(dict(_CTX))

    assert draft.severity == "critical"
    assert draft.model_id == "graph:test"
    assert draft.evidence_chunk_ids == (chunk.id,)
    # one pass: triage(fast) -> diagnose(main) -> critic(main) -> synthesize(fast)
    assert chat.calls == [
        ("triage", "fast"),
        ("diagnose", "main"),
        ("critic", "main"),
        ("synthesize", "fast"),
    ]


async def test_critic_loop_reretrieves_then_finishes():
    chat, chunk = _ScriptedChat(critic_need_more=(True, False)), _chunk()
    retriever = _Retriever(chunk)
    graph = GraphAnalyzer(chat, _Embedder(), retriever, model_label="graph:test", max_rounds=2)

    draft = await graph.analyze(dict(_CTX))

    triage_calls = [c for c in chat.calls if c[0] == "triage"]
    critic_calls = [c for c in chat.calls if c[0] == "critic"]
    assert len(triage_calls) == 2  # looped back once
    assert len(critic_calls) == 2
    assert retriever.calls == 2  # retrieved again on the second round
    assert draft.severity == "critical"
    assert draft.evidence_chunk_ids == (chunk.id,)  # deduped across rounds
