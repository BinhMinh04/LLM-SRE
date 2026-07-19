"""Single-call analyzer via LangChain ChatBedrockConverse — implements the domain `Analyzer` port.

Reuses the domain prompt (`SYSTEM_PROMPT` + `build_user_message`) and returns an `AnalysisDraft`.
Parsing the provider's response (stripping code fences, validating the 5 fields) is an infrastructure
concern and lives here. The blocking Bedrock call is offloaded with `asyncio.to_thread` so it does
not block the request event loop. This is the seam M3's LangGraph analyzer replaces.

LangChain ChatBedrockConverse: https://python.langchain.com/docs/integrations/chat/bedrock/
"""

from __future__ import annotations

import asyncio
import json
import re

from langchain_aws import ChatBedrockConverse

from app.domain.incidents.entities import AnalysisDraft
from app.domain.incidents.prompts import SYSTEM_PROMPT, build_user_message
from app.infrastructure.config import Settings

_ANALYSIS_FIELDS = ("severity", "summary", "root_cause", "recommended_action", "confidence")


class AnalysisError(RuntimeError):
    """The model returned something that is not a usable 5-field analysis."""


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

    async def analyze(self, context: dict) -> AnalysisDraft:
        raw = await asyncio.to_thread(self._invoke, context)
        parsed = _parse_analysis(raw)
        return AnalysisDraft(model_id=self._settings.model_id, **parsed)

    def _invoke(self, context: dict) -> str:
        response = self._get_client().invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", build_user_message(context)),
            ]
        )
        return response.content if isinstance(response.content, str) else str(response.content)


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` fences the model sometimes wraps JSON in."""
    return re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()


def _parse_analysis(raw: str) -> dict:
    """Parse and validate the model's JSON payload into the 5 contract fields."""
    text = _strip_fences(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"model did not return valid JSON: {text[:200]}") from exc
    if not isinstance(data, dict):
        raise AnalysisError(f"model returned a non-object JSON value: {type(data).__name__}")
    missing = [f for f in _ANALYSIS_FIELDS if f not in data]
    if missing:
        raise AnalysisError(f"model response missing fields: {missing}")
    return {f: data[f] for f in _ANALYSIS_FIELDS}
