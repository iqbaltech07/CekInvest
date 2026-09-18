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
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "CekInvest API"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = False

    # ── Database (Prisma Postgres) ────────────────────────────────────────────
    DATABASE_URL: str

    # ── SENTRA AI Engine (Gemini 2.5 Flash + Fallback Chain) ────────────────
    GEMINI_API_KEY: str
    GEMINI_API_KEY_BACKUP_1: str | None = None
    GEMINI_API_KEY_BACKUP_2: str | None = None
    GEMINI_API_KEY_BACKUP_3: str | None = None
    SENTRA_MODEL: str = "gemini-2.5-flash"
    SENTRA_MODEL_BACKUP_1: str | None = "gemini-2.5-flash-lite"
    SENTRA_MODEL_BACKUP_2: str | None = "gemini-3.5-flash"
    SENTRA_MODEL_BACKUP_3: str | None = "gemini-3.8-flash"
    SENTRA_MODEL_FALLBACKS: list[str] = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash",
    ]

    def get_gemini_api_keys(self) -> list[str]:
        """
        Returns all configured Gemini API keys in priority order.
        Supports comma-separated keys and deduplicates while preserving order.
        """
        raw_keys = [
            self.GEMINI_API_KEY,
            self.GEMINI_API_KEY_BACKUP_1,
            self.GEMINI_API_KEY_BACKUP_2,
            self.GEMINI_API_KEY_BACKUP_3,
        ]
        keys: list[str] = []
        for rk in raw_keys:
            if not rk:
                continue
            for k in rk.split(","):
                clean = k.strip()
                if clean and clean not in keys:
                    keys.append(clean)
        return keys

    def get_sentra_models(self) -> list[str]:
        """
        Returns candidate models in prioritized fallback order.
        """
        candidates = [
            self.SENTRA_MODEL,
            self.SENTRA_MODEL_BACKUP_1,
            self.SENTRA_MODEL_BACKUP_2,
            self.SENTRA_MODEL_BACKUP_3,
        ] + (self.SENTRA_MODEL_FALLBACKS or []) + [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ]
        models: list[str] = []
        for c in candidates:
            if c and c.strip() and c.strip() not in models:
                models.append(c.strip())
        return models

    # ── Dense Vector Embedding (gemini-embedding-001 + pgvector) ─────────────
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIM: int = 768

    # ── Upstash Redis (Cache + Rate Limit) ────────────────────────────────────
    # Free tier: 10,000 req/day. Sign up at https://upstash.com
    UPSTASH_REDIS_URL: str | None = None
    UPSTASH_REDIS_TOKEN: str | None = None

    # ── Cache TTL Settings ────────────────────────────────────────────────────
    OJK_CACHE_TTL_HOURS: int = 1          # OJK entity list: refresh every 1 hour
    ANALYSIS_CACHE_TTL_HOURS: int = 24    # Identical analysis deduplication: 24 hours
    MEDIA_CACHE_TTL_HOURS: int = 1        # RSS news search cache

    # ── OJK Endpoints (legalkah.id live indices) ──────────────────────────────
    OJK_LEGAL_ENDPOINT: str = "https://legalkah.id/search-index.json"
    OJK_ILLEGAL_ENDPOINT: str = "https://legalkah.id/historical-search-index.json"

    # ── Intelligence Settings ─────────────────────────────────────────────────
    DOMAIN_AGE_RED_FLAG_DAYS: int = 90    # Domains < 90 days old = red flag (PRD #15)
    UNREALISTIC_RETURN_THRESHOLD: float = 3.0  # Return > 3%/month = red flag (PRD #14)

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── GNN (Graph Neural Network) ───────────────────────────────────────────
    # Default False to keep RAM below 150 MB on Render Free Plan (512 MB limit).
    # Set ENABLE_GNN=true when running on high-RAM workers or local machines.
    ENABLE_GNN: bool = False

    # ── Frontend ───────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
