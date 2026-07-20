"""Application settings, loaded from environment variables / .env.

Defaults match the Step 0 brain (`domain/incidents/prompts.py`) so the API behaves the same when it
wraps the analysis. See `.claude/specs/SPEC.md` section 13 for the full env var list.

pydantic-settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "IIM"
    debug: bool = False
    # Comma-separated list of allowed CORS origins (the Vite dev server / nginx).
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # --- Database (Postgres + pgvector) ---
    # asyncpg driver; overridden by DATABASE_URL in compose.
    database_url: str = "postgresql+asyncpg://iim:iim@localhost:5432/iim"

    # --- Analysis pipeline ---
    analysis_mode: str = "single"  # single (RAG single-call) | graph (multi-agent LangGraph)

    # --- LLM provider (decision 0016) ---
    llm_provider: str = "bedrock"  # bedrock | deepseek
    max_rounds: int = 2  # critic corrective-retrieval loop cap

    # Bedrock (Claude)
    aws_region: str = "ap-southeast-1"
    model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"  # main tier (diagnosis, critic)
    fast_model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"  # Haiku tier (triage, etc.)

    # DeepSeek (OpenAI-compatible)
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    # --- Embedding provider (decision 0016) ---
    embedding_provider: str = "titan"  # titan | jina
    embedding_model: str = "amazon.titan-embed-text-v2:0"
    embedding_dim: int = 1024  # Titan v2 = 1024, Jina jina-embeddings-v3 = 768

    # Jina
    jina_api_key: str | None = None
    jina_base_url: str = "https://api.jina.ai/v1/embeddings"

    # --- Cache ---
    cache_ttl_seconds: int = 1800  # 30 min, matches Step 0 CACHE_TTL_SECONDS

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
