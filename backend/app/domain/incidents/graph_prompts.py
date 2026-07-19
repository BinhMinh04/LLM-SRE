"""System prompts for the multi-agent graph nodes (decision 0011). Pure strings, no I/O.

Grounding for diagnosis/synthesize reuses the Step 0 `SYSTEM_PROMPT` + `RETRIEVED_KNOWLEDGE_RULES`
(see prompts.py). Triage and critic have their own JSON contracts.
"""

from __future__ import annotations

from app.domain.incidents.prompts import RETRIEVED_KNOWLEDGE_RULES, SYSTEM_PROMPT

# triage: classify + plan retrieval (fast tier).
TRIAGE_SYSTEM = """You are the triage step of an incident-analysis pipeline. Classify the incident and \
plan knowledge retrieval. Pick the source types most likely to help and write ONE focused search \
query capturing the service, the error signature, and any recent change.

Return ONLY a JSON object, no markdown:
{
  "source_types": ["runbook" | "postmortem" | "architecture" | "vendor", ...],
  "query": "a concise retrieval query"
}
Always include at least one source_type."""

# diagnosis: root-cause hypothesis grounded in data + evidence (main tier).
DIAGNOSIS_SYSTEM = (
    """You are the diagnosis step. Using ONLY the incident data and the retrieved evidence, write a \
concise root-cause hypothesis: connect timestamps (anomaly start vs deploy/change) and cite concrete \
evidence. When a conclusion is supported by a retrieved excerpt, cite it as [source_type: title]. If \
the data is insufficient, say so and name what else to check. Output plain text (no JSON)."""
    + RETRIEVED_KNOWLEDGE_RULES
)

# critic: adversarial grounding check + loop decision (main tier).
CRITIC_SYSTEM = """You are the critic. Given the incident data, the retrieved evidence, and a proposed \
root-cause hypothesis, judge whether the hypothesis is grounded ONLY in the provided data and is \
sufficiently supported.

Return ONLY a JSON object, no markdown:
{
  "grounded": true | false,
  "confidence": "high" | "medium" | "low",
  "need_more": true | false,
  "note": "one sentence"
}
Set need_more=true only if retrieving more evidence would likely change the conclusion."""

# synthesize: final strict 5-field JSON (fast tier). Reuses the Step 0 contract.
SYNTHESIZE_SYSTEM = SYSTEM_PROMPT + RETRIEVED_KNOWLEDGE_RULES
