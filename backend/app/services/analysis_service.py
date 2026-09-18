"""
Analysis service v2.1 — orchestrates the full SENTRA pipeline.
Additions:
  - Input deduplication via SHA-256 hash + Redis cache
  - Parallel intelligence orchestration (OJK, WHOIS, media, community DB)
  - Shareable report slug generation
  - New fields: explanation, trapQuestions, ojkStatus, shareSlug, domainAgeDays
"""
import asyncio
import hashlib
import logging
import re
import secrets
import socket
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address, ip_network
from urllib.parse import urlparse

import httpx
from prisma import Prisma
from prisma.enums import InputType, RiskLevel, OjkStatus

from app.schemas.analysis import SentraAnalysisResult
from app.services.sentra_service import SentraService
from app.services.risk_scorer import boost_score_from_patterns, compute_final_result
from app.services.cache_service import cache_get, cache_set, make_analysis_key
from app.services.emotion_signal_service import normalize_emotion_signals
from app.services.intelligence_orchestrator import run_parallel_checks
from app.utils.exceptions import BadRequestException, NotFoundException

logger = logging.getLogger(__name__)


# ── Public pipeline functions ──────────────────────────────────────────────────

async def analyze_chat(text: str, sentra: SentraService, db: Prisma):
    """Analyze pasted chat/text through the full SENTRA intelligence pipeline."""
    # Deduplication check
    cached = await _check_dedup_cache(text, db=db)
    if cached:
        return cached

    # Run intelligence checks in parallel with SENTRA prep
    intel = await run_parallel_checks(
        content=text, input_type="CHAT", url=None, db=db, sentra=sentra
    )

    sentra_result = await sentra.analyze(
        content=text,
        context_hint="chat WhatsApp/Telegram",
        intelligence_context=intel.to_prompt_context(),
    )
    result = await _persist_analysis(
        raw_input=text,
        input_type=InputType.CHAT,
        extracted_text=text,
        sentra_result=sentra_result,
        intel=intel,
        db=db,
    )
    # Auto-Ingestion Flywheel: HIGH/CRITICAL analyses feed the threat intelligence database
    await _auto_feed_to_threat_intelligence(result, text, db)
    return result


async def analyze_screenshot(image_bytes: bytes, sentra: SentraService, db: Prisma):
    """Extract text from screenshot via OCR, then analyze through SENTRA pipeline."""
    from app.services.ocr_service import extract_text_from_image

    try:
        extracted_text = await extract_text_from_image(image_bytes)
    except ValueError as exc:
        raise BadRequestException(str(exc)) from exc

    if not extracted_text.strip():
        raise BadRequestException(
            "Tidak ada teks yang terdeteksi dalam screenshot. "
            "Pastikan gambar berisi teks yang jelas."
        )

    # Deduplication on extracted text
    cached = await _check_dedup_cache(extracted_text, db=db)
    if cached:
        return cached

    intel = await run_parallel_checks(
        content=extracted_text, input_type="SCREENSHOT", url=None, db=db, sentra=sentra
    )
    sentra_result = await sentra.analyze(
        content=extracted_text,
        context_hint="screenshot percakapan/iklan investasi",
        intelligence_context=intel.to_prompt_context(),
    )
    result = await _persist_analysis(
        raw_input=f"[SCREENSHOT] {len(image_bytes)} bytes",
        input_type=InputType.SCREENSHOT,
        extracted_text=extracted_text,
        sentra_result=sentra_result,
        intel=intel,
        db=db,
    )
    # Auto-Ingestion Flywheel
    await _auto_feed_to_threat_intelligence(result, extracted_text, db)
    return result


