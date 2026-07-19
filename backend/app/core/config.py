"""Application settings, loaded from environment variables / .env.

Defaults match the Step 0 brain (`ai/analyze_incident.py`) so the API behaves the same when it
wraps `analyze()` in M2. See `.claude/specs/SPEC.md` section 13 for the full env var list.

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

    # --- Bedrock / models (reused from Step 0 constants; see ai/analyze_incident.py) ---
    aws_region: str = "ap-southeast-1"
    model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"  # main tier (diagnosis, critic)
    fast_model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"  # Haiku tier (triage, etc.)
    embed_model_id: str = "amazon.titan-embed-text-v2:0"  # Titan v2, 1024-dim
    max_rounds: int = 2  # critic corrective-retrieval loop cap

    # --- Cache ---
    cache_ttl_seconds: int = 1800  # 30 min, matches Step 0 CACHE_TTL_SECONDS

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
