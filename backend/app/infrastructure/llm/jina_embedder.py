"""Jina embeddings adapter — implements the domain `Embedder` port (decision 0016).

Async `httpx` call to the Jina embeddings API. Uses `jina-embeddings-v3` task types
(`retrieval.passage` for stored chunks, `retrieval.query` for queries) and requests the configured
output dimension (768 by default). Lets RAG run locally without AWS Titan.

Jina Embeddings API: https://jina.ai/embeddings/
"""

from __future__ import annotations

import httpx

from app.infrastructure.config import Settings


class JinaEmbedderError(RuntimeError):
    pass


class JinaEmbedder:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(list(texts), task="retrieval.passage")

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([text], task="retrieval.query")
        return vectors[0]

    async def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        if not self._settings.jina_api_key:
            raise JinaEmbedderError("JINA_API_KEY is not set")
        payload = {
            "model": self._settings.embedding_model,
            "task": task,
            "dimensions": self._settings.embedding_dim,
            "input": texts,
        }
        headers = {"Authorization": f"Bearer {self._settings.jina_api_key}"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self._settings.jina_base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        try:
            items = sorted(data["data"], key=lambda d: d["index"])
        except (KeyError, TypeError) as exc:
            raise JinaEmbedderError(f"unexpected Jina response shape: {data}") from exc
        return [item["embedding"] for item in items]