async def analyze_url(url: str, sentra: SentraService, db: Prisma):
    """Fetch URL content and analyze through SENTRA pipeline with WHOIS enrichment."""
    url = await _normalize_and_validate_public_url(url)

    # Deduplication on URL
    cache_key = make_analysis_key(f"url:{url}")
    from app.config import settings
    cached_data = await cache_get(cache_key)
    if cached_data and isinstance(cached_data, str):
        analysis = await db.analysis.find_unique(
            where={"id": cached_data},
            include={"redFlags": True, "emotionSignals": True},
        )
        if analysis:
            logger.info("URL analysis cache HIT: %s", url)
            return analysis

    # Try to fetch content, but don't crash if it fails (fallback to AI grounding)
    try:
        page_content = await _fetch_url_content(url)
        content_hint = f"URL: {url}\n\nKonten halaman:\n{page_content}"
    except Exception as exc:
        logger.warning("Direct URL fetch failed for %s: %s. Falling back to AI grounding.", url, exc)
        page_content = f"[Peringatan: Akses langsung ke website ini diblokir atau gagal ({type(exc).__name__}). Silakan gunakan riset web untuk menganalisis URL ini.]"
        content_hint = f"URL: {url}\n\n(Akses langsung gagal, lakukan riset web mendalam untuk URL ini)"

    intel = await run_parallel_checks(
        content=content_hint,
        input_type="URL",
        url=url,
        db=db,
        sentra=sentra,
    )
    sentra_result = await sentra.analyze(
        content=content_hint,
        context_hint="halaman web investasi",
        intelligence_context=intel.to_prompt_context(),
    )
    result = await _persist_analysis(
        raw_input=url,
        input_type=InputType.URL,
        extracted_text=page_content,
        sentra_result=sentra_result,
        intel=intel,
        db=db,
    )
    # Cache URL → analysis ID
    await cache_set(cache_key, result.id, ttl_seconds=settings.ANALYSIS_CACHE_TTL_HOURS * 3600)
    # Auto-Ingestion Flywheel
    await _auto_feed_to_threat_intelligence(result, page_content, db)
    return result


async def get_analysis_by_id(analysis_id: str, db: Prisma):
    """Fetch a complete analysis result with all related data."""
    analysis = await db.analysis.find_unique(
        where={"id": analysis_id},
        include={"redFlags": True, "emotionSignals": True},
    )
    if not analysis:
        raise NotFoundException("Analysis")
    return analysis


async def get_analysis_by_slug(slug: str, db: Prisma):
    """Fetch an analysis by its public share slug."""
    analysis = await db.analysis.find_unique(
        where={"shareSlug": slug},
        include={"redFlags": True, "emotionSignals": True},
    )
    if not analysis:
        raise NotFoundException("Report")
    return analysis


# ── Internal Pipeline ─────────────────────────────────────────────────────────

async def _check_dedup_cache(text: str, db: Prisma | None = None):
    """
    Check Multi-Layer Cache for identical analysis:
    1. L1 RAM / L2 Redis Cache
    2. L3 Database Cache (inputHash index within TTL)
    Returns existing analysis and completely skips Gemini API call if found.
    """
    from app.config import settings
    from app.database import prisma as default_prisma

    active_db = db or default_prisma
    if not active_db.is_connected():
        try:
            await active_db.connect()
        except Exception:
            pass

    cache_key = make_analysis_key(text)
    cached_id = await cache_get(cache_key)
    if cached_id and isinstance(cached_id, str):
        try:
            analysis = await active_db.analysis.find_unique(
                where={"id": cached_id},
                include={"redFlags": True, "emotionSignals": True},
            )
            if analysis:
                logger.info("Analysis dedup cache HIT (L1/L2) — skipping Gemini API call")
                return analysis
        except Exception as exc:
            logger.warning("Cache id lookup failed: %s", exc)

    # L3: Fallback to PostgreSQL database cache via indexed inputHash
    try:
        input_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        db_analysis = await active_db.analysis.find_first(
            where={
                "inputHash": input_hash,
            },
            order={"createdAt": "desc"},
            include={"redFlags": True, "emotionSignals": True},
        )
        if db_analysis:
            logger.info("Analysis dedup cache HIT (L3 DB: %s) — skipping Gemini API call", input_hash[:8])
            # Re-populate L1 cache for fast subsequent hits
            await cache_set(cache_key, db_analysis.id, ttl_seconds=settings.ANALYSIS_CACHE_TTL_HOURS * 3600)
            return db_analysis
    except Exception as exc:
        logger.warning("DB dedup check skipped: %s", exc)

    return None


