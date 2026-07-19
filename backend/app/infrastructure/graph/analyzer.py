"""GraphAnalyzer: multi-agent incident analysis as a LangGraph state machine (decision 0011).

Graph: triage -> retrieve -> diagnose -> critic -> (loop to triage if weak & under MAX_ROUNDS, else
synthesize). Implements the domain `Analyzer` port, so it drops into the same ingest use case as the
single-pass `RagAnalyzer` (Open/Closed). Retrieval happens inside the graph; the returned draft
reports the chunk ids it grounded on. Node LLM calls go through the `ChatModel` port with tiering
(triage/synthesize on fast, diagnosis/critic on main).

LangGraph: https://langchain-ai.github.io/langgraph/
"""

from __future__ import annotations

import json
import re

from langgraph.graph import END, START, StateGraph

from app.domain.documents.entities import RetrievedChunk
from app.domain.documents.entities import SOURCE_TYPES
from app.domain.documents.ports import Embedder, Retriever
from app.domain.incidents.entities import AnalysisDraft
from app.domain.incidents.graph_prompts import (
    CRITIC_SYSTEM,
    DIAGNOSIS_SYSTEM,
    SYNTHESIZE_SYSTEM,
    TRIAGE_SYSTEM,
)
from app.domain.incidents.prompts import build_retrieval_query, build_user_message
from app.domain.llm import ChatModel
from app.infrastructure.graph.state import GraphState
from app.infrastructure.llm.parsing import parse_analysis


def _parse_json(raw: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


class GraphAnalyzer:
    def __init__(
        self,
        chat: ChatModel,
        embedder: Embedder,
        retriever: Retriever,
        *,
        model_label: str,
        max_rounds: int = 2,
        top_k: int = 6,
        min_similarity: float = 0.0,
    ) -> None:
        self._chat = chat
        self._embedder = embedder
        self._retriever = retriever
        self._model_label = model_label
        self._max_rounds = max_rounds
        self._top_k = top_k
        self._min_similarity = min_similarity
        self._graph = self._build()

    def _build(self):
        builder = StateGraph(GraphState)
        builder.add_node("triage", self._triage)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("diagnose", self._diagnose)
        builder.add_node("critic", self._critic)
        builder.add_node("synthesize", self._synthesize)
        builder.add_edge(START, "triage")
        builder.add_edge("triage", "retrieve")
        builder.add_edge("retrieve", "diagnose")
        builder.add_edge("diagnose", "critic")
        builder.add_conditional_edges(
            "critic", self._route, {"retry": "triage", "done": "synthesize"}
        )
        builder.add_edge("synthesize", END)
        return builder.compile()

    # --- nodes ---------------------------------------------------------------

    async def _triage(self, state: GraphState) -> dict:
        ctx = state["context"]
        raw = await self._chat.complete(
            TRIAGE_SYSTEM, build_user_message(ctx), tier="fast"
        )
        parsed = _parse_json(raw)
        source_types = [s for s in parsed.get("source_types", []) if s in SOURCE_TYPES]
        query = parsed.get("query") or build_retrieval_query(ctx)
        return {"source_types": source_types or list(SOURCE_TYPES), "query": query}

    async def _retrieve(self, state: GraphState) -> dict:
        query = state["query"] or build_retrieval_query(state["context"])
        if not query:
            return {"evidence": state["evidence"]}
        query_embedding = await self._embedder.embed_query(query)
        seen = {chunk.id for chunk in state["evidence"]}
        merged: list[RetrievedChunk] = list(state["evidence"])
        service = state["context"].get("service")
        for source_type in state["source_types"]:
            hits = await self._retriever.search(
                query_embedding=query_embedding,
                service=service,
                source_type=source_type,
                top_k=self._top_k,
                min_similarity=self._min_similarity,
            )
            for chunk in hits:
                if chunk.id not in seen:
                    seen.add(chunk.id)
                    merged.append(chunk)
        return {"evidence": merged}

    async def _diagnose(self, state: GraphState) -> dict:
        user = build_user_message(state["context"], state["evidence"])
        hypothesis = await self._chat.complete(DIAGNOSIS_SYSTEM, user, tier="main")
        return {"hypothesis": hypothesis}

    async def _critic(self, state: GraphState) -> dict:
        user = (
            build_user_message(state["context"], state["evidence"])
            + f"\n\n[PROPOSED ROOT CAUSE]\n{state['hypothesis']}"
        )
        critique = _parse_json(await self._chat.complete(CRITIC_SYSTEM, user, tier="main"))
        return {"critique": critique, "round": state["round"] + 1}

    async def _synthesize(self, state: GraphState) -> dict:
        note = state.get("critique", {}).get("note", "")
        user = (
            build_user_message(state["context"], state["evidence"])
            + f"\n\n[ROOT-CAUSE HYPOTHESIS]\n{state['hypothesis']}"
            + (f"\n\n[CRITIC NOTE]\n{note}" if note else "")
        )
        parsed = parse_analysis(await self._chat.complete(SYNTHESIZE_SYSTEM, user, tier="fast"))
        return {"draft": parsed}

    def _route(self, state: GraphState) -> str:
        critique = state.get("critique", {})
        if critique.get("need_more") and state["round"] < self._max_rounds:
            return "retry"
        return "done"

    # --- Analyzer port -------------------------------------------------------

    async def analyze(
        self, context: dict, evidence: list[RetrievedChunk] | None = None
    ) -> AnalysisDraft:
        initial: GraphState = {
            "context": context,
            "source_types": [],
            "query": "",
            "evidence": list(evidence or []),
            "hypothesis": "",
            "critique": {},
            "round": 0,
            "draft": {},
        }
        final = await self._graph.ainvoke(initial)
        fields = final["draft"]
        return AnalysisDraft(
            model_id=self._model_label,
            evidence_chunk_ids=tuple(chunk.id for chunk in final["evidence"]),
            **fields,
        )
