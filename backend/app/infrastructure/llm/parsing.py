"""Shared parsing of an LLM's analysis response into the 5 contract fields.

Used by every Analyzer adapter (Bedrock, DeepSeek). Stripping code fences and validating the schema
is an infrastructure concern (it depends on how a provider formats output), not a domain rule.
"""

from __future__ import annotations

import json
import re

_ANALYSIS_FIELDS = ("severity", "summary", "root_cause", "recommended_action", "confidence")


class AnalysisError(RuntimeError):
    """The model returned something that is not a usable 5-field analysis."""


def strip_fences(text: str) -> str:
    """Remove ```json ... ``` fences the model sometimes wraps JSON in."""
    return re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()


def parse_analysis(raw: str) -> dict:
    """Parse and validate the model's JSON payload into the 5 contract fields."""
    text = strip_fences(raw)
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