async def _persist_analysis(
    raw_input: str,
    input_type: InputType,
    extracted_text: str,
    sentra_result: SentraAnalysisResult,
    intel,
    db: Prisma,
):
    """Persist SENTRA's analysis + intelligence findings via Prisma nested writes."""
    from app.config import settings

    # Normalize emotion signals early so psychological manipulation can boost risk score
    normalized_emotion_signals = normalize_emotion_signals(
        extracted_text,
        sentra_result.emotion_signals,
    )

    boosted_score = await boost_score_from_patterns(
        extracted_text,
        sentra_result.risk_score,
        db,
        intel,
        emotion_signals=normalized_emotion_signals,
    )
    final_score, final_level, safe_to_invest = compute_final_result(sentra_result, boosted_score)

    # Map OJK status to Prisma enum
    ojk_status_map = {
        "TERDAFTAR": OjkStatus.TERDAFTAR,
        "TIDAK_TERDAFTAR": OjkStatus.TIDAK_TERDAFTAR,
        "TERINDIKASI_ILEGAL": OjkStatus.TERINDIKASI_ILEGAL,
        "TIDAK_DITEMUKAN": OjkStatus.TIDAK_DITEMUKAN,
    }
    ojk_status = ojk_status_map.get(intel.ojk_status, OjkStatus.TIDAK_DITEMUKAN)

    # Generate unique share slug
    share_slug = secrets.token_urlsafe(8)

    # Build nested data
    red_flags_data = [
        {
            "category": flag.category,
            "description": flag.description,
            "severity": flag.severity.value,
            "confidence": flag.confidence,
            "excerpt": flag.excerpt,
        }
        for flag in sentra_result.red_flags
    ]
    emotion_signals_data = [
        {
            "signalType": signal.type.value,
            "detected": signal.detected,
            "description": signal.description,
            "examples": signal.examples,
        }
        for signal in normalized_emotion_signals
    ]

    # Input hash for deduplication (only for text-based inputs)
    input_hash = None
    if input_type in (InputType.CHAT, InputType.SCREENSHOT):
        import hashlib
        input_hash = hashlib.sha256(extracted_text.strip().lower().encode()).hexdigest()

    analysis = await db.analysis.create(
        data={
            "inputType": input_type.value,
            "rawInput": raw_input[:10_000],
            "extractedText": extracted_text[:50_000],
            "riskScore": final_score,
            "riskLevel": final_level.value,
            "safeToInvest": safe_to_invest,
            "summary": sentra_result.summary,
            "explanation": sentra_result.explanation,
            "trapQuestions": sentra_result.trap_questions,
            "ojkStatus": ojk_status.value,
            "ojkEntityName": intel.ojk_entity_name,
            "shareSlug": share_slug,
            "domainAgeDays": intel.domain_age_days,
            "domainCountry": intel.domain_country,
            "mediaHitCount": intel.negative_news_count,
            "inputHash": input_hash,
            "redFlags": {"create": red_flags_data},
            "emotionSignals": {"create": emotion_signals_data},
        },
        include={"redFlags": True, "emotionSignals": True},
    )

    logger.info(
        "Analysis created: id=%s slug=%s risk=%s score=%d ojk=%s",
        analysis.id, share_slug, final_level.value, final_score, intel.ojk_status,
    )

    # Cache analysis ID for deduplication
    if input_hash:
        cache_key = make_analysis_key(extracted_text)
        await cache_set(cache_key, analysis.id, ttl_seconds=settings.ANALYSIS_CACHE_TTL_HOURS * 3600)

    return analysis


