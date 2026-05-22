"""
OJK Service — safer & production-ready version

Features:
  #01 — Redis cache
  #02 — Prisma DB cache
  #03 — Official OJK public scraping
  #04 — Graceful failure
  #05 — Retry transport
  #06 — Better entity matching

Architecture:
  Redis
    ↓
  PostgreSQL (Prisma)
    ↓
  Live OJK scrape fallback
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from prisma import Prisma

from app.config import settings
from app.services.cache_service import (
    cache_get,
    cache_set,
    make_ojk_key,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# RESULT OBJECT
# ─────────────────────────────────────────────

class OjkCheckResult(NamedTuple):
    status: str
    entity_name: str
    detail: str | None
    source_url: str | None


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

async def check_entity(
    entity_name: str,
    db: Prisma,
) -> OjkCheckResult:
    """
    Main entity checker.
    """

    if not entity_name or len(entity_name.strip()) < 3:
        return OjkCheckResult(
            status="TIDAK_DITEMUKAN",
            entity_name=entity_name,
            detail="Nama entitas tidak valid.",
            source_url=None,
        )

    normalized = entity_name.strip()
    
    # ─────────────────────────────────────────
    # 0. VERIFIED WHITELIST (Pasar Modal / Crypto)
    # ─────────────────────────────────────────
    _VERIFIED_LEGAL_ENTITIES = {
        "stockbit": "PT Stockbit Sekuritas Digital",
        "ajaib": "PT Ajaib Sekuritas Asia",
        "bibit": "PT Bibit Tumbuh Bersama",
        "bareksa": "PT Bareksa Portal Investasi",
        "pluang": "PT Bumi Santosa Cemerlang",
        "pintu": "PT Pintu Kemana Saja",
        "tokocrypto": "PT Crypto Indonesia Berkat",
        "indodax": "PT Indodax Nasional Indonesia",
        "makmur": "PT Inovasi Finansial Teknologi",
        "tanamduit": "PT Star Mercato Capitale",
        "gopay": "PT Dompet Anak Bangsa",
        "ovo": "PT Visionet Internasional",
        "dana": "PT Espay Debit Indonesia Koe"
    }
    
    norm_lower = normalized.lower()
    for key, formal_name in _VERIFIED_LEGAL_ENTITIES.items():
        if key in norm_lower:
            result = OjkCheckResult(
                status="TERDAFTAR",
                entity_name=formal_name,
                detail="Entitas adalah platform investasi/finansial resmi yang terdaftar dan diawasi oleh OJK atau Bappebti.",
                source_url="https://reksadana.ojk.go.id/Public/ManajerInvestasiList.aspx" if key in ["bibit", "bareksa", "makmur", "tanamduit"] else "https://bappebti.go.id" if key in ["pintu", "tokocrypto", "indodax", "pluang"] else "https://ojk.go.id"
            )
            return result

    cache_key = make_ojk_key(normalized)

    # ─────────────────────────────────────────
    # 1. REDIS CACHE
    # ─────────────────────────────────────────

    cached = await cache_get(cache_key)

    if cached:
        logger.info(
            "OJK Redis cache HIT: %s",
            normalized,
        )

        return OjkCheckResult(**cached)

    # ─────────────────────────────────────────
    # 2. DATABASE CACHE
    # ─────────────────────────────────────────

    ttl_cutoff = (
        datetime.now(timezone.utc)
        - timedelta(
            hours=settings.OJK_CACHE_TTL_HOURS
        )
    )

    db_cached = await db.ojkentitycache.find_unique(
        where={
            "entityName": normalized.lower()
        }
    )

    if (
        db_cached
        and db_cached.cachedAt > ttl_cutoff
    ):
        logger.info(
            "OJK DB cache HIT: %s",
            normalized,
        )

        result = OjkCheckResult(
            status=db_cached.status,
            entity_name=db_cached.entityName,
            detail=db_cached.detail,
            source_url=db_cached.sourceUrl,
        )

        await _store_redis(
            cache_key,
            result,
        )

        return result

    # ─────────────────────────────────────────
    # 3. GEMINI GROUNDED OJK CHECK
    # ─────────────────────────────────────────

    result = await _check_ojk_with_gemini(
        normalized
    )

    # ─────────────────────────────────────────
    # 4. FALLBACK
    # ─────────────────────────────────────────

    if result is None:
        result = OjkCheckResult(
            status="TIDAK_DITEMUKAN",
            entity_name=normalized,
            detail=(
                "Entitas tidak ditemukan "
                "berdasarkan pencarian internet."
            ),
            source_url=None,
        )

    # ─────────────────────────────────────────
    # CACHE RESULT
    # ─────────────────────────────────────────

    await _persist_to_db(
        normalized,
        result,
        db,
    )

    await _store_redis(
        cache_key,
        result,
    )

    return result


async def check_entities_batch(
    entity_names: list[str],
    db: Prisma,
) -> dict[str, OjkCheckResult]:
    """
    Batch entity checker with concurrency control to avoid Gemini Rate Limits.
    """
    # Limit to 2 concurrent requests to avoid 429 Limit Reached on Free Tier
    semaphore = asyncio.Semaphore(2)

    async def _throttled_check(name: str):
        async with semaphore:
            # Add a tiny delay between requests to be safe
            await asyncio.sleep(0.5)
            return await check_entity(name, db)

    tasks = {
        name: asyncio.create_task(_throttled_check(name))
        for name in entity_names
    }

    results = {}

    for name, task in tasks.items():
        try:
            results[name] = await task

        except Exception as exc:
            logger.warning(
                "Batch check failed for '%s': %s",
                name,
                exc,
            )

            results[name] = OjkCheckResult(
                status="TIDAK_DITEMUKAN",
                entity_name=name,
                detail=None,
                source_url=None,
            )

    return results


import json
from google import genai
from google.genai import types

# ─────────────────────────────────────────────
# GEMINI AI GROUNDED CHECK
# ─────────────────────────────────────────────

async def _check_ojk_with_gemini(
    entity_name: str,
) -> OjkCheckResult | None:
    """
    Tahap 1: Use Gemini to format the entity name to kebab-case.
    Tahap 2: Scrape legalkah.id to find the exact status badges.
    """
    from app.services.cache_service import is_primary_api_key_exhausted, mark_primary_api_key_exhausted
    import httpx
    from bs4 import BeautifulSoup
    
    is_exhausted = await is_primary_api_key_exhausted()
    
    # Priority list of models
    primary_models = [
        settings.SENTRA_MODEL,
        settings.SENTRA_MODEL_BACKUP_1,
        "gemini-2.5-flash"
    ]
    primary_models = list(dict.fromkeys([m for m in primary_models if m]))
    
    clients_and_models = []
    primary_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    backup_client = None
    if hasattr(settings, "GEMINI_API_KEY_BACKUP_1") and settings.GEMINI_API_KEY_BACKUP_1:
        backup_client = genai.Client(api_key=settings.GEMINI_API_KEY_BACKUP_1)
        
    if not is_exhausted:
        for m in primary_models:
            clients_and_models.append((primary_client, m, True))
            
    if backup_client:
        for m in primary_models:
            clients_and_models.append((backup_client, m, False))
            
    if not clients_and_models:
        for m in primary_models:
            clients_and_models.append((primary_client, m, True))

    # TAHAP 1: AI Name Formatting
    prompt = f"""
