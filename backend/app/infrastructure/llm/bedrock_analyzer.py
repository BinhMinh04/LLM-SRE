"""Single-call analyzer via LangChain ChatBedrockConverse — implements the domain `Analyzer` port.

Reuses the domain prompt (`SYSTEM_PROMPT` + `build_user_message`) and returns an `AnalysisDraft`.
Response parsing is shared (`parsing.py`). The blocking Bedrock call is offloaded with
`asyncio.to_thread` so it does not block the request event loop.

LangChain ChatBedrockConverse: https://python.langchain.com/docs/integrations/chat/bedrock/
"""

from __future__ import annotations

import asyncio

from langchain_aws import ChatBedrockConverse

from app.domain.documents.entities import RetrievedChunk
from app.domain.incidents.entities import AnalysisDraft
from app.domain.incidents.prompts import (
    RETRIEVED_KNOWLEDGE_RULES,
    SYSTEM_PROMPT,
    build_user_message,
)
from app.infrastructure.config import Settings
from app.infrastructure.llm.parsing import parse_analysis

# Re-exported so existing imports (tests) keep working after parsing moved to parsing.py.
from app.infrastructure.llm.parsing import AnalysisError  # noqa: F401  (re-export)


class BedrockAnalyzer:
    """Analyzer backed by Bedrock (Claude) via LangChain ChatBedrockConverse."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: ChatBedrockConverse | None = None

    def _get_client(self) -> ChatBedrockConverse:
        if self._client is None:
            self._client = ChatBedrockConverse(
                model=self._settings.model_id,
                region_name=self._settings.aws_region,
                max_tokens=600,
                temperature=0.2,
            )
        return self._client

    async def analyze(
        self, context: dict, evidence: list[RetrievedChunk] | None = None
    ) -> AnalysisDraft:
        raw = await asyncio.to_thread(self._invoke, context, evidence)
        parsed = parse_analysis(raw)
        return AnalysisDraft(model_id=self._settings.model_id, **parsed)

    def _invoke(self, context: dict, evidence: list[RetrievedChunk] | None) -> str:
        system = SYSTEM_PROMPT + (RETRIEVED_KNOWLEDGE_RULES if evidence else "")
        response = self._get_client().invoke(
            [
                ("system", system),
                ("human", build_user_message(context, evidence)),
            ]
        )
        return response.content if isinstance(response.content, str) else str(response.content)
