"""
Application configuration — loaded from environment variables via pydantic-settings.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "CekInvest API"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False

    # ── Database (Prisma Postgres) ────────────────────────────────────────────
    DATABASE_URL: str

    # ── SENTRA AI Engine (Gemini 2.5 Flash) ──────────────────────────────────
    GEMINI_API_KEY: str
    GEMINI_API_KEY_BACKUP_1: str | None = None
    SENTRA_MODEL: str = "gemini-2.5-flash"
    SENTRA_MODEL_BACKUP_1: str = "gemini-2.5-flash-lite"

    # ── Upstash Redis (Cache + Rate Limit) ────────────────────────────────────
    # Free tier: 10,000 req/day. Sign up at https://upstash.com
    UPSTASH_REDIS_URL: str | None = None
    UPSTASH_REDIS_TOKEN: str | None = None

    # ── Cache TTL Settings ────────────────────────────────────────────────────
    OJK_CACHE_TTL_HOURS: int = 1          # OJK entity list: refresh every 1 hour
    ANALYSIS_CACHE_TTL_HOURS: int = 24    # Identical analysis deduplication: 24 hours
    MEDIA_CACHE_TTL_HOURS: int = 1        # RSS news search cache

    # ── Intelligence Settings ─────────────────────────────────────────────────
    DOMAIN_AGE_RED_FLAG_DAYS: int = 90    # Domains < 90 days old = red flag (PRD #15)
    UNREALISTIC_RETURN_THRESHOLD: float = 3.0  # Return > 3%/month = red flag (PRD #14)

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Frontend ───────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