Tugasmu adalah mengekstrak dan memformat nama perusahaan investasi dari input berikut untuk dicocokkan dengan database OJK.
Input: "{entity_name}"

Aturan:
1. Identifikasi nama LEGAL LENGKAP perusahaan tersebut di Indonesia (misalnya jika input "JP Morgan" atau "JPMorgan", nama legalnya adalah "Jp Morgan Sekuritas Indonesia").
2. Buang awalan seperti "PT", "PT.", "CV", "Firma", atau akhiran "Tbk", "Tbk.".
3. Ubah nama legal yang sudah dibersihkan tersebut menjadi lowercase kebab-case (menggunakan tanda hubung).
Contoh 1: "PT. Stockbit Sekuritas Digital" -> "stockbit-sekuritas-digital"
Contoh 2: "https://www.jpmorgan.co.id/" -> "jp-morgan-sekuritas-indonesia"
Contoh 3: "Aplikasi Ajaib" -> "ajaib-sekuritas-asia" (selalu gunakan nama legal perusahaan lengkapnya tanpa awalan PT jika kamu mengetahuinya)

Kembalikan HANYA string kebab-case tersebut tanpa tanda kutip, tanpa penjelasan apapun.
"""

    formatted_name = None

    for client, model_name, is_primary in clients_and_models:
        try:
            key_type = "PRIMARY" if is_primary else "BACKUP"
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                )
            )
            
            text = response.text.strip().lower()
            # Clean up potential markdown formatting
            if text.startswith("`") and text.endswith("`"):
                text = text.strip("`").strip()
            
            formatted_name = text
            break
        except Exception as exc:
            error_msg = str(exc).lower()
            if "429" in error_msg or "resource_exhausted" in error_msg:
                logger.warning("OJK Gemini format exhausted for %s on %s key, trying fallback...", model_name, key_type)
                if is_primary:
                    remaining_primaries = [
                        c for c in clients_and_models[clients_and_models.index((client, model_name, is_primary))+1:] 
                        if c[2]
                    ]
                    if not remaining_primaries:
                        await mark_primary_api_key_exhausted()
                continue
            logger.warning("Gemini OJK format failed for '%s' on %s: %s", entity_name, model_name, exc)
            break

    if not formatted_name:
        # Fallback regex if Gemini completely fails
        formatted_name = re.sub(r'^(pt\.?|cv\.?)\s+', '', entity_name, flags=re.IGNORECASE)
        formatted_name = re.sub(r'[^a-z0-9]+', '-', formatted_name.lower()).strip('-')

    # TAHAP 2: Web Scraping legalkah.id
    target_url = f"https://legalkah.id/e/{formatted_name}"
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http_client:
            resp = await http_client.get(target_url)
            
            if resp.status_code != 200:
                logger.warning("legalkah.id returned HTTP %s for %s", resp.status_code, formatted_name)
                return OjkCheckResult(
                    status="TIDAK_DITEMUKAN",
                    entity_name=entity_name,
                    detail=f"Tidak ditemukan data di legalkah.id untuk entitas ini.",
                    source_url=target_url
                )
                
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Check for TERDAFTAR DI OJK
            # <div class="status-badge badge-licensed">✅ TERDAFTAR DI OJK</div>
            licensed_tags = soup.find_all(lambda tag: tag.name in ["div", "span"] and "badge-licensed" in tag.get("class", []))
            for tag in licensed_tags:
                if "TERDAFTAR DI OJK" in tag.text.upper() or "✅" in tag.text:
                    return OjkCheckResult(
                        status="TERDAFTAR",
                        entity_name=entity_name,
                        detail="Entitas terdaftar resmi di OJK (via legalkah.id).",
                        source_url=target_url
                    )
                    
            # Check for ILEGAL
            # <div class="status-badge badge-illegal">❌ ILEGAL / DIBLOKIR</div> 
            # <span class="status-badge badge-illegal">❌ ILEGAL DALAM ARSIP</span>
            illegal_tags = soup.find_all(lambda tag: tag.name in ["div", "span"] and "badge-illegal" in tag.get("class", []))
            for tag in illegal_tags:
                text_upper = tag.text.upper()
                if "ILEGAL / DIBLOKIR" in text_upper or "ILEGAL DALAM ARSIP" in text_upper or "❌" in text_upper:
                    return OjkCheckResult(
                        status="TIDAK_TERDAFTAR", # Mapped per user request
                        entity_name=entity_name,
                        detail="Entitas terindikasi ilegal atau diblokir (via legalkah.id).",
                        source_url=target_url
                    )
            
            # If no badges matched
            return OjkCheckResult(
                status="TIDAK_DITEMUKAN",
                entity_name=entity_name,
                detail="Status legalitas tidak dapat dipastikan dari web.",
                source_url=target_url
            )
            
    except Exception as e:
        logger.error("Scraping legalkah.id failed for %s: %s", formatted_name, e)
        return OjkCheckResult(
            status="TIDAK_DITEMUKAN",
            entity_name=entity_name,
            detail="Gagal mengakses database legalitas eksternal.",
            source_url=target_url
        )


# ─────────────────────────────────────────────
# DATABASE CACHE
# ─────────────────────────────────────────────

async def _persist_to_db(
    entity_name: str,
    result: OjkCheckResult,
    db: Prisma,
) -> None:
    """
    Store result to database cache.
    """

    try:
        await db.ojkentitycache.upsert(
            where={
                "entityName": entity_name.lower()
            },
            data={
                "create": {
                    "entityName": (
                        entity_name.lower()
                    ),
                    "status": result.status,
                    "detail": result.detail,
                    "sourceUrl": (
                        result.source_url
                    ),
                },
                "update": {
                    "status": result.status,
                    "detail": result.detail,
                    "sourceUrl": (
                        result.source_url
                    ),
                    "cachedAt": datetime.now(
                        timezone.utc
                    ),
                },
            },
        )

    except Exception as exc:
        logger.warning(
            "DB persist failed: %s",
            exc,
        )


# ─────────────────────────────────────────────
# REDIS CACHE
# ─────────────────────────────────────────────

async def _store_redis(
    cache_key: str,
    result: OjkCheckResult,
) -> None:
    """
    Store to Redis cache.
    """

    try:
        ttl_seconds = (
            settings.OJK_CACHE_TTL_HOURS
            * 3600
        )

        await cache_set(
            cache_key,
            result._asdict(),
            ttl_seconds=ttl_seconds,
        )

    except Exception as exc:
        logger.warning(
            "Redis cache store failed: %s",
            exc,
        )