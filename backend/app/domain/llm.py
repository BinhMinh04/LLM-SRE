"""Generic LLM chat port used by the multi-agent graph nodes (decision 0011).

Distinct from `Analyzer` (which returns a fixed 5-field analysis): the graph's triage / diagnosis /
critic / synthesize steps need free-form completions. `tier` selects the model tier for cost control:
`fast` for mechanical steps, `main` for diagnosis/critic. Implemented by infrastructure adapters
(Bedrock, DeepSeek).
"""

from __future__ import annotations

from typing import Literal, Protocol

Tier = Literal["fast", "main"]


class ChatModel(Protocol):
    async def complete(self, system: str, user: str, *, tier: Tier = "main") -> str: ...
