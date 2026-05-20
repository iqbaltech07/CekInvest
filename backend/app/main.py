"""
CekInvest API v2.1 — FastAPI application factory.
Powered by SENTRA AI Engine (Gemini 2.5 Flash) + Prisma Postgres + Upstash Redis.
PRD v2.1 — Zero Budget Edition. All endpoints public — no login required.
"""
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import connect, disconnect
from app.routers import analysis_router, intelligence_router, reports_router, share_router, chat_router, clustering_router
from app.services.sentra_service import get_sentra

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 60


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect Prisma, warm SENTRA, verify Redis. Shutdown: clean disconnect."""
    logger.info("🚀 Starting CekInvest API v2.1 — SENTRA + Prisma + Upstash Redis")

    # Database
    await connect()
    logger.info("✅ Prisma connected to database")

    # SENTRA AI engine
    get_sentra()
    logger.info("✅ SENTRA AI engine ready (Gemini 2.5 Flash + Google Search Grounding)")

    # Redis connectivity check
    from app.services.cache_service import _get_client
    redis = _get_client()
    if redis:
        logger.info("✅ Upstash Redis connected — caching active")
    else:
        logger.warning("⚠️  Upstash Redis not available — running without cache (degraded mode)")

    yield

    await disconnect()
    logger.info("🛑 Prisma disconnected — CekInvest API v2.1 shut down")


# ── App Factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "CekInvest — AI Financial Threat Intelligence Platform powered by **SENTRA**.\n\n"
            "Melindungi masyarakat Indonesia dari penipuan investasi melalui:\n"
            "- 🤖 **SENTRA AI** (Gemini 2.5 Flash + Google Search Grounding)\n"
            "- 🏛️ **OJK Real-time Check** — status database Satgas Waspada Investasi\n"
            "- 🌐 **WHOIS Domain Intel** — deteksi domain muda dan hosting mencurigakan\n"
            "- 📰 **Media Intelligence** — pemberitaan negatif dari Detik, Kompas, Tempo\n"
            "- 👥 **Community Database** — laporan nomor rekening dan telepon scam\n"
            "- 📤 **Shareable Reports** — laporan yang bisa dibagikan tanpa perlu akun\n"
            "- 💬 **AI Scam Guardian Chat** — tanya jawab lanjutan setelah analisis\n\n"
            "**Tidak perlu login** — langsung analisis, gratis untuk semua orang."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def public_rate_limit(request: Request, call_next):
        """Rate limit using Upstash Redis with fallback to in-memory guardrail."""
        if request.url.path.startswith(API_PREFIX):
            from app.services.cache_service import check_rate_limit
            client_ip = request.client.host if request.client else "unknown"
            
            is_allowed = await check_rate_limit(
                ip=client_ip,
                max_requests=_RATE_LIMIT_MAX_REQUESTS,
                window_seconds=_RATE_LIMIT_WINDOW_SECONDS
            )
            
            if not is_allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Terlalu banyak permintaan. Silakan coba lagi sebentar lagi.",
                        },
                    },
                    headers={"Retry-After": str(_RATE_LIMIT_WINDOW_SECONDS)},
                )
        return await call_next(request)

    # ── Global Exception Handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s: %s", request.method, request.url, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Terjadi kesalahan internal. Tim kami sedang menangani masalah ini.",
                },
            },
        )

    # ── Health Check ──────────────────────────────────────────────────────────
    @app.get(f"{API_PREFIX}/health", tags=["Health"], summary="Service health check")
    async def health_check():
        from app.services.cache_service import _get_client
        redis_ok = _get_client() is not None
        return {
            "success": True,
            "data": {
                "status": "ok",
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "ai_engine": "SENTRA (Gemini 2.5 Flash)",
                "grounding": "Google Search enabled",
                "database": "Prisma Postgres",
                "cache": "Upstash Redis (active)" if redis_ok else "disabled (degraded)",
                "auth_required": False,
                "prd_version": "2.1 — Zero Budget Edition",
            },
        }

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(analysis_router, prefix=API_PREFIX)
    app.include_router(reports_router, prefix=API_PREFIX)
    app.include_router(intelligence_router, prefix=API_PREFIX)
    app.include_router(share_router, prefix=API_PREFIX)      # PRD 5.5 — Shareable Reports
    app.include_router(chat_router, prefix=API_PREFIX)       # PRD 5.4 — AI Scam Guardian
    app.include_router(clustering_router, prefix=API_PREFIX) # Non-AI Clustering & Regional Monitoring

    logger.info(
        "All routers registered under %s — analysis, reports, intelligence, share, chat, clustering",
        API_PREFIX,
    )
    return app


app = create_app()
