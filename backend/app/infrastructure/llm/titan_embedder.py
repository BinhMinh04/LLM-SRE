"""Titan Text Embeddings v2 adapter implementing the domain `Embedder` port.

Uses LangChain `BedrockEmbeddings` (1024-dim). The blocking Bedrock calls are offloaded with
`asyncio.to_thread` so they do not block the request event loop.

LangChain BedrockEmbeddings: https://python.langchain.com/docs/integrations/text_embedding/bedrock/
Titan Text Embeddings: https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html
"""

from __future__ import annotations

import asyncio

from langchain_aws import BedrockEmbeddings

from app.infrastructure.config import Settings


class TitanEmbedder:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: BedrockEmbeddings | None = None

    def _get_client(self) -> BedrockEmbeddings:
        if self._client is None:
            self._client = BedrockEmbeddings(
                model_id=self._settings.embedding_model,
                region_name=self._settings.aws_region,
            )
        return self._client

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._get_client().embed_documents, texts)

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._get_client().embed_query, text)
