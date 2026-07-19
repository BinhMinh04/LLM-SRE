"""Unit tests for provider selection (decision 0016) — no network.

`select_base_analyzer` / `select_embedder` pick the adapter from config. Bedrock/Titan are the defaults;
DeepSeek/Jina are opt-in via LLM_PROVIDER / EMBEDDING_PROVIDER.
"""

from app.infrastructure.config import Settings
from app.infrastructure.llm.bedrock_analyzer import BedrockAnalyzer
from app.infrastructure.llm.deepseek_analyzer import DeepSeekAnalyzer
from app.infrastructure.llm.jina_embedder import JinaEmbedder
from app.infrastructure.llm.titan_embedder import TitanEmbedder
from app.interface.http.deps import select_base_analyzer, select_embedder


def _settings(**overrides) -> Settings:
    # Ignore any ambient .env so defaults are deterministic in the test.
    base = dict(
        llm_provider="bedrock",
        embedding_provider="titan",
        embedding_dim=1024,
        deepseek_api_key=None,
        jina_api_key=None,
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_defaults_are_bedrock_and_titan():
    s = _settings()
    assert isinstance(select_base_analyzer(s), BedrockAnalyzer)
    assert isinstance(select_embedder(s), TitanEmbedder)


def test_deepseek_selected_when_configured():
    s = _settings(llm_provider="deepseek", deepseek_api_key="x")
    assert isinstance(select_base_analyzer(s), DeepSeekAnalyzer)


def test_jina_selected_when_configured():
    s = _settings(embedding_provider="jina", embedding_model="jina-embeddings-v3", jina_api_key="x")
    assert isinstance(select_embedder(s), JinaEmbedder)
