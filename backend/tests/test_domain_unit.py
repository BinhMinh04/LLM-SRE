"""Unit tests for the incident domain + the analyzer's response parsing — no DB or network.

Covers: fingerprint reuse (deploy-version sensitivity, digit/hex normalization), qualitative->numeric
confidence mapping, LLM response parsing, and that both canonical sample shapes render + fingerprint.
"""

import json
from pathlib import Path

import pytest

from app.domain.incidents.confidence import confidence_to_score
from app.domain.incidents.fingerprint import fingerprint
from app.domain.incidents.prompts import build_user_message
from app.infrastructure.llm.parsing import AnalysisError, parse_analysis

_SAMPLES = Path(__file__).parent / "samples"

# --- fingerprint reuse -------------------------------------------------------

_BASE_CTX = {
    "service": "GCM",
    "sample_logs": [{"message": "java.lang.OutOfMemoryError: heap 0x1a2b3c4d after 4096 reqs"}],
    "recent_deploy": {"version": "1.8.0"},
}


def test_fingerprint_is_stable_for_same_context():
    assert fingerprint(dict(_BASE_CTX)) == fingerprint(dict(_BASE_CTX))


def test_fingerprint_changes_on_new_deploy_version():
    other = {**_BASE_CTX, "recent_deploy": {"version": "1.9.0"}}
    assert fingerprint(_BASE_CTX) != fingerprint(other)


def test_fingerprint_normalizes_digits_and_hex():
    a = {**_BASE_CTX, "sample_logs": [{"message": "OOM heap 0xdeadbeef after 10 reqs"}]}
    b = {**_BASE_CTX, "sample_logs": [{"message": "OOM heap 0xcafef00d after 99 reqs"}]}
    assert fingerprint(a) == fingerprint(b)


# --- confidence mapping ------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("high", 0.9),
        ("Medium", 0.6),
        ("LOW", 0.3),
        (0.82, 0.82),
        (1, 1.0),
        ("unknown", None),
        (None, None),
        (True, None),  # bool guarded off (int subclass)
    ],
)
def test_confidence_to_score(label, expected):
    assert confidence_to_score(label) == expected


# --- LLM response parsing ----------------------------------------------------

_VALID = (
    '{"severity":"critical","summary":"s","root_cause":"r",'
    '"recommended_action":"a","confidence":"high"}'
)


def test_parse_analysis_valid():
    out = parse_analysis(_VALID)
    assert out["severity"] == "critical"
    assert out["confidence"] == "high"


def test_parse_analysis_strips_code_fences():
    fenced = f"```json\n{_VALID}\n```"
    assert parse_analysis(fenced)["summary"] == "s"


def test_parse_analysis_missing_field_raises():
    with pytest.raises(AnalysisError):
        parse_analysis('{"severity":"info","summary":"s"}')


def test_parse_analysis_non_json_raises():
    with pytest.raises(AnalysisError):
        parse_analysis("I could not analyze this incident.")


def test_parse_analysis_non_object_raises():
    with pytest.raises(AnalysisError):
        parse_analysis("[1, 2, 3]")


# --- both canonical sample shapes --------------------------------------------


@pytest.mark.parametrize("name", ["infra_oom", "apicost_overage"])
def test_samples_render_and_fingerprint(name):
    ctx = json.loads((_SAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    msg = build_user_message(ctx)
    assert f"Service: {ctx['service']}" in msg
    assert len(fingerprint(ctx)) == 16