async def _auto_feed_to_threat_intelligence(analysis, content: str, db: Prisma) -> None:
    """
    Auto-Ingestion Flywheel (PRD 13):
    Automatically feeds HIGH/CRITICAL risk analyses into the threat intelligence database.
    - Creates a UserReport record as a validated data point
    - Generates a 768-dim gemini-embedding-001 vector and stores it in report_embeddings
    This ensures every real-world scam analysis strengthens SENTRA's future detection.
    """
    try:
        # Only ingest truly high-risk analyses (threshold: score >= 70 AND HIGH/CRITICAL)
        risk_level = getattr(analysis, "riskLevel", None)
        risk_score = getattr(analysis, "riskScore", 0)
        risk_level_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)

        if risk_level_str not in ("HIGH", "CRITICAL") or risk_score < 70:
            return

        input_type = getattr(analysis, "inputType", None)
        input_type_str = input_type.value if hasattr(input_type, "value") else str(input_type)

        logger.info(
            "🔄 Auto-Ingestion Flywheel triggered: analysis=%s risk=%s score=%d",
            analysis.id, risk_level_str, risk_score,
        )

        # ── Extract structured entities from the content ────────────────────
        from ml.utils import extract_phone_numbers, extract_bank_accounts, extract_domains

        phones = list(extract_phone_numbers(content))[:1]
        banks = list(extract_bank_accounts(content))[:1]
        domains = list(extract_domains(content))[:1]

        bank_name = banks[0][0] if banks else None
        bank_account = banks[0][1] if banks else None
        phone_number = phones[0] if phones else None
        domain = domains[0] if domains else None

        # ── Determine scam category from red flags (best-effort) ───────────
        scam_category = "Investasi Bodong"  # default
        if hasattr(analysis, "redFlags") and analysis.redFlags:
            # Use the category of the highest-severity red flag
            category_candidates = [f.category for f in analysis.redFlags if f.category]
            if category_candidates:
                scam_category = category_candidates[0]

        # ── Create UserReport (if not already exists via inputHash dedup) ──
        existing = await db.userreport.find_first(
            where={
                "rawInput": content[:500],
                "isScam": True,
            }
        )

        if existing:
            report_id = existing.id
            logger.debug("Auto-ingestion: UserReport already exists, reusing id=%s", report_id)
        else:
            new_report = await db.userreport.create(
                data={
                    "inputType": input_type_str,
                    "rawInput": content[:10_000],
                    "isScam": True,
                    "notes": f"Auto-ingested from Analysis {analysis.id} (SENTRA score={risk_score})",
                    "scamCategory": scam_category,
                    "bankName": bank_name,
                    "bankAccount": bank_account,
                    "phoneNumber": phone_number,
                    "domain": domain,
                }
            )
            report_id = new_report.id
            logger.info("Auto-ingestion: Created UserReport id=%s category=%s", report_id, scam_category)

        # ── Generate embedding and upsert to pgvector ───────────────────────
        from app.services.embedding_service import embedding_service
        from app.services.vector_store import vector_store

        embed_text = f"{scam_category}. {content[:2000]}"
        vec = await embedding_service.embed_text(embed_text)
        await vector_store.upsert_report_embedding(
            db=db,
            report_id=report_id,
            raw_input=content[:500],
            is_scam=True,
            scam_category=scam_category,
            embedding=vec,
        )

        logger.info(
            "✅ Auto-Ingestion Flywheel complete: report_id=%s embedded into pgvector",
            report_id,
        )

    except Exception as exc:
        # Non-fatal: never let flywheel block the main analysis response
        logger.warning("Auto-ingestion flywheel failed (non-fatal): %s", exc)


_BLOCKED_NETWORKS = [
    ip_network("0.0.0.0/8"),
    ip_network("10.0.0.0/8"),
    ip_network("127.0.0.0/8"),
    ip_network("169.254.0.0/16"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("224.0.0.0/4"),
    ip_network("240.0.0.0/4"),
    ip_network("::1/128"),
    ip_network("fc00::/7"),
    ip_network("fe80::/10"),
]


async def _normalize_and_validate_public_url(raw_url: str) -> str:
    """Normalize user URL and reject private/local targets before server-side fetch."""
    url = raw_url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise BadRequestException("URL tidak valid. Gunakan alamat website publik http/https.")

    host = parsed.hostname.strip().lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise BadRequestException("URL lokal tidak dapat dianalisis.")

    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as exc:
        raise BadRequestException("Domain tidak dapat ditemukan.") from exc

    for addr in addresses:
        candidate = ip_address(addr[4][0])
        if any(candidate in network for network in _BLOCKED_NETWORKS):
            raise BadRequestException("URL mengarah ke alamat privat/lokal dan tidak dapat dianalisis.")

    return parsed.geturl()


async def _fetch_url_content(url: str) -> str:
    """Fetch and return the plain-text content of a URL (max 50KB)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, max_redirects=5) as client:
        # Note: raise_for_status() will be called here, 
        # and analyze_url will catch the exception to fallback to AI.
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        text = response.text[:150_000]
        # Strip script and style contents completely
        text = re.sub(r"<script\b[^>]*>([\s\S]*?)<\/script>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<style\b[^>]*>([\s\S]*?)<\/style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:50_000]
